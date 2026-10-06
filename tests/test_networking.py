import errno
import io
import json
import socket

import pytest

import networking
from configuration import Settings
from pbx import Pbx
from run import start_services
from server import create_app


def test_supervisor_port_and_token_not_exposed(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "fake-private-token")
    seen = []
    def reply(request, timeout):
        seen.append((request.full_url, request.get_header("Authorization"), timeout))
        return io.BytesIO(json.dumps({"result": "ok", "data": {"ingress_port": 18123}}).encode())
    monkeypatch.setattr(networking, "urlopen", reply)
    assert networking.ingress_port() == 18123
    assert seen == [("http://supervisor/addons/self/info", "Bearer fake-private-token", 10)]


@pytest.mark.parametrize("response", [b"bad", b'{"result":"error"}', b'{"result":"ok","data":{"ingress_port":0}}', b'{"result":"ok","data":{"ingress_port":true}}'])
def test_no_fixed_port_fallback_on_supervisor_failure(monkeypatch, response):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "fake-private-token")
    monkeypatch.setattr(networking, "urlopen", lambda *a, **k: io.BytesIO(response))
    with pytest.raises(RuntimeError) as error:
        networking.ingress_port()
    assert "fake-private-token" not in str(error.value)
    assert "Supervisor" in str(error.value)


def test_standalone_ingress(monkeypatch):
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    assert networking.ingress_port() == 8099


@pytest.mark.parametrize("protocol,kind", [("UDP", socket.SOCK_DGRAM), ("TCP", socket.SOCK_STREAM)])
def test_real_occupied_sip_socket_is_reported(protocol, kind):
    with socket.socket(socket.AF_INET, kind) as occupied:
        occupied.bind(("127.0.0.1", 0))
        if kind == socket.SOCK_STREAM:
            occupied.listen(1)
        with pytest.raises(networking.PortConflict, match="bereits belegt") as error:
            networking.check_port("127.0.0.1", occupied.getsockname()[1], protocol, "SIP")
        assert "HA-Assistenten" in str(error.value)


def test_failed_pbx_does_not_hide_setup_and_can_retry(tmp_path, monkeypatch):
    settings = Settings(tmp_path)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        settings.value["sip_port"] = occupied.getsockname()[1]
        pbx = Pbx(settings)
        with pytest.raises(RuntimeError, match="bereits belegt"):
            pbx.restart()
        assert pbx.process is None and not pbx.status()["asterisk_running"]
        app = create_app(settings, pbx)
        client = app.test_client()
        assert client.get("/setup", environ_overrides={"kiosk.ingress": True}).status_code == 200
        state = client.get("/api/status", environ_overrides={"kiosk.ingress": True}).json
        assert "bereits belegt" in state["startup_error"]
        assert settings.ami_secret not in json.dumps(state)
    checked = []
    monkeypatch.setattr("pbx.check_port", lambda *args: checked.append(args))
    monkeypatch.setattr(pbx, "write_config", lambda: None)
    monkeypatch.setattr("pbx.subprocess.Popen", lambda *a, **k: type("Alive", (), {"poll": lambda self: None})())
    monkeypatch.setattr(pbx, "cli", lambda command: "transport-udp transport-tcp" if "transports" in command else "System uptime")
    pbx.restart()
    assert pbx.last_error == "" and pbx.status()["asterisk_running"]
    assert len(checked) == 3


def test_ingress_and_lan_startup_failures_cleanup(tmp_path, monkeypatch):
    settings = Settings(tmp_path)
    settings.value["lan_enabled"] = True
    pbx = Pbx(settings)
    class FakeServer:
        closed = False
        def run(self): pass
        def close(self): self.closed = True
    server = FakeServer()
    seen = []
    def create(app, host, port, threads):
        seen.append((app, port))
        if port == 8088:
            raise OSError(errno.EADDRINUSE, "occupied")
        return server
    monkeypatch.setattr("run.create_server", create)
    monkeypatch.setattr(pbx, "restart", lambda: None)
    servers = start_services(settings, pbx, 8088, 18123)
    assert servers == [server] and not server.closed
    assert "HA-Einrichtung bleibt erreichbar" in seen[0][0].app.config["LAN_ERROR"]
    def fail(*a, **k): raise OSError(errno.EADDRINUSE, "occupied")
    monkeypatch.setattr("run.create_server", fail)
    with pytest.raises(RuntimeError, match="18123"):
        start_services(settings, pbx, 8088, 18123)
    assert pbx.process is None


def test_dynamic_ingress_cannot_become_sip_port(tmp_path):
    # Conflict is rejected before any persistent configuration or PBX restart.
    settings = Settings(tmp_path)
    pbx = Pbx(settings)
    client = create_app(settings, pbx, ingress_port=18123).test_client()
    trusted = {"kiosk.ingress": True}
    token = client.get("/api/setup", environ_overrides=trusted).json["csrf"]
    response = client.post("/api/setup", json={"sip_port": 18123},
                           headers={"X-CSRF-Token": token}, environ_overrides=trusted)
    assert response.status_code == 400
    assert not settings.path.exists()
