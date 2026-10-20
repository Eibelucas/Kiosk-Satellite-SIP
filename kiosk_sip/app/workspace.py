"""Normalized administration drafts with migration of existing gateway settings."""
import copy
import ipaddress
import json
import re
import threading
from datetime import datetime, timezone

from configuration import atomic_json, secret_value, DEFAULTS, ACCOUNT_DEFAULTS, effective_lines, ACCOUNT_FIELDS, ANNOUNCEMENT_DEFAULTS, incoming_devices
from providers import PROVIDERS

CONNECTION_KEYS = {"id","name","provider","enabled","auth_mode","auth_username","auth_password",*ACCOUNT_DEFAULTS}
NUMBER_KEYS = {"id","name","number","connection_id","incoming_mode","incoming_devices","announcement_callers","announcement_pin","announcement_clear_pin","announcement_auto_answer","announcement_max_seconds"}
DEVICE_KEYS = {"id","name","extension","password","enabled","address","room"}
CONTACT_KEYS = {"id","name","number","room","favorite"}
NETWORK_KEYS = {"listen_address","local_network","external_address","sip_port"}
AUDIO_KEYS = {"phone_password","audio_target","kiosk_address","kiosk_port","intercom_port","intercom_key"}
WEB_KEYS = {"lan_enabled","web_username","web_password"}
ROOT_KEYS = {"schema_version","demo","runtime_enabled","connections","numbers","devices","contacts","network","audio","web","outbound_number"}

def blank():
    return {"schema_version":1,"demo":False,"runtime_enabled":False,"connections":[],"numbers":[],"devices":[],"contacts":[],
            "network":{"listen_address":"","local_network":"","external_address":"","sip_port":5070},
            "audio":{"phone_password":"","audio_target":"sip","kiosk_address":"","kiosk_port":2324,"intercom_port":8090,"intercom_key":""},
            "web":{"lan_enabled":False,"web_username":"kiosk","web_password":""},"outbound_number":""}

def sample():
    draft=blank()
    draft["demo"]=True
    draft["network"].update(listen_address="192.0.2.10",local_network="192.0.2.0/24")
    draft["connections"]=[{"id":"sample_account","name":"Beispiel-Anschluss","provider":"custom","enabled":False,"auth_mode":"password","auth_username":"sample-user","registrar":"sip.example.invalid","domain":"example.invalid","auth_password":"","transport":"udp"}]
    draft["numbers"]=[{"id":"sample_number","name":"Zentrale","number":"+49305550100","connection_id":"sample_account","incoming_mode":"normal","incoming_devices":["101","102"],"announcement_callers":[],"announcement_pin":"","announcement_auto_answer":False,"announcement_max_seconds":180}]
    draft["devices"]=[{"id":"sample_hall","name":"Flur","extension":"101","password":"","enabled":True,"address":"192.0.2.21","room":"Eingang"},
                      {"id":"sample_living","name":"Wohnzimmer","extension":"102","password":"","enabled":True,"address":"192.0.2.22","room":"Wohnzimmer"}]
    draft["contacts"]=[{"id":"sample_contact","name":"Beispielkontakt","number":"+49305550101","room":"","favorite":True}]
    draft["outbound_number"]="sample_number"
    return draft

def text(value,label,limit=256):
    if not isinstance(value,str) or len(value)>limit:
        raise ValueError(label+": ungültiger Text.")
    return secret_value(value.strip(),label)

def boolean(value,label):
    if type(value) is not bool: raise ValueError(label+": ungültiger Schalter.")
    return value

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,23}",value):
        raise ValueError("Ungültige Eintrags-ID.")
    return value

def objects(raw,keys,limit,label):
    if not isinstance(raw,list) or len(raw)>limit: raise ValueError(label+": zu viele Einträge.")
    seen=set()
    for item in raw:
        if not isinstance(item,dict) or set(item)-keys: raise ValueError(label+": ungültiger Eintrag.")
        key=identifier(item.get("id"))
        if key in seen: raise ValueError(label+": doppelte ID.")
        seen.add(key)
    return raw

def retained(raw,old,key,label,identity=True):
    value=raw.get(key,"")
    if not isinstance(value,str): raise ValueError(label+": ungültiges Passwort.")
    return secret_value(value,label) if value else (old.get(key,"") if identity else "")

