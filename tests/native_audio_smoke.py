"""Container only: real Asterisk Echo through FastAGI/AudioSocket and KS WebSocket.

No provider is contacted; the test uses a local custom profile and fake key.
"""
import asyncio
import hashlib
import math
import os
import pwd
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from aiohttp import ClientSession, WSMsgType, web

sys.path.insert(0, "/app")
from configuration import DEFAULTS, asterisk_files
from intercom import IntercomBridge, issue_token, verify_token

KEY = "fake-ci-intercom-key-no-customer-data"


async def main():
    bridge = None
    process = None
    received = asyncio.Queue()
    connected = asyncio.Event()
    fake_ws = []
    base = Path(tempfile.mkdtemp(prefix="native-audio-smoke-"))
    base.chmod(0o755)
    user = pwd.getpwnam("asterisk")
    for sub in ("config", "run", "db", "spool", "log"):
        p = base / sub
        p.mkdir()
        os.chown(p, user.pw_uid, user.pw_gid)
    value = {**DEFAULTS, "enabled": True, "phone_number": "+4900001234567",
             "listen_address": "127.0.0.1", "local_network": "127.0.0.1/32",
             "sip_port": 15090, "audio_target": "kiosk", "kiosk_address": "127.0.0.1",
             "intercom_port": 0, "intercom_key": KEY}
    value["lines"] = [{**value, "id": "main", "label": "CI", "provider": "custom",
                       "incoming_mode": "normal", "registrar": "127.0.0.1:15999",
                       "domain": "127.0.0.1", "client_user": "test", "contact_user": "test",
                       "from_user": "test", "stun_server": ""}]

    async def identity(request):
        return web.json_response({"id": "fake-ci-kiosk", "enabled": True,
                                  "key": hashlib.sha256(KEY.encode()).hexdigest()[:8], "endpoint": {"tls": False}})

    async def incoming(request):
        data = await request.json()
        assert data["kind"] == "call"
        assert verify_token(KEY, request.headers["Authorization"][7:], data["call"], "kiosk-sip-gateway", {})
        async def answer():
            await asyncio.sleep(.1)
            async with ClientSession() as client:
                response = await client.post(f"http://127.0.0.1:{value['intercom_port']}/api/intercom/call/{data['call']}",
                    json={"action": "answer"}, headers={"Authorization": "Bearer " + issue_token(KEY, data["call"], "fake-ci-kiosk")})
                assert response.status == 200
        asyncio.create_task(answer())
        return web.json_response({"status": "ringing"})

    async def audio(request):
        assert verify_token(KEY, request.query["token"], request.match_info["call"], "kiosk-sip-gateway", {})
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        fake_ws.append(ws)
        connected.set()
        async for message in ws:
            if message.type == WSMsgType.BINARY:
                await received.put(message.data)
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
    value["kiosk_port"] = site._server.sockets[0].getsockname()[1]
    try:
        bridge = IntercomBridge(value)
        await bridge._start()
        value["intercom_port"] = next(iter(bridge.runner.sites))._server.sockets[0].getsockname()[1]
        bridge.cfg["intercom_port"] = value["intercom_port"]
        files = asterisk_files(value, "fake-ci-ami-secret", (bridge.agi_port, bridge.audio_port))
        # Remove registration entirely: this smoke test is strictly local audio.
        files["pjsip.conf"] = files["pjsip.conf"].split("[line-main-registration]")[0]
        files["asterisk.conf"] = files["asterisk.conf"].replace("/etc/asterisk", str(base / "config"))
        for old, sub in (("/run/asterisk", "run"), ("/data/asterisk", "db"),
                         ("/var/spool/asterisk", "spool"), ("/var/log/asterisk", "log")):
            files["asterisk.conf"] = files["asterisk.conf"].replace(old, str(base / sub))
        files["manager.conf"] = "[general]\nenabled=no\n"
        for name, content in files.items():
            path = base / "config" / name
            path.write_text(content)
            path.chmod(0o640)
            os.chown(path, 0, user.pw_gid)
        conf = str(base / "config/asterisk.conf")
        log = open(base / "asterisk.log", "w+")
        process = subprocess.Popen(["asterisk", "-f", "-C", conf, "-U", "asterisk", "-G", "asterisk"], stdout=log, stderr=log)
        def cli(command):
            return subprocess.run(["asterisk", "-C", conf, "-rx", command], capture_output=True, text=True, timeout=3).stdout
        for _ in range(60):
            if "System uptime" in cli("core show uptime"):
                break
            if process.poll() is not None:
                raise RuntimeError("isolated Asterisk exited")
            await asyncio.sleep(.1)
        for module in ("res_agi.so", "res_audiosocket.so", "chan_audiosocket.so", "codec_resample.so"):
            assert module in cli("module show like " + module), module
        cli("channel originate Local/s@kiosk-native-out/n extension 600@from-phone")
        await asyncio.wait_for(connected.wait(), 10)
        # The WS opens just before AGI returns. Wait until Asterisk attaches.
        for _ in range(100):
            if bridge.active and bridge.active["writer"]:
                break
            await asyncio.sleep(.02)
        assert bridge.active and bridge.active["writer"], "real AudioSocket did not attach"
        async def speak():
            for frame in range(25):
                samples = [int(6000 * math.sin(2 * math.pi * 440 * (frame * 1280 + i) / 16000)) for i in range(1280)]
                await fake_ws[0].send_bytes(struct.pack("<1280h", *samples))
                await asyncio.sleep(.08)
        speaking = asyncio.create_task(speak())
        heard = False
        for _ in range(35):
            data = await asyncio.wait_for(received.get(), 5)
            assert len(data) == 2560
            samples = struct.unpack("<1280h", data)
            if sum(x*x for x in samples) / 1280 > 1000000:
                heard = True
                break
        assert heard, "only silence returned by real Echo"
        await speaking
        assert bridge.sent > 0 and bridge.received > 0
        await fake_ws[0].send_json({"type": "end"})
        for _ in range(80):
            if bridge.active is None and "0 active channels" in cli("core show channels"):
                break
            await asyncio.sleep(.05)
        assert bridge.active is None
        assert "0 active channels" in cli("core show channels")
        print("PASS: real Asterisk FastAGI -> AudioSocket 8 kHz / KS 16 kHz -> KS WebSocket, microphone tone echoed bidirectionally and hangup leaves no channels.")
    except Exception:
        if 'log' in locals():
            log.flush()
            log.seek(0)
            print(log.read()[-12000:])
        raise
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        if bridge:
            await bridge._close()
        await runner.cleanup()


asyncio.run(main())
