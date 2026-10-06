"""Native KS Intercom wire <-> Asterisk AudioSocket, no microphone in a web page.

Protocol sources: jxlarrea/kiosk-satellite intercom_routes.dart,
intercom_manager.dart and remote/auth.dart. KS is 16 kHz; Asterisk 20 is 8 kHz.
Only the configured LAN kiosk can signal an active call, with a fresh HMAC token.
"""
import asyncio
from array import array
import base64
import hashlib
import hmac
import json
import secrets
import struct
import sys
import threading
import time
import uuid

from aiohttp import ClientSession, ClientTimeout, ClientWSTimeout, WSMsgType, web


def issue_token(key, call, sender="kiosk-sip-gateway"):
    claims = {"intercom": call, "from": sender, "n": secrets.token_hex(12),
              "exp": int(time.time() * 1000) + 60000}
    payload = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode()).decode()
    signature = base64.urlsafe_b64encode(hmac.digest(("intercom:" + key).encode(), payload.encode(), "sha256")).decode()
    return payload + "." + signature


def verify_token(key, token, call, sender, seen):
    if not key or not isinstance(token, str) or len(token) > 2048:
        return False
    try:
        payload, signature = token.split(".")
        expected = base64.urlsafe_b64encode(hmac.digest(("intercom:" + key).encode(), payload.encode(), "sha256")).decode()
        if not hmac.compare_digest(signature, expected):
            return False
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        now = int(time.time() * 1000)
        exp = claims.get("exp")
        if (type(exp) is not int or not now < exp <= now + 65000 or
                claims.get("intercom") != call or claims.get("from") != sender or not claims.get("n")):
            return False
        for old in [t for t, expiry in seen.items() if expiry < now]:
            del seen[old]
        if token in seen or len(seen) >= 256:
            return False
        seen[token] = exp
        return True
    except (ValueError, TypeError, AttributeError, UnicodeError):
        return False


async def read_packet(reader):
    header = await reader.readexactly(3)
    kind, size = header[0], struct.unpack("!H", header[1:])[0]
    if size > 4096:
        raise ValueError("Audio frame too large")
    return kind, await reader.readexactly(size)


def packet(kind, data=b""):
    return bytes([kind]) + struct.pack("!H", len(data)) + data


def pcm_samples(data):
    samples = array("h")
    samples.frombytes(data)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def pcm_bytes(samples):
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


