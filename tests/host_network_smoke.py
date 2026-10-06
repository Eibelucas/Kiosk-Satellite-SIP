"""Container-only regression: occupied legacy ports + assigned HA ingress."""
import json
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


def main():
    with socket.socket() as old_web, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as old_sip, socket.socket() as chosen:
        old_web.bind(("0.0.0.0", 8099)); old_web.listen(1)
        old_sip.bind(("127.0.0.1", 5070))
        chosen.bind(("127.0.0.1", 0)); assigned = chosen.getsockname()[1]
        chosen.close()
        class Supervisor(BaseHTTPRequestHandler):
            requests = 0
            def do_GET(self):
                assert self.path == "/addons/self/info"
                assert self.headers.get("Authorization") == "Bearer fake-test-token"
                Supervisor.requests += 1
                data = json.dumps({"result":"ok", "data":{"ingress_port":assigned}}).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(data)
            def log_message(self, *args): pass
        api = HTTPServer(("127.0.0.1", 80), Supervisor)
        threading.Thread(target=api.serve_forever, daemon=True).start()
        with open("/etc/hosts", "a") as hosts:
            hosts.write("\n127.0.0.1 supervisor\n")
        process = subprocess.Popen(["/opt/venv/bin/python", "/app/run.py"], cwd="/app",
                                   env={**os.environ,"SUPERVISOR_TOKEN":"fake-test-token"},
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            ready = False
            for _ in range(60):
                assert process.poll() is None, "Gateway exited with occupied SIP port"
                try:
                    urlopen(f"http://127.0.0.1:{assigned}/setup", timeout=.5)
                except HTTPError as exc:
                    # Actual ingress rejects non-Supervisor source even during recovery.
                    assert exc.code == 403
                    ready = True
                except OSError:
                    pass
                if ready and Path("/run/kiosk-sip-ingress-port").exists(): break
                time.sleep(.1)
            assert ready and int(Path("/run/kiosk-sip-ingress-port").read_text()) == assigned
            assert Supervisor.requests == 1
            process.terminate()
            output = process.communicate(timeout=10)[0]
            assert "bereits belegt" in output and "HA-Einrichtung bleibt erreichbar" in output
            assert "fake-test-token" not in output and "Traceback" not in output
            print("PASS: assigned ingress with occupied 8099/5070, setup recovery, source restriction, clean shutdown.")
        finally:
            if process.poll() is None:
                process.kill(); process.communicate(timeout=5)
            api.shutdown(); api.server_close()


if __name__ == "__main__": main()
