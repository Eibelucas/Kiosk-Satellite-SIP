"""Validated local configuration. No customer credentials belong in Git."""
import ipaddress
import json
import os
import re
import secrets
from pathlib import Path

from werkzeug.security import generate_password_hash
from providers import ACCOUNT_DEFAULTS, PROVIDERS, resolve, validate_account

DEFAULTS = {
    "enabled": False, "provider": "telekom_private", "phone_number": "",
    "auth_mode": "access", "auth_username": "anonymous@t-online.de",
    "auth_password": "", "listen_address": "127.0.0.1",
    "local_network": "10.99.0.0/24", "external_address": "",
    "sip_port": 5070, "phone_password": "", "lan_enabled": False,
    "audio_target": "sip", "kiosk_address": "", "kiosk_port": 2324,
    "intercom_port": 8090, "intercom_key": "",
    "web_username": "kiosk", "web_password_hash": "", "contacts": [], "lines": [], "outbound_line": "main", **ACCOUNT_DEFAULTS,
}
INPUT_FIELDS = (set(DEFAULTS) - {"web_password_hash"}) | {"web_password"}
PHONE = re.compile(r"^\+[1-9][0-9]{6,14}$")
DESTINATION = re.compile(r"^\+?[0-9*#]{3,20}$")


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def secret_value(value, label, minimum=0):
    if not isinstance(value, str) or len(value) < minimum or len(value) > 256:
        raise ValueError(f"{label}: mindestens {minimum}, höchstens 256 Zeichen.")
    if value != value.strip():
        raise ValueError(f"{label}: keine Leerzeichen am Anfang oder Ende.")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f"{label}: Steuerzeichen sind nicht erlaubt.")
    return value


ACCOUNT_FIELDS = {"enabled", "provider", "phone_number", "auth_mode", "auth_username", "auth_password"} | set(ACCOUNT_DEFAULTS)
ANNOUNCEMENT_DEFAULTS = {"announcement_callers": [], "announcement_pin": "", "announcement_auto_answer": False, "announcement_max_seconds": 180}
LINE_FIELDS = ACCOUNT_FIELDS | {"id", "label", "incoming_mode"} | set(ANNOUNCEMENT_DEFAULTS) | {"announcement_clear_pin"}


def effective_lines(cfg):
    if cfg.get("lines"):
        return cfg["lines"]
    if cfg.get("phone_number"):
        return [{**{k: cfg.get(k, DEFAULTS[k]) for k in ACCOUNT_FIELDS}, "id": "main", "label": "Hauptrufnummer", "incoming_mode": "normal"}]
    return []


def number_aliases(number):
    result = {number, number[1:], "00" + number[1:]}
    if number.startswith("+49"):
        result.add("0" + number[3:])
    return sorted(result)


def incoming_aliases(line):
    account = resolve(line)
    number = line["phone_number"]
    aliases = set(number_aliases(number)) | {account["contact_user"], account["client_user"]}
    return sorted(aliases)