def upsample(data, previous=0):
    """8 -> 16 kHz, continuous linear interpolation across socket frames."""
    out = array("h")
    for sample in pcm_samples(data):
        out.extend(((previous + sample) // 2, sample))
        previous = sample
    return pcm_bytes(out), previous


def downsample(data):
    """16 -> 8 kHz, pair-average low-pass for the narrowband G.711 leg."""
    samples = pcm_samples(data)
    return pcm_bytes(array("h", ((samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples), 2))))


class IntercomBridge:
    def __init__(self, cfg):
        self.cfg = dict(cfg)
        self.loop = None
        self.thread = None
        self.active = None
        self.ready = threading.Event()
        self.start_error = False
        self.agi_port = self.audio_port = 0
        self.state = "nicht gestartet"
        self.last_error = ""
        self.sent = self.received = 0
        self._identity = None
        self._probe_at = 0
        self._call_port = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        if not self.ready.wait(8) or self.start_error:
            self.stop()
            raise RuntimeError("Kiosk-Audio-Listener konnte nicht starten. Kiosk-Rückrufport und lokale HAOS-IP prüfen.")

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._start())
            self.ready.set()
            self.loop.run_forever()
        except Exception:
            self.start_error = True
            self.ready.set()
        finally:
            self.loop.run_until_complete(self._close())
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()

    async def _start(self):
        self.session = ClientSession(timeout=ClientTimeout(total=5))
        self.audio_server = await asyncio.start_server(self._audio, "127.0.0.1", 0)
        self.audio_port = self.audio_server.sockets[0].getsockname()[1]
        self.agi_server = await asyncio.start_server(self._agi, "127.0.0.1", 0)
        self.agi_port = self.agi_server.sockets[0].getsockname()[1]
        app = web.Application(client_max_size=4096)
        app.router.add_post("/api/intercom/call/{call}", self._signal)
        self.runner = web.AppRunner(app, access_log=None)
        await self.runner.setup()
        await web.TCPSite(self.runner, self.cfg["listen_address"], self.cfg["intercom_port"]).start()
        self.state = "bereit"

    async def _close(self):
        if self.active:
            await self._finish(self.active)
        for name in ("audio_server", "agi_server"):
            server = getattr(self, name, None)
            if server:
                server.close()
                await server.wait_closed()
        if getattr(self, "runner", None):
            await self.runner.cleanup()
        if getattr(self, "session", None):
            await self.session.close()

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=8)

    def status(self):
        return {"state": self.state, "error": self.last_error,
                "active": self.active is not None, "sent": self.sent, "received": self.received}

    async def _probe(self):
        # Never guess a host or scan a subnet. The administrator supplies one IP.
        if self._identity and time.monotonic() - self._probe_at < 2:
            return self._identity
        async with self.session.get(self._base(identity=True) + "/api/intercom/identity", allow_redirects=False) as response:
            if response.status != 200:
                raise RuntimeError("Kiosk-Intercom nicht erreichbar. IP und Intercom-Port prüfen.")
            raw = await response.content.read(4097)
            if len(raw) > 4096:
                raise RuntimeError("Ungültige Kiosk-Identität.")
            identity = json.loads(raw)
        if (not isinstance(identity, dict) or not isinstance(identity.get("id"), str) or
                not identity["id"] or len(identity["id"]) > 256):
            raise RuntimeError("Ungültige Kiosk-Identität.")
        if not identity.get("enabled"):
            raise RuntimeError("Intercom am Kiosk ist nicht aktiviert.")
        if identity.get("key") != hashlib.sha256(self.cfg["intercom_key"].encode()).hexdigest()[:8]:
            raise RuntimeError("Der Intercom-Schlüssel stimmt nicht mit dem Kiosk überein.")
        endpoint = identity.get("endpoint") or {}
        if not isinstance(endpoint, dict):
            raise RuntimeError("Ungültige Kiosk-Identität.")
        if endpoint.get("tls"):
            raise RuntimeError("Der Kiosk verlangt TLS. Diese Audio-Brücke unterstützt derzeit nur lokale HTTP/WS-Intercom-Verbindungen; TLS-Einstellungen werden nicht verändert.")
        if identity.get("dnd"):
            raise RuntimeError("Der Kiosk ist auf Nicht stören gestellt.")
        port = endpoint.get("port", self.cfg["kiosk_port"])
        if type(port) is not int or not 1024 <= port <= 65535:
            raise RuntimeError("Ungültiger Kiosk-Intercom-Port.")
        self._call_port = port
        self._identity, self._probe_at = identity, time.monotonic()
        return identity

    def _base(self, identity=False):
        port = self.cfg["kiosk_port"] if identity else self._call_port or self.cfg["kiosk_port"]
        return f"http://{self.cfg['kiosk_address']}:{port}"

    async def _post(self, call, path, body):
        async with self.session.post(self._base() + path, json=body, allow_redirects=False,
                headers={"Authorization": "Bearer " + issue_token(self.cfg["intercom_key"], call["id"])}) as response:
            raw = await response.content.read(4097)
            if len(raw) > 4096:
                raise RuntimeError("Ungültige Kiosk-Antwort.")
            data = json.loads(raw)
            return response.status, data

    async def _invite(self, kind, label):
        if self.active:
            raise RuntimeError("Kiosk-Audio ist bereits in einem Gespräch.")
        call = {"id": str(uuid.uuid4()), "kind": kind, "answer": asyncio.Event(),
                "end": asyncio.Event(), "seen": {}, "writer": None, "ws": None,
                "peer_id": None, "answered": False, "created": time.monotonic()}
        self.active = call
        self.sent = self.received = 0
        self.last_error = ""
        self.state = "verbinden"
        try:
            identity = await self._probe()
            call["peer_id"] = identity["id"]
            code, reply = await self._post(call, "/api/intercom/call", {
                "call": call["id"], "kind": kind,
                "from": {"id": "kiosk-sip-gateway", "name": label[:80],
                         "address": self.cfg["listen_address"], "port": self.cfg["intercom_port"],
                         "version": "26.10.10", "tls": False}})
            if code != 200 or reply.get("status") not in {"ringing", "auto", "listening"}:
                status = reply.get("status")
                reason = {"busy": "Kiosk ist besetzt.", "dnd": "Kiosk ist auf Nicht stören gestellt.",
                          "key": "Intercom-Schlüssel stimmt nicht.", "off": "Intercom am Kiosk ist aus.",
                          "tls": "Kiosk verlangt eine verschlüsselte Intercom-Verbindung.",
                          "refused": "Kiosk erlaubt keine Durchsagen."}.get(status, "Kiosk hat den Anruf abgelehnt.")
                raise RuntimeError(reason)
            if kind == "broadcast":
                call["answered"] = True
                call["answer"].set()
            self.state = "Durchsage" if kind == "broadcast" else "klingelt am Kiosk"
            answer = asyncio.create_task(call["answer"].wait())
            end = asyncio.create_task(call["end"].wait())
            try:
                await asyncio.wait({answer, end}, timeout=50, return_when=asyncio.FIRST_COMPLETED)
                if not call["answered"] or call["end"].is_set():
                    raise RuntimeError("Kiosk hat nicht angenommen oder den Anruf beendet.")
            finally:
                for task in (answer, end):
                    task.cancel()
                await asyncio.gather(answer, end, return_exceptions=True)
            token = issue_token(self.cfg["intercom_key"], call["id"])
            call["ws"] = await self.session.ws_connect(self._base() + "/api/intercom/audio/" + call["id"],
                params={"token": token}, max_msg_size=4096, heartbeat=10, timeout=ClientWSTimeout(ws_close=5),
                compress=0, autoclose=True)
            await call["ws"].send_json({"type": "talk", "on": True})
            self.state = "Durchsage verbunden" if kind == "broadcast" else "Audio verbunden"
            return call
        except Exception as exc:
            self.last_error = str(exc) if isinstance(exc, RuntimeError) else "Kiosk-Audio nicht erreichbar. IP, Intercom-Port und Schlüssel prüfen."
            await self._finish(call)
            raise RuntimeError(self.last_error) from None

    async def _signal(self, request):
        call = self.active
        if (not call or request.match_info["call"] != call["id"] or
                request.remote != self.cfg["kiosk_address"]):
            return web.json_response({"ok": False}, status=403)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or not verify_token(self.cfg["intercom_key"], auth[7:],
                call["id"], call["peer_id"], call["seen"]):
            return web.json_response({"ok": False}, status=403)
        try:
            body = await request.json()
        except (ValueError, UnicodeError):
            return web.json_response({"ok": False}, status=400)
        action = body.get("action") if isinstance(body, dict) else None
        if action == "answer" and call["kind"] == "call" and not call["answered"]:
            call["answered"] = True
            call["answer"].set()
        elif action in {"decline", "missed", "cancel", "hangup"}:
            call["end"].set()
        else:
            return web.json_response({"ok": False}, status=400)
        return web.json_response({"ok": True})

    async def _agi(self, reader, writer):
        call = None
        tasks = []
        try:
            env = {}
            for _ in range(80):
                line = await asyncio.wait_for(reader.readline(), 5)
                if not line or line in {b"\n", b"\r\n"}:
                    break
                key, _, value = line.decode(errors="replace").partition(":")
                env[key] = value.strip()
            # Fixed contexts supply only the configured line ID, never a URL.
            line_id = env.get("agi_arg_1", "")
            kind = env.get("agi_arg_2", "call")
            line = next((x for x in self.cfg.get("lines", []) if x["id"] == line_id and x["enabled"]), None)
            if kind not in {"call", "broadcast"} or (line_id != "local" and not line):
                return
            if kind == "broadcast" and (not line or line["incoming_mode"] != "announcement"):
                return
            invite = asyncio.create_task(self._invite(kind, line["label"] if line else "Lokaler Audio-Test"))
            gone = asyncio.create_task(reader.readline())
            tasks.extend((invite, gone))
            done, _ = await asyncio.wait({invite, gone}, return_when=asyncio.FIRST_COMPLETED)
            if gone in done:
                invite.cancel()
                if self.active:
                    await self._finish(self.active)
                return
            gone.cancel()
            await asyncio.gather(gone, return_exceptions=True)
            call = await invite
            writer.write(f'SET VARIABLE KIOSK_UUID "{call["id"]}"\n'.encode())
            await writer.drain()
            if not (await asyncio.wait_for(reader.readline(), 3)).startswith(b"200"):
                await self._finish(call)
                return
            # AudioSocket must attach quickly after AGI. Otherwise discard invite.
            asyncio.create_task(self._expire_unattached(call))
        except (Exception, asyncio.CancelledError):
            if call:
                await self._finish(call)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            writer.close()
            await writer.wait_closed()

    async def _expire_unattached(self, call):
        await asyncio.sleep(5)
        if self.active is call and not call["writer"]:
            await self._finish(call)

    async def _audio(self, reader, writer):
        call = None
        tasks = []
        try:
            kind, data = await asyncio.wait_for(read_packet(reader), 3)
            active = self.active
            if (kind != 1 or len(data) != 16 or not active or active["writer"] or
                    str(uuid.UUID(bytes=data)) != active["id"] or not active["ws"]):
                return
            call = active
            call["writer"] = writer
            tasks = [asyncio.create_task(self._to_kiosk(call, reader)),
                     asyncio.create_task(self._to_asterisk(call, writer)),
                     asyncio.create_task(call["end"].wait())]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        except (Exception, asyncio.CancelledError):
            pass
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if call:
                await self._finish(call)
            writer.close()
            await writer.wait_closed()

    async def _to_kiosk(self, call, reader):
        pending = bytearray()
        previous = 0
        while True:
            kind, data = await read_packet(reader)
            if kind == 0:
                return
            if kind == 3:  # DTMF is not PCM; don't feed it to the speaker.
                continue
            if kind != 0x10 or not data or len(data) % 2:
                raise ValueError("Expected 8-kHz signed PCM")
            converted, previous = upsample(data, previous)
            pending.extend(converted)
            while len(pending) >= 2560:  # KS wire: 80 ms * 16 kHz * 2 bytes.
                await call["ws"].send_bytes(bytes(pending[:2560]))
                del pending[:2560]
                self.sent += 1

    async def _to_asterisk(self, call, writer):
        pending = bytearray()
        clock = asyncio.get_running_loop()
        due = clock.time()
        async for frame in call["ws"]:
            if frame.type == WSMsgType.BINARY:
                data = frame.data
                if not data or len(data) % 2 or len(data) > 4096:
                    raise ValueError("Invalid KS PCM frame")
                self.received += 1
                if call["kind"] == "broadcast":
                    continue  # A page never returns kiosk microphone audio.
                pending.extend(data)
                if len(pending) > 5120:
                    raise ValueError("Audio backlog")
                while len(pending) >= 640:
                    now = clock.time()
                    due = max(due, now - 0.02)
                    await asyncio.sleep(max(0, due - now))
                    writer.write(packet(0x10, downsample(bytes(pending[:640]))))
                    del pending[:640]
                    await asyncio.wait_for(writer.drain(), 1)
                    due += 0.02
            elif frame.type == WSMsgType.TEXT:
                control = json.loads(frame.data)
                if control.get("type") == "end":
                    return
            elif frame.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                return

    async def _finish(self, call):
        if call.get("finishing"):
            return
        call["finishing"] = True
        call["end"].set()
        ws = call.get("ws")
        if ws and not ws.closed:
            try:
                await ws.send_json({"type": "end"})
                await ws.close()
            except Exception:
                pass
        if call.get("writer"):
            call["writer"].close()
        try:
            await self._post(call, "/api/intercom/call/" + call["id"],
                             {"action": "hangup" if call["answered"] else "cancel"})
        except Exception:
            pass
        if self.active is call:
            self.active = None
            self.state = "bereit"