def validate_draft(body,previous):
    if not isinstance(body,dict) or set(body)-ROOT_KEYS: raise ValueError("Ungültiger Entwurf.")
    if body.get("schema_version")!=1: raise ValueError("Unbekannte Entwurfsversion.")
    draft=blank()
    for key in ("demo","runtime_enabled"): draft[key]=boolean(body.get(key,False),key)
    if draft["demo"] and draft["runtime_enabled"]: raise ValueError("Beispieldaten können keinen Telefonserver aktivieren.")
    old_connections={item["id"]:item for item in previous.get("connections",[])}
    for raw in objects(body.get("connections",[]),CONNECTION_KEYS,8,"SIP-Zugänge"):
        item={**ACCOUNT_DEFAULTS,"provider":"custom","auth_mode":"password","auth_username":"","enabled":False,**raw}
        if not isinstance(item["provider"],str) or item["provider"] not in PROVIDERS or not isinstance(item["auth_mode"],str) or item["auth_mode"] not in {"password","access"}: raise ValueError("SIP-Profil und Anmeldeart prüfen.")
        item["name"]=text(item.get("name",""),"Zugangsname",80)
        if not item["name"]: raise ValueError("SIP-Zugang benennen.")
        item["enabled"]=boolean(item["enabled"],"SIP-Zugang aktiv")
        for key in ("auth_username",*ACCOUNT_DEFAULTS): item[key]=text(item.get(key,""),key)
        old=old_connections.get(item["id"],{})
        same=all(item.get(k)==old.get(k) for k in ("provider","auth_username","registrar","domain","client_user"))
        item["auth_password"]=retained(raw,old,"auth_password","SIP-Passwort",same)
        draft["connections"].append(item)
    old_devices={item["id"]:item for item in previous.get("devices",[])}
    extensions=set()
    for raw in objects(body.get("devices",[]),DEVICE_KEYS,100,"Kiosks"):
        item={key:text(raw.get(key,""),key,80) for key in ("id","name","extension","address","room")}
        if not item["name"]: raise ValueError("Kiosk benennen.")
        if not re.fullmatch(r"1[0-9]{2}",item["extension"]) or (item["extension"]=="100" and old_devices.get(item["id"],{}).get("extension")!="100") or item["extension"] in extensions: raise ValueError("Kiosks benötigen eindeutige Nebenstellen von 101 bis 199.")
        extensions.add(item["extension"])
        if item["address"]:
            try:
                ip=ipaddress.IPv4Address(item["address"])
                if ip.is_multicast or ip.is_unspecified: raise ValueError()
            except ValueError: raise ValueError("Kiosk-Adresse muss eine IPv4-Adresse sein.") from None
        item["enabled"]=boolean(raw.get("enabled",True),"Kiosk aktiv")
        if item["extension"]=="100" and not item["enabled"]: raise ValueError("Die kompatible Nebenstelle 100 bleibt aktiv. Den Telefonserver bei Bedarf unter Netzwerk ausschalten.")
        old=old_devices.get(item["id"],{})
        item["password"]=retained(raw,old,"password","Geräte-SIP-Passwort",item["extension"]==old.get("extension"))
        draft["devices"].append(item)
    if any(item["extension"]=="100" for item in previous.get("devices",[])) and not any(item["extension"]=="100" for item in draft["devices"]):
        raise ValueError("Die übernommene Nebenstelle 100 bleibt für bestehende Anmeldungen erhalten.")
    old_numbers={item["id"]:item for item in previous.get("numbers",[])}
    for raw in objects(body.get("numbers",[]),NUMBER_KEYS,8,"Rufnummern"):
        item={"incoming_mode":"normal","incoming_devices":[],"announcement_callers":[],"announcement_pin":"","announcement_auto_answer":False,"announcement_max_seconds":180,**raw}
        for key in ("id","name","number","connection_id"): item[key]=text(item.get(key,""),key,80)
        if not item["name"]: raise ValueError("Rufnummer benennen.")
        if not re.fullmatch(r"\+[1-9][0-9]{6,14}",item["number"]): raise ValueError("Rufnummer mit +Landesvorwahl eingeben.")
        if item["connection_id"] not in {c["id"] for c in draft["connections"]}: raise ValueError("Der Rufnummer einen vorhandenen SIP-Zugang zuordnen.")
        if not isinstance(item["incoming_mode"],str) or item["incoming_mode"] not in {"normal","reject","announcement"}: raise ValueError("Ungültiges Rufnummern-Verhalten.")
        targets=item["incoming_devices"]
        if not isinstance(targets,list) or any(not isinstance(t,str) for t in targets) or len(set(targets))!=len(targets) or any(t not in extensions|{"100"} for t in targets): raise ValueError("Klingelziele zuerst aus den Rufnummern entfernen.")
        if not isinstance(item["announcement_callers"],list) or len(item["announcement_callers"])>20 or any(not isinstance(n,str) or not re.fullmatch(r"\+[1-9][0-9]{6,14}",n) for n in item["announcement_callers"]): raise ValueError("Erlaubte Absender als internationale Rufnummern eintragen.")
        item["announcement_auto_answer"]=boolean(item["announcement_auto_answer"],"Auto-Answer")
        if type(item["announcement_max_seconds"]) is not int or not 10<=item["announcement_max_seconds"]<=600: raise ValueError("Durchsage-Dauer: 10 bis 600 Sekunden.")
        clear=item.pop("announcement_clear_pin",False)
        boolean(clear,"PIN löschen")
        pin=retained(raw,old_numbers.get(item["id"],{}),"announcement_pin","Durchsage-PIN")
        if pin and not re.fullmatch(r"[0-9]{6}",pin): raise ValueError("Durchsage-PIN: genau sechs Ziffern.")
        item["announcement_pin"]="" if clear else pin
        draft["numbers"].append(item)
    if len({n["number"] for n in draft["numbers"]})!=len(draft["numbers"]): raise ValueError("Rufnummern dürfen nicht doppelt vorkommen.")
    for raw in objects(body.get("contacts",[]),CONTACT_KEYS,100,"Kontakte"):
        item={key:text(raw.get(key,""),key,80) for key in ("id","name","number","room")}
        if not item["name"] or not re.fullmatch(r"\+?[0-9*#]{3,20}",item["number"]): raise ValueError("Kontaktname und Telefonnummer prüfen.")
        item["favorite"]=boolean(raw.get("favorite",False),"Favorit")
        draft["contacts"].append(item)
    for section,keys in (("network",NETWORK_KEYS),("audio",AUDIO_KEYS),("web",WEB_KEYS)):
        raw=body.get(section,{})
        if not isinstance(raw,dict) or set(raw)-keys: raise ValueError("Ungültiger Bereich: "+section)
        for key,value in raw.items():
            if key in {"phone_password","intercom_key","web_password"}: continue
            if key in {"sip_port","kiosk_port","intercom_port"}:
                if type(value) is not int or not 1024<=value<=65535: raise ValueError("Ports: 1024 bis 65535.")
                draft[section][key]=value
            elif key=="lan_enabled": draft[section][key]=boolean(value,key)
            else: draft[section][key]=text(value,key)
        for key in keys & {"phone_password","intercom_key","web_password"}:
            same=True
            if key=="intercom_key": same=raw.get("kiosk_address","")==previous.get("audio",{}).get("kiosk_address","")
            draft[section][key]=retained(raw,previous.get(section,{}),key,key,same)
    if draft["audio"]["audio_target"] not in {"sip","kiosk"}: raise ValueError("Ungültiges Audio-Ziel.")
    draft["outbound_number"]=text(body.get("outbound_number",""),"Standardrufnummer",24)
    if draft["outbound_number"] and draft["outbound_number"] not in {n["id"] for n in draft["numbers"]}: raise ValueError("Standardrufnummer prüfen.")
    return draft

