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
    "local_network": "192.168.2.0/24", "external_address": "",
    "sip_port": 5070, "phone_password": "", "lan_enabled": False,
    "web_username": "kiosk", "web_password_hash": "", "contacts": [], **ACCOUNT_DEFAULTS,
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


def validate(body, previous=None):
    if not isinstance(body, dict) or set(body) - INPUT_FIELDS:
        raise ValueError("Ungültige Konfiguration.")
    cfg = {**DEFAULTS, **(previous or {})}
    cfg.update({k: v for k, v in body.items() if k not in {"web_password", "auth_password", "phone_password"}})
    for key in ("enabled", "lan_enabled"):
        if not isinstance(cfg[key], bool):
            raise ValueError("Ungültiger Schalter.")
    if not isinstance(cfg["provider"], str) or cfg["provider"] not in PROVIDERS:
        raise ValueError("Unbekannter Anbieter.")
    if previous and cfg["provider"] != previous["provider"]:
        cfg["auth_password"] = ""
        for key in ACCOUNT_DEFAULTS:
            if key not in body:
                cfg[key] = ACCOUNT_DEFAULTS[key]
    if cfg["auth_mode"] not in {"access", "password"} or (cfg["auth_mode"] == "access" and cfg["provider"] != "telekom_private"):
        raise ValueError("Dieser Anbieter benötigt SIP-Benutzername und SIP-Passwort.")
    number = cfg["phone_number"]
    if not isinstance(number, str) or not PHONE.fullmatch(number):
        raise ValueError("Rufnummer international, zum Beispiel +492611234567, ohne Leerzeichen eingeben.")
    try:
        address = ipaddress.IPv4Address(cfg["listen_address"])
        network = ipaddress.IPv4Network(cfg["local_network"], strict=False)
    except (ValueError, TypeError, ipaddress.AddressValueError) as exc:
        raise ValueError("NAS-Adresse und Heimnetz müssen gültige IPv4-Werte sein.") from exc
    private_ranges = [ipaddress.IPv4Network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if not any(network.subnet_of(n) for n in private_ranges) or address not in network or address in {network.network_address, network.broadcast_address}:
        raise ValueError("Die NAS-Adresse muss eine private IPv4-Adresse innerhalb deines Heimnetzes sein.")
    cfg["listen_address"], cfg["local_network"] = str(address), str(network)
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
    for key, label, minimum in (("auth_password", "Telekom-Passwort", 0), ("phone_password", "SIP-Telefon-Passwort", 12)):
        value = body.get(key)
        if value is not None and value != "":
            cfg[key] = secret_value(value, label, minimum)
    if cfg["auth_mode"] == "access":
        cfg["auth_username"], cfg["auth_password"] = "anonymous@t-online.de", ""
    else:
        user = cfg["auth_username"]
        if not isinstance(user, str) or not re.fullmatch(r"[A-Za-z0-9._+@~-]{1,120}", user) or not cfg["auth_password"] or (cfg["provider"] == "telekom_private" and user != user.lower()):
            raise ValueError("SIP-Benutzername und Passwort eintragen. Telekom-Benutzernamen müssen kleingeschrieben sein.")
    validate_account(cfg)
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
        contacts.append({"name": name.strip(), "number": number, "favorite": bool(contact.get("favorite", False))})
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
        return {**{k: v for k, v in self.value.items() if k not in {"auth_password", "phone_password", "web_password_hash"}},
                "auth_password_set": bool(self.value["auth_password"]),
                "phone_password_set": bool(self.value["phone_password"]),
                "web_password_set": bool(self.value["web_password_hash"])}


def ini(value):
    """Asterisk config values: keep escaped semicolons literal, reject line injection."""
    secret_value(str(value), "Konfigurationswert")
    return str(value).replace(";", r"\;")


def asterisk_files(cfg, ami_secret):
    ip, port = cfg["listen_address"], cfg["sip_port"]
    pjsip = f"""[global]
type=global
user_agent=Kiosk-Satellite-SIP

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
    account = resolve(cfg) if cfg["enabled"] else None
    if cfg["enabled"]:
        auth = "outbound_auth=telekom-auth\n" if cfg["auth_mode"] == "password" else ""
        pjsip += f"""
[telekom-registration]
type=registration
transport=transport-{account['transport']}
server_uri=sip:{account['registrar']}
client_uri=sip:{account['client_user']}@{account['domain']}
contact_user={account['contact_user']}
retry_interval=60
forbidden_retry_interval=300
expiration=600
line=yes
endpoint=telekom
{auth}
[telekom]
type=endpoint
transport=transport-{account['transport']}
context=from-telekom
disallow=all
allow=alaw,ulaw
aors=telekom-aor
from_user={account['from_user']}
from_domain={account['domain']}
send_pai=yes
direct_media=no
force_rport=yes
rtp_symmetric=yes
{auth}
[telekom-aor]
type=aor
contact=sip:{account['registrar']}

[telekom-identify]
type=identify
endpoint=telekom
match={account['registrar'].split(':')[0]}
srv_lookups=yes
"""
        if account['outbound_proxy']:
            proxy = f"outbound_proxy={ini('sip:' + account['outbound_proxy'] + ';lr')}\n"
            pjsip = pjsip.replace('[telekom-registration]\n', '[telekom-registration]\n' + proxy).replace('[telekom]\n', '[telekom]\n' + proxy)
        if auth:
            pjsip += f"\n[telekom-auth]\ntype=auth\nauth_type=userpass\nusername={ini(cfg['auth_username'])}\npassword={ini(cfg['auth_password'])}\nrealm={ini(account['realm']) or '*'}\n"
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
    if cfg["enabled"]:
        for pattern in ("_X.", "_+X.", "_*X.", "_#X."):
            dial += f"exten => {pattern},1,Set(CALLERID(num)={cfg['phone_number']})\n same => n,Dial(PJSIP/${{EXTEN}}@telekom,60)\n same => n,Hangup()\n"
    dial += "\n[from-telekom]\nexten => _+X.,1,Dial(PJSIP/100,45)\n same => n,Hangup()\nexten => _X.,1,Dial(PJSIP/100,45)\n same => n,Hangup()\n"
    return {
        "pjsip.conf": pjsip, "extensions.conf": dial,
        "manager.conf": f"[general]\nenabled=yes\nwebenabled=no\nbindaddr=127.0.0.1\nport=5038\n\n[kioskphone]\nsecret={ini(ami_secret)}\ndeny=0.0.0.0/0.0.0.0\npermit=127.0.0.1/255.255.255.255\nread=none\nwrite=originate\n",
        "rtp.conf": "[general]\nrtpstart=30000\nrtpend=30100\nicesupport=yes\n" + (f"stunaddr={account['stun_server']}\n" if account and account["stun_server"] else ""),
        "dnsmgr.conf": "[general]\nenable=yes\nrefreshinterval=90\n",
        "http.conf": "[general]\nenabled=no\n",
        "modules.conf": "[modules]\nautoload=no\n" + "".join(f"load={module}.so\n" for module in (
            "res_pjproject", "res_sorcery_config", "res_sorcery_memory", "res_sorcery_astdb",
            "res_pjsip", "res_pjsip_authenticator_digest", "res_pjsip_outbound_authenticator_digest",
            "res_pjsip_endpoint_identifier_user", "res_pjsip_endpoint_identifier_ip",
            "res_pjsip_registrar", "res_pjsip_outbound_registration", "res_pjsip_session",
            "res_pjsip_sdp_rtp", "res_pjsip_pubsub", "res_rtp_asterisk", "chan_pjsip",
            "codec_alaw", "codec_ulaw", "format_pcm", "bridge_simple", "bridge_native_rtp",
            "bridge_softmix", "pbx_config", "app_dial", "app_echo", "app_stack", "func_pjsip_header",
        )), 
        "logger.conf": "[general]\n[logfiles]\nconsole=warning,error\n",
        "asterisk.conf": "[directories]\nastetcdir => /etc/asterisk\nastmoddir => /usr/lib/asterisk/modules\nastvarlibdir => /var/lib/asterisk\nastdbdir => /data/asterisk\nastkeydir => /var/lib/asterisk/keys\nastdatadir => /var/lib/asterisk\nastagidir => /var/lib/asterisk/agi-bin\nastspooldir => /var/spool/asterisk\nastrundir => /run/asterisk\nastlogdir => /var/log/asterisk\n[options]\nrunuser=asterisk\nrungroup=asterisk\n[files]\nastctlpermissions=0660\nastctlowner=asterisk\nastctlgroup=asterisk\n",
    }
