import importlib.util
import io
import json
import re
import sys
from pathlib import Path

import pytest
import yaml
from werkzeug.test import Client
from werkzeug.wrappers import Response

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kiosk_sip" / "app"))
from configuration import Settings, asterisk_files, validate
from server import IngressOnly, LanOnly, create_app


def valid(**changes):
    return {"enabled": True, "phone_number": "+4921611234567", "listen_address": "192.168.2.20",
            "local_network": "192.168.2.0/24", "phone_password": "fake-phone-secret-123",
            "lan_enabled": True, "web_password": "fake-kiosk-secret-123", **changes}


class FakePbx:
    def __init__(self):
        self.restarts = 0
        self.calls = []
        self.state = {"asterisk_running": True, "telekom_registered": True, "phone_registered": True,
                      "registration_state": "registriert", "media_bridge": False}

    def restart(self):
        self.restarts += 1

    def status(self):
        return self.state

    def originate(self, number):
        self.calls.append(number)
        return {"message": "Rückruf angefordert"}


@pytest.fixture
def instance(tmp_path):
    settings = Settings(tmp_path)
    settings.save(valid())
    pbx = FakePbx()
    app = create_app(settings, pbx)
    app.config["TESTING"] = True
    return settings, pbx, app


def trusted(client, method, path, **kwargs):
    return client.open(path, method=method, environ_overrides={"kiosk.ingress": True}, **kwargs)


def token(client):
    return trusted(client, "GET", "/api/setup").json["csrf"]


def test_repository_and_addon_metadata():
    repository = yaml.safe_load((ROOT / "repository.yaml").read_text())
    addon = yaml.safe_load((ROOT / "kiosk_sip" / "config.yaml").read_text())
    assert repository["url"] == "https://github.com/Eibelucas/Kiosk-Satellite-SIP"
    assert addon["arch"] == ["amd64"]
    assert addon["ingress"] and addon["host_network"]
    assert addon["ingress_port"] == 8099
    assert "image" not in addon  # Local build, no unpublished registry image.
    assert not addon.get("hassio_api", False)


@pytest.mark.parametrize("change", [
    {"phone_number": "021611234567"}, {"phone_number": "+49216\n[evil]"},
    {"listen_address": "0.0.0.0"}, {"listen_address": "8.8.8.8"},
    {"listen_address": "192.168.3.20"}, {"sip_port": True}, {"sip_port": 8099},
    {"phone_password": "short"}, {"phone_password": "hello\r\n[evil]"},
    {"provider": "business"}, {"auth_mode": "password", "auth_username": "TEST@example.com"},
    {"external_address": "192.168.2.1"}, {"lan_enabled": True, "web_password": ""},
    {"contacts": [{"name": "Max", "number": "123\r\nAction: Command"}]},
    {"enabled": "true"}, {"web_password_hash": "injected"},
])
def test_reject_invalid_and_injected_configuration(change):
    with pytest.raises(ValueError):
        validate(valid(**change))


def test_secrets_preserved_redacted_and_permissions(tmp_path):
    settings = Settings(tmp_path)
    settings.save(valid(auth_mode="password", auth_username="fake@t-online.de", auth_password="fake-telekom-secret"))
    public = json.dumps(settings.public())
    assert "fake-telekom-secret" not in public and "fake-phone-secret" not in public
    assert "web_password_hash" not in public
    assert settings.path.stat().st_mode & 0o777 == 0o600
    settings.save({"auth_password": "", "phone_password": "", "web_password": ""})
    assert settings.value["auth_password"] == "fake-telekom-secret"
    settings.save({"auth_mode": "access"})
    assert settings.value["auth_password"] == ""


def test_generated_pbx_isolated_ami_and_no_inbound_outbound_context(tmp_path):
    cfg = validate(valid(auth_mode="password", auth_username="fake@t-online.de", auth_password="pass;with\\punctuation"))
    files = asterisk_files(cfg, "fake-ami-secret")
    assert "bindaddr=127.0.0.1" in files["manager.conf"]
    assert "write=originate" in files["manager.conf"]
    assert "write=all" not in files["manager.conf"]
    assert "pass\\;with\\\\punctuation" in files["pjsip.conf"]
    assert "server_uri=sip:tel.t-online.de\n" in files["pjsip.conf"]
    assert "line=yes\nendpoint=telekom" in files["pjsip.conf"]
    inbound = files["extensions.conf"].split("[from-telekom]")[1]
    assert "Dial(PJSIP/100" in inbound and "@telekom" not in inbound
    assert "Echo()" in files["extensions.conf"]


