"""Asterisk lifecycle, read-only diagnostics and local AMI call setup."""
import grp
import os
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path

from configuration import asterisk_files, effective_lines, DESTINATION
from networking import PortConflict, check_port
from intercom import IntercomBridge


class Pbx:
    def __init__(self, settings):
        self.settings = settings
        self.process = None
        self.lock = threading.RLock()
        self.last_error = ""
        self.bridge = None

    def write_config(self):
        import pwd
        uid = pwd.getpwnam("asterisk").pw_uid
        gid = grp.getgrnam("asterisk").gr_gid
        for directory in ("/run/asterisk", "/var/log/asterisk", "/var/spool/asterisk", str(self.settings.directory / "asterisk")):
            Path(directory).mkdir(parents=True, exist_ok=True)
            os.chown(directory, uid, gid)
        ports = (self.bridge.agi_port, self.bridge.audio_port) if self.bridge else None
        for filename, text in asterisk_files(self.settings.value, self.settings.ami_secret, ports).items():
            path = Path("/etc/asterisk") / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            os.chown(path, 0, gid)
            path.chmod(0o640)

    def restart(self):
        with self.lock:
            self.stop()
            self.last_error = ""
            try:
                cfg = self.settings.value
                for protocol in ("UDP", "TCP"):
                    check_port(cfg["listen_address"], cfg["sip_port"], protocol, "SIP")
                check_port("127.0.0.1", 5038, "TCP", "AMI")
                if cfg.get("audio_target") == "kiosk":
                    self.bridge = IntercomBridge(cfg)
                    self.bridge.start()
                self.write_config()
                self.process = subprocess.Popen(["asterisk", "-f", "-C", "/etc/asterisk/asterisk.conf", "-U", "asterisk", "-G", "asterisk"])
                for _ in range(40):
                    if self.process.poll() is not None:
                        raise RuntimeError("Asterisk konnte nicht starten. Add-on-Protokoll prüfen.")
                    transports = self.cli("pjsip show transports")
                    if "System uptime" in self.cli("core show uptime") and all(name in transports for name in ("transport-udp", "transport-tcp")):
                        if self.bridge and any(module not in self.cli("module show like " + module) for module in ("res_agi.so", "res_audiosocket.so", "chan_audiosocket.so", "codec_resample.so")):
                            raise RuntimeError("Asterisk-Audio-Module fehlen.")
                        return
                    time.sleep(0.25)
                raise RuntimeError("Asterisk/SIP-Transport konnte nicht starten. SIP-Port, NAS-IP und Add-on-Protokoll prüfen.")
            except (OSError, RuntimeError) as exc:
                self.last_error = str(exc) if isinstance(exc, PortConflict) or (self.bridge and self.bridge.start_error) else "Asterisk/SIP-Transport konnte nicht starten. SIP-Port, NAS-IP und Add-on-Protokoll prüfen."
                self.stop()
                raise RuntimeError(self.last_error) from None

    def stop(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            self.process = None
            if self.bridge:
                self.bridge.stop()
                self.bridge = None

    @staticmethod
    def cli(command):
        # Callers use fixed commands; no user input enters the Asterisk CLI.
        try:
            result = subprocess.run(["asterisk", "-rx", command], capture_output=True, text=True, timeout=3)
            return result.stdout if result.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            return ""

    def status(self):
        running = self.process is not None and self.process.poll() is None
        registrations = self.cli("pjsip show registrations") if running else ""
        phone = self.cli("pjsip show contacts") if running else ""
        # Do not send raw CLI output, account names or secrets to browsers.
        states = []
        for line in effective_lines(self.settings.value):
            row = next((row for row in registrations.splitlines() if f"line-{line['id']}-registration/" in row), "")
            registered = " Registered" in row
            state = "deaktiviert" if not line["enabled"] else "registriert" if registered else "abgelehnt" if "Rejected" in row else "wartet"
            states.append({"id": line["id"], "label": line["label"], "phone_number": line["phone_number"],
                           "enabled": line["enabled"], "incoming_mode": line["incoming_mode"], "registered": registered, "state": state})
        selected = next((line for line in states if line["id"] == self.settings.value.get("outbound_line", "main")), {})
        phone_ready = any("100/sip:" in row and (" Avail" in row or " NonQual" in row) for row in phone.splitlines())
        return {"asterisk_running": running, "provider_registered": selected.get("registered", False),
                "telekom_registered": selected.get("registered", False), "registration_state": selected.get("state", "deaktiviert"),
                "phone_registered": phone_ready, "lines": states, "outbound_line": self.settings.value.get("outbound_line", "main"),
                "audio_target": self.settings.value.get("audio_target", "sip"),
                "media_bridge": self.bridge is not None,
                "intercom": self.bridge.status() if self.bridge else None,
                "startup_error": self.last_error}

    def probe_intercom(self):
        import asyncio
        if not self.bridge or not self.bridge.loop or not self.bridge.loop.is_running():
            raise RuntimeError("Kiosk-Audio zuerst einrichten, speichern und das Add-on neu starten.")
        future = asyncio.run_coroutine_threadsafe(self.bridge._probe(), self.bridge.loop)
        try:
            identity = future.result(timeout=6)
            return {"message": "Kiosk erreichbar, Intercom aktiviert und Schlüssel stimmt.",
                    "name": identity.get("name", "Kiosk")}
        except Exception:
            future.cancel()
            raise RuntimeError("Kiosk nicht bereit. Intercom-IP/Port, Schlüssel, Nicht stören und TLS-Einstellung am Kiosk prüfen.") from None

    @staticmethod
    def _frame(stream):
        fields = {}
        for _ in range(100):
            line = stream.readline(8192)
            if not line:
                raise RuntimeError("AMI-Verbindung wurde geschlossen.")
            line = line.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line and fields:
                return fields
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        raise RuntimeError("Ungültige AMI-Antwort.")

    def originate(self, number, line_id=None, local_test=False):
        if local_test and number != "600":
            raise ValueError("Der lokale Audio-Test darf nur Echo 600 wählen.")
        line_id = line_id or self.settings.value.get("outbound_line", "main")
        line = next((line for line in effective_lines(self.settings.value) if line["id"] == line_id), None)
        if not isinstance(number, str) or not DESTINATION.fullmatch(number) or not line or not line["enabled"] or line["incoming_mode"] != "normal":
            raise ValueError("Ungültige ausgehende Rufnummer.")
        with socket.create_connection(("127.0.0.1", 5038), timeout=5) as sock:
            sock.settimeout(5)
            with sock.makefile("rb") as stream:
                stream.readline(8192)

                def action(fields):
                    sock.sendall(("".join(f"{k}: {v}\r\n" for k, v in fields.items()) + "\r\n").encode())
                    return self._frame(stream)

                login = action({"Action": "Login", "Username": "kioskphone", "Secret": self.settings.ami_secret, "Events": "off"})
                if login.get("Response") != "Success":
                    raise RuntimeError("Lokale Asterisk-Anmeldung fehlgeschlagen.")
                native = self.settings.value.get("audio_target") == "kiosk" and self.bridge is not None
                response = action({"Action": "Originate", "Channel": "Local/s@kiosk-native-out/n" if native else "PJSIP/100", "Context": "from-phone" if local_test else "from-out-" + line_id,
                                   "Exten": number, "Priority": "1", "Timeout": "30000", "Async": "true",
                                   "CallerID": "Kiosk Satellite <100>", "ActionID": str(uuid.uuid4())})
                if response.get("Response") != "Success":
                    raise RuntimeError("Asterisk hat den Rückruf abgelehnt.")
                return {"message": "Kiosk wird angerufen. Am Kiosk annehmen; danach startet der lokale Echo-Test." if native and local_test else
                        "Kiosk wird angerufen. Am Kiosk annehmen; erst danach wird die Zielnummer gewählt." if native else
                        "Rückruf angefordert. Nimm dein SIP-Telefon 100 an; danach wird die Zielnummer gewählt."}
