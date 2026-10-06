"""Real LAN sockets against a KS-wire simulator. All keys/addresses are test data."""
import asyncio
import base64
import hashlib
import hmac
import json
import struct
import sys
import time
import uuid
from pathlib import Path

import pytest
from aiohttp import ClientSession, web

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kiosk_sip/app"))
from configuration import Settings, asterisk_files, validate
from intercom import IntercomBridge, issue_token, packet, read_packet, verify_token, upsample, downsample

KEY = "fake-intercom-key-not-a-real-secret"


def cfg(**changes):
    return {"enabled": True, "phone_number": "+4900001234567", "listen_address": "10.77.8.20",
            "local_network": "10.77.8.0/24", "phone_password": "fake-phone-secret-123",
            "audio_target": "kiosk", "kiosk_address": "10.77.8.21", "intercom_key": KEY, **changes}


def test_native_configuration_and_secret_lifecycle(tmp_path):
    settings = Settings(tmp_path)
    settings.save(cfg())
    assert settings.value["audio_target"] == "kiosk"
    assert KEY not in json.dumps(settings.public())
    assert settings.public()["intercom_key_set"]
    settings.save({"intercom_key": ""})
    assert settings.value["intercom_key"] == KEY
    with pytest.raises(ValueError, match="gemeinsamen Intercom-Schlüssel"):
        settings.save({"kiosk_address": "10.77.8.22", "intercom_key": ""})
    assert settings.value["kiosk_address"] == "10.77.8.21"
    settings.save({"kiosk_address": "10.77.8.22", "intercom_key": "fake-new-intercom-key"})
    assert settings.value["intercom_key"] == "fake-new-intercom-key"


def test_native_audio_does_not_require_an_unused_sip_phone_password():
    value = validate(cfg(phone_password=""))
    assert value["phone_password"] == ""
    assert "[phone-auth]" not in asterisk_files(value, "fake-ami", (14001, 14002))["pjsip.conf"]
    with pytest.raises(ValueError, match="SIP-Telefon-Passwort"):
        validate({"audio_target": "sip"}, value)


@pytest.mark.parametrize("changes", [
    {"kiosk_address": "8.8.8.8"}, {"kiosk_address": "10.77.9.21"},
    {"kiosk_address": "10.77.8.20"}, {"kiosk_address": "10.77.8.255"},
    {"kiosk_address": "kiosk.example"}, {"kiosk_address": []},
    {"kiosk_port": True}, {"kiosk_port": 80}, {"intercom_port": 5038},
    {"intercom_port": 5070}, {"intercom_key": "short"}, {"audio_target": "unknown"},
])
def test_native_configuration_rejects_unsafe_addresses_and_ports(changes):
    with pytest.raises(ValueError):
        validate(cfg(**changes))


def test_native_dialplan_preserves_authorization_before_audio_and_normal_ring():
    value = validate(cfg())
    main = value["lines"][0]
    value["lines"].append({**main, "id": "page", "incoming_mode": "announcement",
                          "phone_number": "+4900001234568", "announcement_callers": ["+4900011234567"],
                          "announcement_pin": "123456"})
    files = asterisk_files(value, "fake-ami-secret", (14001, 14002))
    dial = files["extensions.conf"]
    normal = dial.split("[incoming-main]")[1].split("[incoming-page]")[0]
    assert "Ringing()" in normal and "kiosk-native,s,1(main,call)" in normal
    assert "broadcast" not in normal and "Answer()" not in normal
    page = dial.split("[incoming-page]")[1].split("[kiosk-auto-answer]")[0]
    assert page.index("123456") < page.index("kiosk-native,s,1(page,broadcast)")
    assert page.index("+4900011234567") < page.index("kiosk-native,s,1(page,broadcast)")
    assert "Dial(AudioSocket/127.0.0.1:14002/${KIOSK_UUID}/c(slin)" in dial
    assert "agi://127.0.0.1:14001" in dial
    assert KEY not in json.dumps(files)
    assert all(x + ".so" in files["modules.conf"] for x in ("res_agi", "res_audiosocket", "chan_audiosocket", "codec_resample"))


def test_wire_token_matches_dart_signing_and_rejects_replay_wrong_call_sender_key():
    token = issue_token(KEY, "test-call", "test-kiosk")
    payload, signature = token.split(".")
    assert base64.urlsafe_b64decode(signature) == hmac.new(("intercom:" + KEY).encode(), payload.encode(), hashlib.sha256).digest()
    claims = json.loads(base64.urlsafe_b64decode(payload))
    assert claims["exp"] > time.time() * 1000 and claims["intercom"] == "test-call"
    assert not verify_token(KEY, token, "other", "test-kiosk", {})
    assert not verify_token(KEY, token, "test-call", "other", {})
    assert not verify_token("wrong", token, "test-call", "test-kiosk", {})
    seen = {}
    assert verify_token(KEY, token, "test-call", "test-kiosk", seen)
    assert not verify_token(KEY, token, "test-call", "test-kiosk", seen)
    for invalid in (None, [], "bad", "a.b.c", "a.b", "x" * 3000):
        assert not verify_token(KEY, invalid, "test-call", "test-kiosk", {})


