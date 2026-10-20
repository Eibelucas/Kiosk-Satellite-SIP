import copy
import json
import os
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "kiosk_sip_lab" / "app"
sys.path.insert(0,str(APP))
from configuration import Settings, asterisk_files
from lab import LabStore, blank, sample, validate_draft
from lab_server import create_app
from lab_pbx import LabPbx

def configured():
    value=blank()
    value["connections"]=[{"id":"account","name":"Example account","provider":"custom","enabled":True,"auth_mode":"password",
                           "auth_username":"fake-user","auth_password":"fake-provider-secret","registrar":"sip.example.invalid","domain":"example.invalid","transport":"udp"}]
    value["numbers"]=[{"id":"number","name":"Main","number":"+12025550100","connection_id":"account","incoming_mode":"normal","incoming_devices":["101"]}]
    value["devices"]=[{"id":"hall","name":"Hall","extension":"101","password":"fake-device-secret-123","enabled":True,"address":"192.168.50.21","room":"Entrance"}]
    value["network"].update(listen_address="192.168.50.10",local_network="192.168.50.0/24")
    value["outbound_number"]="number"
    return value

def public_request(store):
    value=store.public()["draft"]
    for section in ("connections","numbers","devices"):
        for row in value[section]:
            for key in list(row):
                if key.endswith("_set"): row.pop(key)
    for section in ("audio","web"):
        for key in list(value[section]):
            if key.endswith("_set"): value[section].pop(key)
    return value

def test_empty_and_sample_are_safe(tmp_path):
    store=LabStore(tmp_path)
    assert store.value==blank()
    assert store.applied["runtime_enabled"] is False
    demo=validate_draft(sample(),blank())
    assert demo["demo"] and not demo["runtime_enabled"]
    assert all(not c["enabled"] for c in demo["connections"])
    demo["runtime_enabled"]=True
    with pytest.raises(ValueError,match="Beispieldaten"): validate_draft(demo,blank())

def test_secrets_redacted_and_preserved(tmp_path):
    store=LabStore(tmp_path);value=configured()
    value["audio"]["phone_password"]="fake-phone-secret-123"
    value["audio"]["intercom_key"]="fake-intercom-secret-123"
    value["web"]["web_password"]="fake-web-secret-123"
    value["numbers"][0]["announcement_pin"]="123456"
    store.save(value,0)
    public=store.public()
    encoded=json.dumps(public)
    for secret in ("fake-provider-secret","fake-device-secret-123","fake-phone-secret-123","fake-intercom-secret-123","fake-web-secret-123","123456"):
        assert secret not in encoded
    assert public["draft"]["connections"][0]["auth_password_set"]
    request=public_request(store);request["connections"][0]["name"]="Renamed account"
    store.save(request,1)
    assert store.value["connections"][0]["auth_password"]=="fake-provider-secret"
    assert store.value["devices"][0]["password"]=="fake-device-secret-123"
    request=public_request(store);request["connections"][0]["auth_username"]="new-user";request["devices"][0]["extension"]="102";request["numbers"][0]["incoming_devices"]=["102"]
    store.save(request,2)
    assert not store.value["connections"][0]["auth_password"]
    assert not store.value["devices"][0]["password"]
    assert os.stat(store.path).st_mode & 0o077 == 0

def test_stale_revision_and_relations(tmp_path):
    store=LabStore(tmp_path);store.save(configured(),0)
    with pytest.raises(RuntimeError,match="anderen Fenster"): store.save(configured(),0)
    request=public_request(store);request["connections"]=[]
    with pytest.raises(ValueError,match="SIP-Zugang"): store.save(request,1)
    request=public_request(store);request["devices"]=[]
    with pytest.raises(ValueError,match="Klingelziele"): store.save(request,1)
    assert store.revision==1
    assert LabStore(tmp_path).value==store.value

@pytest.mark.parametrize("change",[
    lambda d:d["connections"][0].update(provider=[]),
    lambda d:d["numbers"][0].update(incoming_mode=[]),
    lambda d:d["numbers"][0].update(incoming_devices=[{}]),
    lambda d:d.update(runtime_enabled="true"),
    lambda d:d["network"].update(sip_port=True),
    lambda d:d["devices"].append({**d["devices"][0],"id":"other"}),
])
def test_bad_drafts_rejected(change):
    value=configured();change(value)
    with pytest.raises((ValueError,TypeError)): validate_draft(value,blank())

