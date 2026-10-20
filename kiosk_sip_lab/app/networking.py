"""Supervisor-assigned ingress and safe diagnostics for host-network listeners."""
import errno
import json
import os
import socket
from urllib.request import Request, urlopen


def ingress_port():
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        # Standalone development containers have no Supervisor.
        return 8099
    request = Request("http://supervisor/addons/self/info",
                      headers={"Authorization": "Bearer " + token})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read(524289))
        port = payload["data"]["ingress_port"]
        if payload.get("result") != "ok" or type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError()
        return port
    except Exception:
        # Never include token, response/options, or urllib exception text in logs.
        raise RuntimeError("Ingress-Port konnte nicht vom Home-Assistant-Supervisor gelesen werden. Add-on aktualisieren und neu starten.") from None


class PortConflict(RuntimeError):
    """User-facing diagnostic; contains no credentials or arbitrary CLI output."""


def check_port(address, port, protocol, label):
    kind = socket.SOCK_DGRAM if protocol == "UDP" else socket.SOCK_STREAM
    with socket.socket(socket.AF_INET, kind) as probe:
        if protocol == "TCP":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((address, port))
        except OSError as exc:
            if exc.errno == errno.EADDRINUSE:
                hint = "Im HA-Assistenten unter Heimnetz einen freien SIP-Port setzen, z. B. 5072, und am SIP-Telefon denselben Port verwenden." if label == "SIP" else "Den anderen Dienst prüfen; AMI-Port 5038 muss für dieses Add-on frei sein."
                raise PortConflict(f"{label}: {protocol}-Port {port} auf {address} ist bereits belegt. {hint}") from None
            if exc.errno == errno.EADDRNOTAVAIL:
                raise PortConflict("Die eingetragene NAS-IP ist auf HAOS nicht vorhanden. Im HA-Assistenten die tatsächliche lokale IPv4-Adresse eintragen.") from None
            raise PortConflict(f"{label}: {protocol}-Port {port} konnte nicht geöffnet werden. Add-on-Protokoll und Netzwerk prüfen.") from None