def validate_line(raw, previous=None):
    if not isinstance(raw, dict) or set(raw) - LINE_FIELDS:
        raise ValueError("Ungültiges Rufnummernkonto.")
    cfg = {**{k: DEFAULTS[k] for k in ACCOUNT_FIELDS}, "id": "main", "label": "Rufnummer", "incoming_mode": "normal", **ANNOUNCEMENT_DEFAULTS, **(previous or {}), **raw}
    if not isinstance(cfg["id"], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,23}", cfg["id"]):
        raise ValueError("Konto-ID: Kleinbuchstaben, Ziffern, Unterstrich oder Bindestrich, beginnend mit Buchstabe.")
    if not isinstance(cfg["label"], str) or not 1 <= len(cfg["label"].strip()) <= 80:
        raise ValueError("Jede Rufnummer benötigt einen Namen.")
    secret_value(cfg["label"], "Rufnummernname")
    if type(cfg["enabled"]) is not bool or not isinstance(cfg["incoming_mode"], str) or cfg["incoming_mode"] not in {"normal", "reject", "announcement"}:
        raise ValueError("Ungültige Rufnummern-Rolle.")
    if not isinstance(cfg["provider"], str) or cfg["provider"] not in PROVIDERS:
        raise ValueError("Unbekannter Anbieter.")
    if not isinstance(cfg["auth_mode"], str) or cfg["auth_mode"] not in {"access", "password"} or (cfg["auth_mode"] == "access" and cfg["provider"] != "telekom_private"):
        raise ValueError("Dieser Anbieter benötigt SIP-Benutzername und SIP-Passwort.")
    if not isinstance(cfg["phone_number"], str) or not PHONE.fullmatch(cfg["phone_number"]):
        raise ValueError("Die eigene Rufnummer mit +Landesvorwahl und ohne Leerzeichen eingeben.")
    if any(not isinstance(cfg.get(key, ""), str) for key in ACCOUNT_DEFAULTS):
        raise ValueError("SIP-Server und IDs müssen Text sein.")
    if not isinstance(cfg["auth_username"], str):
        raise ValueError("Ungültiger SIP-Benutzername.")
    changed = previous and (any(cfg[k] != previous.get(k) for k in ("provider", "auth_username")) or
        any(resolve(cfg)[k] != resolve(previous)[k] for k in ("registrar", "domain", "client_user")))
    password = raw.get("auth_password")
    if password is not None and not isinstance(password, str):
        raise ValueError("Ungültiges SIP-Passwort.")
    if password:
        cfg["auth_password"] = secret_value(password, "SIP-Passwort")
    else:
        cfg["auth_password"] = "" if changed else (previous or {}).get("auth_password", "")
    if cfg["auth_mode"] == "access":
        cfg["auth_username"], cfg["auth_password"] = "anonymous@t-online.de", ""
    else:
        user = cfg["auth_username"]
        if not isinstance(user, str) or not re.fullmatch(r"[A-Za-z0-9._+@~-]{1,120}", user) or not cfg["auth_password"] or (cfg["provider"] == "telekom_private" and user != user.lower()):
            raise ValueError("SIP-Benutzername und Passwort eintragen. Telekom-Benutzernamen müssen kleingeschrieben sein.")
    if not isinstance(cfg["announcement_callers"], list) or len(cfg["announcement_callers"]) > 20:
        raise ValueError("Höchstens 20 erlaubte Absendernummern für Durchsagen.")
    callers = []
    for caller in cfg["announcement_callers"]:
        if not isinstance(caller, str) or not PHONE.fullmatch(caller):
            raise ValueError("Durchsage-Absender international mit +Landesvorwahl eingeben.")
        if caller not in callers:
            callers.append(caller)
    cfg["announcement_callers"] = callers
    if cfg["incoming_mode"] == "announcement" and not callers:
        raise ValueError("Für die Durchsage-Rufnummer mindestens eine erlaubte Absendernummer festlegen.")
    pin = raw.get("announcement_pin", "")
    if not isinstance(pin, str) or (pin and not re.fullmatch(r"[0-9]{6}", pin)):
        raise ValueError("Optionale Durchsage-PIN muss genau sechs Ziffern enthalten.")
    clear = cfg.pop("announcement_clear_pin", False)
    if type(clear) is not bool or (clear and pin):
        raise ValueError("PIN löschen oder eine neue PIN setzen, nicht beides gleichzeitig.")
    cfg["announcement_pin"] = "" if clear else pin or (previous or {}).get("announcement_pin", "")
    if type(cfg["announcement_auto_answer"]) is not bool or type(cfg["announcement_max_seconds"]) is not int or not 10 <= cfg["announcement_max_seconds"] <= 600:
        raise ValueError("Durchsage: Auto-Answer-Schalter und Dauer zwischen 10 und 600 Sekunden prüfen.")
    validate_account(cfg)
    return cfg