async def wire_scenario(kind="call", refuse=False, tls=False, advertised=False):
    received = asyncio.Queue()
    accepted = asyncio.Event()
    attached = asyncio.Event()
    fake_ws = []
    peer_port = 0
    bridge = IntercomBridge({**validate(cfg()), "listen_address": "127.0.0.1",
                             "kiosk_address": "127.0.0.1", "intercom_port": 0})
    async def identity(request):
        return web.json_response({"id": "test-kiosk", "name": "Test kiosk", "enabled": True,
                                  "key": hashlib.sha256(KEY.encode()).hexdigest()[:8], "endpoint": {"tls": tls, **({"port": peer_port} if advertised else {})}})

    async def incoming(request):
        body = await request.json()
        assert body["kind"] == kind
        assert body["from"]["tls"] is False
        assert verify_token(KEY, request.headers["Authorization"][7:], body["call"], "kiosk-sip-gateway", {})
        async def answer():
            await accepted.wait()
            async with ClientSession() as client:
                token = issue_token(KEY, body["call"], "test-kiosk")
                url = f"http://127.0.0.1:{bridge.callback_port}/api/intercom/call/{body['call']}"
                bad = await client.post(url, json={"action": "answer"}, headers={"Authorization": "Bearer bad"})
                assert bad.status == 403
                good = await client.post(url, json={"action": "answer"}, headers={"Authorization": "Bearer " + token})
                assert good.status == 200
                replay = await client.post(url, json={"action": "answer"}, headers={"Authorization": "Bearer " + token})
                assert replay.status == 403
        if kind == "call" and not refuse:
            asyncio.create_task(answer())
        return web.json_response({"status": "dnd" if refuse else "listening" if kind == "broadcast" else "ringing"})

    async def audio(request):
        assert verify_token(KEY, request.query.get("token"), request.match_info["call"], "kiosk-sip-gateway", {})
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        fake_ws.append(ws)
        attached.set()
        async for frame in ws:
            if isinstance(frame.data, bytes):
                await received.put(frame.data)
            elif isinstance(frame.data, str) and json.loads(frame.data).get("type") == "end":
                break
        return ws

    async def signal(request):
        return web.json_response({"ok": True})
    app = web.Application()
    app.router.add_get("/api/intercom/identity", identity)
    app.router.add_post("/api/intercom/call", incoming)
    app.router.add_get("/api/intercom/audio/{call}", audio)
    app.router.add_post("/api/intercom/call/{call}", signal)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    peer_port = site._server.sockets[0].getsockname()[1]
    bridge.cfg["kiosk_port"] = peer_port
    identity_runner = None
    if advertised:
        identity_app = web.Application()
        identity_app.router.add_get("/api/intercom/identity", identity)
        identity_runner = web.AppRunner(identity_app, access_log=None)
        await identity_runner.setup()
        identity_site = web.TCPSite(identity_runner, "127.0.0.1", 0)
        await identity_site.start()
        bridge.cfg["kiosk_port"] = identity_site._server.sockets[0].getsockname()[1]
        assert bridge.cfg["kiosk_port"] != peer_port
    try:
        await bridge._start()
        bridge.callback_port = next(iter(bridge.runner.sites))._server.sockets[0].getsockname()[1]
        bridge.cfg["intercom_port"] = bridge.callback_port
        if refuse or tls:
            with pytest.raises(RuntimeError):
                await bridge._invite(kind, "Test")
            assert bridge.active is None
            assert not fake_ws
            return
        agi_reader, agi_writer = await asyncio.open_connection("127.0.0.1", bridge.agi_port)
        line_id = "main"
        if kind == "broadcast":
            bridge.cfg["lines"][0]["incoming_mode"] = "announcement"
        agi_writer.write(f"agi_arg_1: {line_id}\nagi_arg_2: {kind}\n\n".encode())
        await agi_writer.drain()
        if kind == "call":
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(agi_reader.readline(), .1)
            assert not attached.is_set()  # No audio/answer before kiosk accepts.
            accepted.set()
        command = await asyncio.wait_for(agi_reader.readline(), 5)
        assert command.startswith(b"SET VARIABLE KIOSK_UUID")
        identifier = command.decode().split('"')[1]
        agi_writer.write(b"200 result=1\n")
        await agi_writer.drain()
        await attached.wait()
        reader, writer = await asyncio.open_connection("127.0.0.1", bridge.audio_port)
        writer.write(packet(1, uuid.UUID(identifier).bytes))
        outbound = struct.pack("<640h", *([1200, -800] * 320))
        for pos in range(0, 1280, 320):
            writer.write(packet(0x10, outbound[pos:pos+320]))
        await writer.drain()
        assert await asyncio.wait_for(received.get(), 3) == upsample(outbound)[0]
        inbound = struct.pack("<1280h", *([-400, 700] * 640))
        await fake_ws[0].send_bytes(inbound)
        if kind == "broadcast":
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(read_packet(reader), .2)
        else:
            returned = []
            for _ in range(4):
                typ, data = await asyncio.wait_for(read_packet(reader), 3)
                assert typ == 0x10 and len(data) == 320
                returned.append(data)
            assert b"".join(returned) == downsample(inbound)
        await fake_ws[0].send_json({"type": "end"})
        assert await asyncio.wait_for(reader.read(), 3) == b""
        for _ in range(30):
            if bridge.active is None:
                break
            await asyncio.sleep(.01)
        assert bridge.active is None
        assert bridge.sent == 1 and bridge.received == 1
        writer.close()
        agi_writer.close()
    finally:
        await bridge._close()
        await runner.cleanup()
        if identity_runner:
            await identity_runner.cleanup()


def test_two_way_native_audio_waits_for_answer_and_hangs_up():
    asyncio.run(wire_scenario())


def test_native_announcement_sends_audio_but_discards_microphone_return():
    asyncio.run(wire_scenario("broadcast"))


def test_native_audio_uses_advertised_dynamic_listener_instead_of_admin_port():
    asyncio.run(wire_scenario(advertised=True))


@pytest.mark.parametrize("refuse,tls", [(True, False), (False, True)])
def test_refusal_and_required_tls_never_open_audio(refuse, tls):
    asyncio.run(wire_scenario(refuse=refuse, tls=tls))
