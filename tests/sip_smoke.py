"""Container test: real PJSIP registration with fake data, no provider or calls."""
import hashlib
import os
import pwd
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.path.insert(0, "/app")
from configuration import DEFAULTS, asterisk_files


def main():
    user = pwd.getpwnam("asterisk")
    base = Path(tempfile.mkdtemp(prefix="sip-smoke-"))
    base.chmod(0o755)
    for sub in ("config", "run", "db", "spool", "log"):
        path = base / sub
        path.mkdir()
        os.chown(path, user.pw_uid, user.pw_gid)
    password = "fake-phone;secret\\with-punctuation"
    cfg = {**DEFAULTS, "phone_password": password, "listen_address": "127.0.0.1",
           "local_network": "127.0.0.1/32", "sip_port": 15070}
    files = asterisk_files(cfg, "fake-ami-secret")
    # Independent config/control socket/database; do not stop the running add-on.
    files["manager.conf"] = "[general]\nenabled=no\n"
    for old, new in (("/etc/asterisk", str(base / "config")), ("/run/asterisk", str(base / "run")),
                     ("/data/asterisk", str(base / "db")), ("/var/log/asterisk", str(base / "log")),
                     ("/var/spool/asterisk", str(base / "spool"))):
        files["asterisk.conf"] = files["asterisk.conf"].replace(old, new)
    for name, content in files.items():
        path = base / "config" / name
        path.write_text(content)
        os.chown(path, 0, user.pw_gid)
        path.chmod(0o640)
    astconf = str(base / "config" / "asterisk.conf")
    process = subprocess.Popen(["asterisk", "-f", "-C", astconf, "-U", "asterisk", "-G", "asterisk"])
    try:
        for _ in range(50):
            result = subprocess.run(["asterisk", "-C", astconf, "-rx", "core show uptime"], capture_output=True, text=True)
            if "System uptime" in result.stdout:
                break
            time.sleep(.2)
        assert process.poll() is None, "Test Asterisk stopped"
        # SIP modules can finish loading just after the control socket opens.
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.bind(("127.0.0.1", 0))
            client.settimeout(5)
            local_port = client.getsockname()[1]
            call_id = str(uuid.uuid4())
            uri = "sip:127.0.0.1:15070"

            def register(cseq, auth=""):
                msg = (f"REGISTER {uri} SIP/2.0\r\nVia: SIP/2.0/UDP 127.0.0.1:{local_port};branch=z9hG4bK{uuid.uuid4().hex};rport\r\n"
                       f"Max-Forwards: 70\r\nFrom: <sip:100@127.0.0.1>;tag=fake\r\nTo: <sip:100@127.0.0.1>\r\n"
                       f"Call-ID: {call_id}\r\nCSeq: {cseq} REGISTER\r\nContact: <sip:100@127.0.0.1:{local_port}>\r\n"
                       f"Expires: 120\r\n{auth}Content-Length: 0\r\n\r\n")
                client.sendto(msg.encode(), ("127.0.0.1", 15070))
                return client.recv(16384).decode()

            challenge = register(1)
            assert challenge.startswith("SIP/2.0 401"), challenge.splitlines()[0]
            values = dict(re.findall(r'([a-z_]+)="([^"]+)"', challenge, re.I))
            realm, nonce = values["realm"], values["nonce"]
            md5 = lambda text: hashlib.md5(text.encode()).hexdigest()
            ha1, ha2 = md5(f"100:{realm}:{password}"), md5(f"REGISTER:{uri}")
            cnonce, nc = uuid.uuid4().hex, "00000001"
            response = md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}") if "qop" in values else md5(f"{ha1}:{nonce}:{ha2}")
            auth = f'Authorization: Digest username="100", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{response}", algorithm=MD5'
            if "qop" in values:
                auth += f', qop=auth, nc={nc}, cnonce="{cnonce}"'
            answer = register(2, auth + "\r\n")
            assert answer.startswith("SIP/2.0 200"), answer.splitlines()[0]
        dialplan = subprocess.check_output(["asterisk", "-C", astconf, "-rx", "dialplan show 600@from-phone"], text=True)
        assert "Echo()" in dialplan, dialplan
        print("PASS: real Asterisk startup, authenticated local SIP REGISTER, password punctuation and echo dialplan. No external call made.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