def validate(body, previous=None):
    if not isinstance(body, dict) or set(body) - INPUT_FIELDS:
        raise ValueError("Ungültige Konfiguration.")
    cfg = {**DEFAULTS, **(previous or {})}
    cfg.update({k: v for k, v in body.items() if k not in {"web_password", "auth_password", "phone_password", "intercom_key"}})
    for key in ("enabled", "lan_enabled"):
        if not isinstance(cfg[key], bool):
            raise ValueError("Ungültiger Schalter.")
    prior_lines = {line["id"]: line for line in effective_lines(previous or {})}
    if "lines" in body:
        raw_lines = body["lines"]
    elif cfg.get("lines") and not (set(body) & ACCOUNT_FIELDS):
        raw_lines = cfg["lines"]
    else:
        if previous and body.get("provider", cfg["provider"]) != previous["provider"]:
            for key in ACCOUNT_DEFAULTS:
                if key not in body:
                    cfg[key] = ACCOUNT_DEFAULTS[key]
        raw_lines = [{**{k: cfg[k] for k in ACCOUNT_FIELDS if k != "auth_password"}, "id": "main", "label": "Hauptrufnummer", "incoming_mode": "normal"}]
        if "auth_password" in body:
            raw_lines[0]["auth_password"] = body["auth_password"]
    if not isinstance(raw_lines, list) or not 1 <= len(raw_lines) <= 8:
        raise ValueError("Eine bis acht Rufnummern einrichten.")
    lines, ids, numbers, aliases = [], set(), set(), set()
    for raw in raw_lines:
        line = validate_line(raw, prior_lines.get(raw.get("id")) if isinstance(raw, dict) and isinstance(raw.get("id"), str) else None)
        if line["id"] in ids or line["phone_number"] in numbers:
            raise ValueError("Rufnummern und Konto-IDs dürfen nicht doppelt vorkommen.")
        ids.add(line["id"]); numbers.add(line["phone_number"])
        if line["enabled"]:
            server = resolve(line)["registrar"].split(":")[0].lower()
            for alias in incoming_aliases(line):
                key = (server, alias)
                if key in aliases:
                    raise ValueError("Eingehende SIP-Ziel-IDs desselben Servers müssen eindeutig sein. Eigene SIP-Konten oder Contact-User verwenden.")
                aliases.add(key)
        lines.append(line)
    if sum(line["enabled"] and line["provider"] == "telekom_private" for line in lines) > 5:
        raise ValueError("Telekom erlaubt maximal fünf SIP-Clients; weitere Geräte am Anschluss mitzählen.")
    cfg["lines"] = lines
    cfg.update({key: lines[0][key] for key in ACCOUNT_FIELDS})
    cfg["enabled"] = any(line["enabled"] for line in lines)
    selected = cfg["outbound_line"]
    if not isinstance(selected, str) or (selected and selected not in ids):
        raise ValueError("Eine vorhandene Rufnummer für ausgehende Anrufe auswählen.")
    outbound = next((line for line in lines if line["id"] == selected), None)
    if outbound and cfg["enabled"] and (not outbound["enabled"] or outbound["incoming_mode"] != "normal"):
        raise ValueError("Ausgehend eine aktive normale Rufnummer auswählen.")
    try:
        address = ipaddress.IPv4Address(cfg["listen_address"])
        network = ipaddress.IPv4Network(cfg["local_network"], strict=False)
    except (ValueError, TypeError, ipaddress.AddressValueError) as exc:
        raise ValueError("NAS-Adresse und Heimnetz müssen gültige IPv4-Werte sein.") from exc
    private_ranges = [ipaddress.IPv4Network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if not any(address in n for n in private_ranges):
        raise ValueError("NAS-Adresse: eine private IPv4-Adresse aus dem eigenen Heimnetz eingeben.")
    if not any(network.subnet_of(n) for n in private_ranges):
        raise ValueError("Heimnetz mit Netzmaske: ein privates IPv4-Netz in CIDR-Schreibweise eingeben.")
    if address not in network:
        raise ValueError("Die NAS-IP ist privat, liegt aber außerhalb des eingetragenen Heimnetzes. Unter Heimnetz mit Netzmaske das passende Netz und dessen Präfixlänge aus HA oder dem Router eintragen.")
    if address in {network.network_address, network.broadcast_address}:
        raise ValueError("NAS-Adresse: eine Geräteadresse verwenden, nicht die Netz- oder Broadcast-Adresse des eingetragenen Heimnetzes.")
    cfg["listen_address"], cfg["local_network"] = str(address), str(network)
    if not isinstance(cfg["audio_target"], str) or cfg["audio_target"] not in {"sip", "kiosk"}:
        raise ValueError("Audio-Ziel: SIP-Telefon oder Kiosk Satellite auswählen.")
    key = body.get("intercom_key", "")
    if not isinstance(key, str):
        raise ValueError("Ungültiger Intercom-Schlüssel.")
    if key:
        cfg["intercom_key"] = secret_value(key, "Intercom-Schlüssel", 16)
    elif body.get("kiosk_address", cfg["kiosk_address"]) != (previous or {}).get("kiosk_address", cfg["kiosk_address"]):
        cfg["intercom_key"] = ""
    for name in ("kiosk_port", "intercom_port"):
        if type(cfg[name]) is not int or not 1024 <= cfg[name] <= 65535:
            raise ValueError("Kiosk-Intercom-Port und Rückrufport zwischen 1024 und 65535 eintragen.")
    if cfg["audio_target"] == "kiosk":
        try:
            kiosk = ipaddress.IPv4Address(cfg["kiosk_address"])
        except (ValueError, TypeError):
            raise ValueError("Kiosk-Adresse: die lokale IPv4-Adresse des Kiosk-Geräts eingeben.") from None
        if kiosk not in network or kiosk in {network.network_address, network.broadcast_address, address}:
            raise ValueError("Kiosk-Adresse muss eine andere Geräte-IP im eingetragenen Heimnetz sein.")
        if not cfg["intercom_key"]:
            raise ValueError("Den gemeinsamen Intercom-Schlüssel aus Kiosk Satellite eintragen.")
        if cfg["intercom_port"] in {5038, cfg["sip_port"]}:
            raise ValueError("Kiosk-Rückrufport muss sich von SIP und AMI unterscheiden.")
    ext = cfg["external_address"]
    if not isinstance(ext, str):
        raise ValueError("Ungültige öffentliche Adresse.")
    if ext:
        try:
            public = ipaddress.IPv4Address(ext)
        except ValueError as exc:
            raise ValueError("Öffentliche IPv4-Adresse eingeben oder das Feld leer lassen.") from exc
        if not public.is_global:
            raise ValueError("Die externe IPv4-Adresse muss öffentlich sein.")
    if type(cfg["sip_port"]) is not int or not 1024 <= cfg["sip_port"] <= 65535 or cfg["sip_port"] in {5038, 8088, 8099}:
        raise ValueError("SIP-Port zwischen 1024 und 65535 verwenden, Standard 5070.")
    value = body.get("phone_password")
    if value is not None and value != "":
        cfg["phone_password"] = secret_value(value, "SIP-Telefon-Passwort", 12)
    if cfg["audio_target"] == "sip" or cfg["phone_password"]:
        secret_value(cfg["phone_password"], "SIP-Telefon-Passwort", 12)
    if not isinstance(cfg["web_username"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", cfg["web_username"]):
        raise ValueError("Kiosk-Benutzername: nur Buchstaben, Ziffern, Unterstrich und Bindestrich.")
    password = body.get("web_password", "")
    if password:
        cfg["web_password_hash"] = generate_password_hash(secret_value(password, "Kiosk-Passwort", 12))
    elif not isinstance(password, str):
        raise ValueError("Ungültiges Kiosk-Passwort.")
    if cfg["lan_enabled"] and not cfg["web_password_hash"]:
        raise ValueError("Für den LAN-Zugriff ein eigenes Kiosk-Passwort mit mindestens 12 Zeichen festlegen.")
    if not isinstance(cfg["contacts"], list) or len(cfg["contacts"]) > 100:
        raise ValueError("Höchstens 100 Kontakte sind erlaubt.")
    contacts = []
    for contact in cfg["contacts"]:
        if not isinstance(contact, dict):
            raise ValueError("Ungültiger Kontakt.")
        name, number = contact.get("name", ""), contact.get("number", "")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or not isinstance(number, str) or not DESTINATION.fullmatch(number):
            raise ValueError("Jeder Kontakt braucht einen Namen und eine gültige Telefonnummer.")
        kind, room, favorite = contact.get("kind", "phone"), contact.get("room", ""), contact.get("favorite", False)
        if not isinstance(kind, str) or kind not in {"phone", "kiosk"} or not isinstance(room, str) or len(room) > 80 or type(favorite) is not bool:
            raise ValueError("Kontakt: Typ Telefon/Kiosk, Raum und Favorit prüfen.")
        secret_value(name.strip(), "Kontaktname")
        secret_value(room.strip(), "Raum")
        contacts.append({"name": name.strip(), "number": number, "favorite": favorite, "kind": kind, "room": room.strip()})
    cfg["contacts"] = contacts
    return cfg


class Settings:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "telekom.json"
        self.value = {**DEFAULTS, "contacts": []}
        if self.path.exists():
            self.value.update(json.loads(self.path.read_text()))
        self.session_secret = self._secret("session.key")
        self.ami_secret = self._secret("ami.key")

    def _secret(self, filename):
        path = self.directory / filename
        if not path.exists():
            atomic_json(path, secrets.token_hex(32))
        return json.loads(path.read_text())

    def save(self, body):
        cfg = validate(body, self.value)
        atomic_json(self.path, cfg)
        self.value = cfg

    def public(self):
        return {**{k: v for k, v in self.value.items() if k not in {"auth_password", "phone_password", "web_password_hash", "intercom_key"}},
                "intercom_key_set": bool(self.value.get("intercom_key")),
                "auth_password_set": bool(self.value["auth_password"]),
                "phone_password_set": bool(self.value["phone_password"]),
                "web_password_set": bool(self.value["web_password_hash"]),
                "lines": [{**{k: v for k, v in {**ANNOUNCEMENT_DEFAULTS, **line}.items() if k not in {"auth_password", "announcement_pin"}},
                           "auth_password_set": bool(line["auth_password"]), "announcement_pin_set": bool(line.get("announcement_pin"))} for line in effective_lines(self.value)]}


def ini(value):
    """Asterisk config values: keep escaped semicolons literal, reject line injection."""
    secret_value(str(value), "Konfigurationswert")
    return str(value).replace(";", r"\;")


def asterisk_files(cfg, ami_secret, bridge_ports=None):
    ip, port = cfg["listen_address"], cfg["sip_port"]
    native = cfg.get("audio_target") == "kiosk" and bridge_ports is not None
    agi_port, audio_port = bridge_ports or (0, 0)
    pjsip = f"""[global]
type=global
user_agent=Kiosk-Satellite-SIP
endpoint_identifier_order=username,ip

[transport-udp]
type=transport
protocol=udp
bind={ip}:{port}
local_net={cfg['local_network']}
local_net=127.0.0.1/32
"""
    if cfg["external_address"]:
        pjsip += f"external_signaling_address={cfg['external_address']}\nexternal_media_address={cfg['external_address']}\n"
    pjsip += pjsip[pjsip.index('[transport-udp]'):].replace('[transport-udp]', '[transport-tcp]').replace('protocol=udp', 'protocol=tcp')
    if cfg["phone_password"]:
        pjsip += f"""
[100]
type=endpoint
transport=transport-udp
context=from-phone
disallow=all
allow=alaw,ulaw
auth=phone-auth
aors=100
direct_media=no
force_rport=yes
rtp_symmetric=yes
rewrite_contact=yes
deny=0.0.0.0/0
permit={cfg['local_network']}

[phone-auth]
type=auth
auth_type=userpass
username=100
password={ini(cfg['phone_password'])}

[100]
type=aor
max_contacts=1
remove_existing=yes
qualify_frequency=30
"""
    lines = [line for line in effective_lines(cfg) if line["enabled"]]
    groups = {}
    for line in lines:
        account = resolve(line)
        server = account["registrar"].split(":")[0].lower()
        groups.setdefault(server, len(groups))
        identifier, context = "line-" + line["id"], "from-provider-" + str(groups[server])
        auth = f"outbound_auth={identifier}-auth\n" if line["auth_mode"] == "password" else ""
        proxy = f"outbound_proxy={ini('sip:' + account['outbound_proxy'] + ';lr')}\n" if account["outbound_proxy"] else ""
        pjsip += f"""
[{identifier}-registration]
type=registration
transport=transport-{account['transport']}
server_uri=sip:{account['registrar']}
client_uri=sip:{account['client_user']}@{account['domain']}
contact_user={account['contact_user']}
retry_interval=60
forbidden_retry_interval=300
expiration=600
line=yes
endpoint={identifier}
{auth}{proxy}
[{identifier}]
type=endpoint
transport=transport-{account['transport']}
context={context}
disallow=all
allow=alaw,ulaw
aors={identifier}-aor
from_user={account['from_user']}
from_domain={account['domain']}
send_pai=yes
direct_media=no
force_rport=yes
rtp_symmetric=yes
{auth}{proxy}
[{identifier}-aor]
type=aor
contact=sip:{account['registrar']}
"""
        if auth:
            pjsip += f"\n[{identifier}-auth]\ntype=auth\nauth_type=userpass\nusername={ini(line['auth_username'])}\npassword={ini(line['auth_password'])}\nrealm={ini(account['realm']) or '*'}\n"
    for server, group in groups.items():
        first = next(line for line in lines if resolve(line)["registrar"].split(":")[0].lower() == server)
        pjsip += f"\n[provider-{group}-identify]\ntype=identify\nendpoint=line-{first['id']}\nmatch={server}\nsrv_lookups=yes\n"
    dial = """[general]
static=yes
writeprotect=yes
clearglobalvars=no

[from-phone]
exten => 600,1,Answer()
 same => n,Echo()
 same => n,Hangup()
include => from-kiosk-phone

[from-kiosk-phone]
"""
    selected = next((line for line in lines if line["id"] == cfg.get("outbound_line", "main") and line["incoming_mode"] == "normal"), None)
    if selected:
        for pattern in ("_X.", "_+X.", "_*X.", "_#X."):
            dial += f"exten => {pattern},1,Goto(from-out-{selected['id']},${{EXTEN}},1)\n"
    for line in lines:
        if line["incoming_mode"] == "normal":
            dial += f"\n[from-out-{line['id']}]\n"
            for pattern in ("_X.", "_+X.", "_*X.", "_#X."):
                dial += f"exten => {pattern},1,Set(CALLERID(num)={line['phone_number']})\n same => n,Dial(PJSIP/${{EXTEN}}@line-{line['id']},60)\n same => n,Hangup()\n"
    for server, group in groups.items():
        dial += f"\n[from-provider-{group}]\n"
        for line in lines:
            if resolve(line)["registrar"].split(":")[0].lower() != server:
                continue
            for alias in incoming_aliases(line):
                dial += f"exten => {alias},1,Goto(incoming-{line['id']},s,1)\n"
        # Unknown called numbers never fall through into an outbound context.
        dial += "exten => _X.,1,Hangup(1)\nexten => _+X.,1,Hangup(1)\nexten => s,1,Hangup(1)\n"
    for line in lines:
        dial += f"\n[incoming-{line['id']}]\nexten => s,1,"
        if line["incoming_mode"] == "normal":
            if native:
                dial += f"Ringing()\n same => n,Gosub(kiosk-native,s,1({line['id']},call))\n same => n,Hangup()\n"
            else:
                dial += "Dial(PJSIP/100,45)\n same => n,Hangup()\n"
        elif line["incoming_mode"] == "announcement":
            dial += "Set(KIOSK_CALLER=${FILTER(0-9+,${CALLERID(num)})})\n"
            dial += ' same => n,GotoIf($["${CALLERID(num-pres):0:7}" != "allowed"]?denied)\n' 
            dial += ' same => n,GotoIf($[${LEN(${CALLERID(num)})} != ${LEN(${KIOSK_CALLER})}]?denied)\n'
            for caller in line["announcement_callers"]:
                for alias in number_aliases(caller):
                    dial += f' same => n,GotoIf($["${{KIOSK_CALLER}}" = "{alias}"]?authorized)\n'
            dial += ' same => n,Goto(denied)\n same => n(authorized),Set(GROUP(kiosk-page)=active)\n same => n,GotoIf($[${GROUP_COUNT(active@kiosk-page)} > 1]?denied)\n'
            dial += f' same => n,Set(TIMEOUT(absolute)={line["announcement_max_seconds"]})\n'
            if line.get("announcement_pin"):
                dial += f' same => n,Answer()\n same => n,Read(KIOSK_PIN,,6,,1,15)\n same => n,GotoIf($["${{KIOSK_PIN}}" != "{line["announcement_pin"]}"]?denied)\n'
            predial = 'b(kiosk-auto-answer^s^1)' if line["announcement_auto_answer"] else ''
            if native:
                dial += f' same => n,Gosub(kiosk-native,s,1({line["id"]},broadcast))\n same => n,Hangup()\n same => n(denied),Hangup(21)\n'
            else:
                dial += f' same => n,Page(PJSIP/100,qsi{predial},30)\n same => n,Hangup()\n same => n(denied),Hangup(21)\n'
        else:
            dial += "Hangup(21)\n"
    dial += "\n[kiosk-auto-answer]\nexten => s,1,Set(PJSIP_HEADER(add,Call-Info)=<sip:kiosk>\\;answer-after=0)\n same => n,Set(PJSIP_HEADER(add,Alert-Info)=<sip:kiosk>\\;info=alert-autoanswer)\n same => n,Return()\n"
    if native:
        dial += f"\n[kiosk-native]\nexten => s,1,Set(KIOSK_UUID=)\n same => n,AGI(agi://127.0.0.1:{agi_port},${{ARG1}},${{ARG2}},${{CALLERID(num-pres)}})\n same => n,GotoIf($[${{LEN(${{KIOSK_UUID}})}} != 36]?failed)\n same => n,Dial(AudioSocket/127.0.0.1:{audio_port}/${{KIOSK_UUID}}/c(slin),60)\n same => n,Return()\n same => n(failed),Hangup(21)\n\n[kiosk-native-out]\nexten => s,1,Gosub(kiosk-native,s,1(local,call))\n same => n,Hangup()\n"
    account = resolve(selected) if selected else None
    return {
        "pjsip.conf": pjsip, "extensions.conf": dial,
        "manager.conf": f"[general]\nenabled=yes\nwebenabled=no\nbindaddr=127.0.0.1\nport=5038\n\n[kioskphone]\nsecret={ini(ami_secret)}\ndeny=0.0.0.0/0.0.0.0\npermit=127.0.0.1/255.255.255.255\nread=none\nwrite=originate\n",
        "rtp.conf": "[general]\nrtpstart=30000\nrtpend=30100\nicesupport=yes\n" + (f"stunaddr={account['stun_server']}\n" if account and account["stun_server"] else ""),
        "resolver_unbound.conf": "[general]\nresolv=system\nhosts=system\n",
        "stasis.conf": "[threadpool]\ninitial_size=5\n",
        "dnsmgr.conf": "[general]\nenable=yes\nrefreshinterval=90\n",
        "http.conf": "[general]\nenabled=no\n",
        "modules.conf": "[modules]\nautoload=no\n" + "".join(f"load={module}.so\n" for module in (
            "res_resolver_unbound", "res_pjproject", "res_sorcery_config", "res_sorcery_memory", "res_sorcery_astdb",
            "res_pjsip", "res_pjsip_authenticator_digest", "res_pjsip_outbound_authenticator_digest",
            "res_pjsip_endpoint_identifier_user", "res_pjsip_endpoint_identifier_ip",
            "res_pjsip_registrar", "res_pjsip_outbound_registration", "res_pjsip_session",
            "res_pjsip_sdp_rtp", "res_pjsip_pubsub", "res_pjsip_nat", "res_pjsip_caller_id", "res_pjsip_dtmf_info", "res_rtp_asterisk", "chan_pjsip",
            "codec_alaw", "codec_ulaw", "codec_resample", "res_speech", "res_agi", "res_audiosocket", "chan_audiosocket", "format_pcm", "bridge_simple", "bridge_native_rtp",
            "res_timing_timerfd", "bridge_softmix", "pbx_config", "app_dial", "app_echo", "app_stack", "app_confbridge", "app_page", "app_read", "func_timeout", "func_groupcount", "res_pjsip_header_funcs", "func_callerid", "func_strings", "func_logic", "func_channel",
        )), 
        "confbridge.conf": "[default_bridge]\ntype=bridge\ninternal_sample_rate=8000\nmixing_interval=20\n[default_user]\ntype=user\nquiet=yes\n",
        "cdr.conf": "[general]\nenable=no\n",
        "cel.conf": "[general]\nenable=no\n",
        "ccss.conf": "[general]\n",
        "features.conf": "[general]\n",
        "acl.conf": "; No reusable ACL objects. Per-endpoint rules are in pjsip.conf.\n",
        "udptl.conf": "[general]\nudptlstart=4000\nudptlend=4999\n",
        "pjproject.conf": "[global]\n",
        "indications.conf": "[general]\ncountry=de\n[de]\ndescription=Germany\nringcadence=1000,4000\ndial=425\nbusy=425/480,0/480\nring=425/1000,0/4000\n",
        "logger.conf": "[general]\n[logfiles]\nconsole=warning,error\n",
        "asterisk.conf": "[directories]\nastetcdir => /etc/asterisk\nastmoddir => /usr/lib/asterisk/modules\nastvarlibdir => /var/lib/asterisk\nastdbdir => /data/asterisk\nastkeydir => /var/lib/asterisk/keys\nastdatadir => /var/lib/asterisk\nastagidir => /var/lib/asterisk/agi-bin\nastspooldir => /var/spool/asterisk\nastrundir => /run/asterisk\nastlogdir => /var/log/asterisk\n[options]\nrunuser=asterisk\nrungroup=asterisk\n[files]\nastctlpermissions=0660\nastctlowner=asterisk\nastctlgroup=asterisk\n",
    }
