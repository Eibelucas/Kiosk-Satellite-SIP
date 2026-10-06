import json
import signal
import threading
from pathlib import Path

from waitress import create_server

from configuration import Settings
from pbx import Pbx
from networking import ingress_port
from server import IngressOnly, LanOnly, create_app


def start_services(settings, pbx, port, ha_port):
    app = create_app(settings, pbx, port, ha_port)
    servers = []
    try:
        try:
            servers.append(create_server(IngressOnly(app), host="0.0.0.0", port=ha_port, threads=8))
        except OSError:
            raise RuntimeError(f"Home-Assistant-Ingress-Port {ha_port} konnte nicht geöffnet werden. Add-on neu starten und andere Dienste prüfen.") from None
        if settings.value["lan_enabled"]:
            try:
                servers.append(create_server(LanOnly(app), host=settings.value["listen_address"], port=port, threads=8))
            except OSError:
                app.config["LAN_ERROR"] = f"Kiosk-Webseite auf Port {port} konnte nicht starten. NAS-IP und Gateway-Port prüfen; unter Add-on-Konfiguration einen freien Gateway-Port setzen und neu starten. Die HA-Einrichtung bleibt erreichbar."
                print(app.config["LAN_ERROR"], flush=True)
        for server in servers:
            threading.Thread(target=server.run, daemon=True).start()
        try:
            pbx.restart()
        except (OSError, RuntimeError):
            print(getattr(pbx, "last_error", "") or "Asterisk konnte nicht starten. Add-on-Protokoll prüfen.", flush=True)
            print("HA-Einrichtung bleibt erreichbar. SIP-Port/NAS-IP korrigieren und speichern.", flush=True)
        return servers
    except Exception:
        for server in servers:
            server.close()
        pbx.stop()
        raise


def main():
    settings = Settings("/data")
    options_file = Path("/data/options.json")
    options = json.loads(options_file.read_text()) if options_file.exists() else {}
    port = options.get("gateway_port", 8088)
    ha_port = ingress_port()
    if type(port) is not int or not 1024 <= port <= 65535 or port in {5038, ha_port, settings.value["sip_port"]}:
        raise ValueError("Ungültiger oder bereits für SIP/Ingress verwendeter Gateway-Port.")
    pbx = Pbx(settings)
    stopping = threading.Event()

    def stop(_sig, _frame):
        stopping.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    servers = []
    try:
        servers = start_services(settings, pbx, port, ha_port)
        Path("/run/kiosk-sip-ingress-port").write_text(str(ha_port))
        print("HA-Einrichtung bereit: Weboberfläche öffnen. SIP-Status im Assistenten prüfen.", flush=True)
        while not stopping.wait(1):
            if pbx.process is not None and pbx.process.poll() is not None:
                raise RuntimeError("Asterisk wurde beendet; das Add-on muss neu starten.")
    finally:
        for server in servers:
            server.close()
        pbx.stop()


if __name__ == "__main__":
    main()
