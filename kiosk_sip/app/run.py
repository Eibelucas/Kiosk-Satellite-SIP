import json
import signal
import threading
import time
from pathlib import Path

from waitress import create_server

from configuration import Settings
from pbx import Pbx
from server import IngressOnly, LanOnly, create_app


def main():
    settings = Settings("/data")
    options_file = Path("/data/options.json")
    options = json.loads(options_file.read_text()) if options_file.exists() else {}
    port = options.get("gateway_port", 8088)
    if type(port) is not int or not 1024 <= port <= 65535 or port in {5038, 5070, 8099, settings.value["sip_port"]}:
        raise ValueError("Ungültiger oder bereits für SIP/Ingress verwendeter Gateway-Port.")
    pbx = Pbx(settings)
    pbx.restart()
    app = create_app(settings, pbx, port)
    ingress_server = create_server(IngressOnly(app), host="0.0.0.0", port=8099, threads=8)
    servers = [ingress_server]
    if settings.value["lan_enabled"]:
        servers.append(create_server(LanOnly(app), host=settings.value["listen_address"], port=port, threads=8))
    for server in servers:
        threading.Thread(target=server.run, daemon=True).start()
    stopping = threading.Event()

    def stop(_sig, _frame):
        stopping.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print("SIP Gateway bereit. Einrichtung über Home Assistant: Weboberfläche öffnen.")
    try:
        while not stopping.wait(1):
            if pbx.process.poll() is not None:
                raise RuntimeError("Asterisk wurde beendet; das Add-on muss neu starten.")
    finally:
        for server in servers:
            server.close()
        pbx.stop()


if __name__ == "__main__":
    main()