def test_ingress_socket_source_required_and_headers_cannot_spoof(instance):
    _, _, app = instance
    client = Client(IngressOnly(app), Response)
    assert client.get("/api/setup", environ_overrides={"REMOTE_ADDR": "192.168.2.50"},
                      headers={"X-Ingress-Path": "/fake", "X-Forwarded-For": "172.30.32.2"}).status_code == 403
    assert client.get("/api/setup", environ_overrides={"REMOTE_ADDR": "172.30.32.2"}).status_code == 200


def test_lan_login_and_setup_denied(instance):
    _, _, app = instance
    client = app.test_client()
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/setup", headers={"X-Ingress-Path": "/fake"}).status_code == 403
    response = client.get("/login")
    csrf = re.search(r'name="csrf" value="([^"]+)"', response.text).group(1)
    assert client.post("/login", data={"username": "kiosk", "password": "fake-kiosk-secret-123"}).status_code == 403
    assert client.post("/login", data={"csrf": csrf, "username": "kiosk", "password": "fake-kiosk-secret-123"}).status_code == 302
    assert client.get("/api/status").status_code == 200
    assert client.get("/api/setup").status_code == 403
    assert "fake-telekom-secret" not in client.get("/").text


def test_login_rate_limited(instance):
    _, _, app = instance
    client = app.test_client()
    response = client.get("/login")
    csrf = re.search(r'name="csrf" value="([^"]+)"', response.text).group(1)
    for _ in range(8):
        assert client.post("/login", data={"csrf": csrf, "username": "wrong", "password": "wrong"}).status_code == 200
    assert client.post("/login", data={"csrf": csrf, "username": "kiosk", "password": "fake-kiosk-secret-123"}).status_code == 429


def test_ingress_relative_assets_and_csrf(instance):
    _, _, app = instance
    client = app.test_client()
    page = trusted(client, "GET", "/setup")
    assert 'src="static/setup.js"' in page.text
    assert 'href="static/style.css"' in page.text
    assert trusted(client, "POST", "/api/setup", json=valid()).status_code == 403
    assert trusted(client, "POST", "/api/setup", json=[], headers={"X-CSRF-Token": token(client)}).status_code == 400


def test_configuration_does_not_call_and_restart_is_explicit(instance):
    settings, pbx, app = instance
    client = app.test_client()
    response = trusted(client, "POST", "/api/setup", json={"contacts": [{"name": "<script>", "number": "+4921611234567"}]},
                       headers={"X-CSRF-Token": token(client)})
    assert response.status_code == 200 and pbx.restarts == 1
    assert pbx.calls == []
    assert "auth_password" not in trusted(client, "GET", "/api/setup").json["config"]


def test_callback_requires_registration_and_valid_number(instance):
    settings, pbx, app = instance
    client = app.test_client()
    headers = {"X-CSRF-Token": token(client)}
    for body in ([], None, {"number": "123\r\nAction: Command"}, {"number": 123}):
        assert trusted(client, "POST", "/api/call", json=body, headers=headers).status_code == 400
    pbx.state["phone_registered"] = False
    assert trusted(client, "POST", "/api/call", json={"number": "+4921611234567"}, headers=headers).status_code == 409
    pbx.state["phone_registered"] = True
    pbx.state["telekom_registered"] = False
    assert trusted(client, "POST", "/api/call", json={"number": "+4921611234567"}, headers=headers).status_code == 409
    pbx.state["telekom_registered"] = True
    assert trusted(client, "POST", "/api/call", json={"number": "+4921611234567"}, headers=headers).status_code == 200
    assert pbx.calls == ["+4921611234567"]
    assert trusted(client, "POST", "/api/call", json={"number": "+4921611234567"}, headers=headers).status_code == 429


def test_password_change_invalidates_lan_session(instance):
    settings, _, app = instance
    client = app.test_client()
    csrf = re.search(r'name="csrf" value="([^"]+)"', client.get("/login").text).group(1)
    client.post("/login", data={"csrf": csrf, "username": "kiosk", "password": "fake-kiosk-secret-123"})
    assert client.get("/api/status").status_code == 200
    settings.save({"web_password": "a-different-fake-secret"})
    assert client.get("/api/status").status_code == 401