class WorkspaceStore:
    def __init__(self,directory,legacy=None):
        self.web_password_existing=bool((legacy or {}).get("web_password_hash"))
        self.path=directory/"workspace.json"
        self.applied_path=directory/"workspace-applied.json"
        self.lock=threading.RLock()
        saved=json.loads(self.path.read_text()) if self.path.exists() else {}
        self.value=saved.get("draft",blank())
        self.revision=saved.get("revision",0)
        self.updated=saved.get("updated","")
        self.applied=json.loads(self.applied_path.read_text()) if self.applied_path.exists() else {"revision":-1,"runtime_enabled":False,"updated":""}
        if not saved and legacy is not None:
            self.value=migrate_legacy(legacy)
            self.revision=0
            self.updated=datetime.now(timezone.utc).isoformat()
            self.applied={"revision":0,"runtime_enabled":self.value["runtime_enabled"],"updated":self.updated}
            atomic_json(self.path,{"draft":self.value,"revision":0,"updated":self.updated})
            atomic_json(self.applied_path,self.applied)
    def public(self):
        value=copy.deepcopy(self.value)
        for section,key in (("connections","auth_password"),("devices","password"),("numbers","announcement_pin")):
            for item in value[section]:
                item[key+"_set"]=bool(item.pop(key,""))
        for section,key in (("audio","phone_password"),("audio","intercom_key"),("web","web_password")):
            value[section][key+"_set"]=bool(value[section].pop(key,""))
        value["web"]["web_password_set"]=value["web"]["web_password_set"] or self.web_password_existing
        return {"draft":value,"revision":self.revision,"updated":self.updated,"applied":self.applied}
    def save(self,body,expected):
        if type(expected) is not int or expected!=self.revision: raise RuntimeError("Der Entwurf wurde in einem anderen Fenster geändert. Seite neu laden.")
        value=validate_draft(body,self.value)
        revision=self.revision+1;updated=datetime.now(timezone.utc).isoformat()
        atomic_json(self.path,{"draft":value,"revision":revision,"updated":updated})
        self.revision=revision;self.updated=updated;self.value=value
    def mark_applied(self):
        self.applied={"revision":self.revision,"runtime_enabled":self.value["runtime_enabled"],"updated":datetime.now(timezone.utc).isoformat()}
        atomic_json(self.applied_path,self.applied)
    def compile(self):
        d=self.value
        if d["demo"]: raise ValueError("Beispieldaten zuerst durch eine eigene Konfiguration ersetzen.")
        if not d["numbers"]: raise ValueError("Mindestens eine Rufnummer einrichten.")
        accounts={c["id"]:c for c in d["connections"]}
        used=set();lines=[]
        for n in d["numbers"]:
            c=accounts[n["connection_id"]]
            if not c["enabled"]: continue
            if c["id"] in used: raise ValueError("Dieser Gateway-Kern unterstützt eine Rufnummer pro SIP-Login. Einen eigenen Zugang pro Rufnummer verwenden; gemeinsame Trunk-Registrierungen sind noch nicht unterstützt.")
            used.add(c["id"])
            line={k:v for k,v in c.items() if k not in {"id","name"}}
            line.update(id=n["id"],label=n["name"],phone_number=n["number"])
            line.update({k:v for k,v in n.items() if k not in {"id","name","number","connection_id"}})
            if not line["incoming_devices"]:
                line["incoming_devices"]=[device["extension"] for device in d["devices"] if device["enabled"]]
            lines.append(line)
        if not lines: raise ValueError("Mindestens einen SIP-Zugang aktivieren und einer Rufnummer zuordnen.")
        if d["network"]["sip_port"] in {5038}: raise ValueError("SIP und AMI müssen getrennte Ports verwenden.")
        if d["audio"]["audio_target"]=="kiosk" and d["audio"]["intercom_port"] in {5038,d["network"]["sip_port"]}: raise ValueError("Rückruf-, SIP- und AMI-Ports müssen getrennt sein.")
        legacy=next((device for device in d["devices"] if device["extension"]=="100"),None)
        audio={**d["audio"]}
        if legacy: audio["phone_password"]=legacy["password"]
        return {**d["network"],**audio,**d["web"],"lines":lines,"outbound_line":d["outbound_number"],
                "devices":[{k:v for k,v in device.items() if k in {"name","extension","password","enabled"}} for device in d["devices"] if device["extension"]!="100"],
                "contacts":[{k:v for k,v in contact.items() if k!="id"} for contact in d["contacts"]]}


