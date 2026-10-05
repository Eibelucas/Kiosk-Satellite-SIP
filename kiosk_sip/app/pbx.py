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


class Pbx:
    def __init__(self, settings):
        self.settings = settings
        self.process = None
        self.lock = threading.RLock()

    def write_config(self):
        import pwd
        uid = pwd.getpwnam("asterisk").pw_uid
        gid = grp.getgrnam("asterisk").gr_gid
        for directory in ("/run/asterisk", "/var/log/asterisk", "/var/spool/asterisk", str(self.settings.directory / "asterisk")):
            Path(directory).mkdir(parents=True, exist_ok=True)
            os.chown(directory, uid, gid)
        for filename, text in asterisk_files(self.settings.value, self.settings.ami_secret).items():
            path = Path("/etc/asterisk") / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            os.chown(path, 0, gid)
            path.chmod(0o640)

    def restart(self):
        with self.lock:
            self.stop()
            self.write_config()
            self.process = subprocess.Popen(["asterisk", "-f", "-C", "/etc/asterisk/asterisk.conf", "-U", "asterisk", "-G", "asterisk"])
            for _ in range(40):
                if self.process.poll() is not None:
                    raise RuntimeError("Asterisk konnte nicht starten. Add-on-Protokoll prüfen.")
                if "System uptime" in self.cli("core show uptime"):
                    return
                time.sleep(0.25)
            raise RuntimeError("Asterisk startet noch. Status und Add-on-Protokoll prüfen.")

    def stop(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)

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
                "media_bridge": False}

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

    def originate(self, number, line_id=None):
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
                response = action({"Action": "Originate", "Channel": "PJSIP/100", "Context": "from-out-" + line_id,
                                   "Exten": number, "Priority": "1", "Timeout": "30000", "Async": "true",
                                   "CallerID": "Kiosk Satellite <100>", "ActionID": str(uuid.uuid4())})
                if response.get("Response") != "Success":
                    raise RuntimeError("Asterisk hat den Rückruf abgelehnt.")
                return {"message": "Rückruf angefordert. Nimm dein SIP-Telefon 100 an; danach wird die Zielnummer gewählt."}