def test_compile_separate_services(tmp_path):
    store=LabStore(tmp_path);store.save(configured(),0)
    settings=Settings(tmp_path)
    settings.save(store.compile())
    files=asterisk_files(settings.value,"fake-ami-secret")
    assert "port=5039" in files["manager.conf"]
    assert "rtpstart=30200\nrtpend=30299" in files["rtp.conf"]
    assert "bind=192.168.50.10:5083" in files["pjsip.conf"]
    assert "PJSIP/101" in files["extensions.conf"]
    for port in (5038,5039,5053,5070,8088,8092,8093):
        store.value["network"]["sip_port"]=port
        with pytest.raises(ValueError,match="eigenen SIP-Port"):store.compile()

def test_disabled_incomplete_accounts_do_not_block_active_config(tmp_path):
    store=LabStore(tmp_path);value=configured()
    value["connections"].append({"id":"later","name":"Later","provider":"custom","enabled":False,"auth_mode":"password"})
    value["numbers"].append({"id":"later_number","name":"Later","number":"+12025550101","connection_id":"later"})
    store.save(value,0)
    assert len(store.compile()["lines"])==1

class Pbx:
    def __init__(self): self.started=0;self.stopped=0;self.process=None
    def restart(self): self.started+=1
    def stop(self): self.stopped+=1
    def status(self): return {"asterisk_running":False,"lines":[],"devices":[],"media_bridge":False}

@pytest.fixture
def app(tmp_path):
    settings=Settings(tmp_path);pbx=Pbx();app=create_app(settings,pbx)
    app.testing=True
    app.config["TEST_SETTINGS"]=settings;app.config["TEST_PBX"]=pbx
    return app

def client(app):
    c=app.test_client();response=c.get("/",environ_overrides={"kiosk.ingress":True})
    assert response.status_code==200
    with c.session_transaction() as s: token=s["csrf"]
    return c,{"X-CSRF-Token":token},{"kiosk.ingress":True}

def test_api_requires_ingress_and_csrf(app):
    c=app.test_client()
    assert c.get("/api/setup/lab").status_code==403
    c,headers,environ=client(app)
    assert c.post("/api/setup/lab",json={},environ_overrides=environ).status_code==403
    assert c.post("/api/setup",json={},headers=headers,environ_overrides=environ).status_code==405
    assert "script-src 'self'" in c.get("/",environ_overrides=environ).headers["Content-Security-Policy"]

def test_drafts_do_not_start_pbx_and_apply_is_explicit(app):
    c,headers,environ=client(app)
    body={"draft":configured(),"revision":0}
    response=c.post("/api/setup/lab",json=body,headers=headers,environ_overrides=environ)
    assert response.status_code==200
    pbx=app.config["TEST_PBX"]
    assert pbx.started==0 and pbx.stopped==0
    response=c.post("/api/setup/lab/apply",json={"revision":1},headers=headers,environ_overrides=environ)
    assert response.status_code==200
    assert pbx.started==0 and pbx.stopped==1
    value=configured();value["runtime_enabled"]=True
    assert c.post("/api/setup/lab",json={"draft":value,"revision":1},headers=headers,environ_overrides=environ).status_code==200
    assert pbx.started==0
    assert c.post("/api/setup/lab/apply",json={"revision":2},headers=headers,environ_overrides=environ).status_code==200
    assert pbx.started==1 and app.config["TEST_SETTINGS"].lab_enabled
    assert c.post("/api/setup/lab/reset",json={"revision":2,"sample":True},headers=headers,environ_overrides=environ).status_code==409
    assert c.post("/api/setup/lab/apply",json={"revision":1},headers=headers,environ_overrides=environ).status_code==409

def test_no_runtime_from_fresh_container_settings(tmp_path,monkeypatch):
    settings=Settings(tmp_path)
    pbx=LabPbx(settings)
    monkeypatch.setattr("pbx.subprocess.Popen",lambda *a,**k:pytest.fail("Asterisk must not launch"))
    pbx.restart()
    assert pbx.process is None

def test_template_has_no_wizard_or_external_assets(app):
    c,_,environ=client(app)
    text=c.get("/",environ_overrides=environ).text
    assert "lab.css" in text and "lab.js" in text
    assert "wizard-step" not in text
    assert "https://" not in text