def migrate_legacy(cfg):
    """Keep SIP identities, secrets, routing and network values during an in-place upgrade."""
    draft=blank()
    draft["runtime_enabled"]=bool(cfg.get("enabled"))
    for section,keys in (("network",NETWORK_KEYS),("audio",AUDIO_KEYS),("web",WEB_KEYS-{"web_password"})):
        for key in keys:
            if key in cfg: draft[section][key]=copy.deepcopy(cfg[key])
    for index,line in enumerate(effective_lines(cfg)):
        connection_id="account_"+str(index+1)
        connection={key:copy.deepcopy(line.get(key,DEFAULTS.get(key,""))) for key in ACCOUNT_FIELDS if key!="phone_number"}
        connection.update(id=connection_id,name=line.get("label") or "SIP account "+str(index+1))
        draft["connections"].append(connection)
        number={key:copy.deepcopy(line.get(key,default)) for key,default in ANNOUNCEMENT_DEFAULTS.items()}
        number.update(id=line.get("id","main"),name=line.get("label") or "Phone number "+str(index+1),number=line["phone_number"],connection_id=connection_id,
                      incoming_mode=line.get("incoming_mode","normal"),incoming_devices=copy.deepcopy(line.get("incoming_devices") or incoming_devices(cfg,line))))
        draft["numbers"].append(number)
    for index,device in enumerate(cfg.get("devices",[])):
        draft["devices"].append({**copy.deepcopy(device),"id":"device_"+device["extension"],"address":"","room":""})
    if cfg.get("phone_password"):
        draft["devices"].insert(0,{"id":"legacy_phone","name":"Telefon 100","extension":"100","password":cfg["phone_password"],"enabled":True,"address":"","room":""})
    draft["contacts"]=[{**copy.deepcopy(contact),"id":"contact_"+str(index+1)} for index,contact in enumerate(cfg.get("contacts",[]))]
    draft["outbound_number"]=cfg.get("outbound_line",draft["numbers"][0]["id"] if draft["numbers"] else "")
    return draft
