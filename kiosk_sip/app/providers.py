"""Provider profiles. Account-specific values always come from the customer."""
import re

PROVIDERS = {
    'telekom_private': {'name': 'Telekom Privatkunden', 'registrar': 'tel.t-online.de',
        'domain': 'tel.t-online.de', 'realm': 'tel.t-online.de', 'auth_mode': 'access',
        'stun_server': 'stun.t-online.de:3478', 'help_url': 'https://www.telekom.de/hilfe/internet-telefonie/telefonie/voice-over-ip-sip-client',
        'hint': 'MagentaZuhause Privatkunden. Anschluss-Anmeldung oder gültige Telefonie-Zugangsdaten. Kein DeutschlandLAN-Trunk und kein Regio-Profil.'},
    'sipgate': {'name': 'sipgate (SIP-Gerät)', 'registrar': 'sipgate.de', 'domain': 'sipgate.de',
        'auth_mode': 'password', 'help_url': 'https://help.sipgate.de/cloud-telefonanlage/erste-schritte/alles-fur-den-start-mit-sipgate/wie-konfiguriere-ich-mein-voip-telefon-mit-sipgate',
        'hint': 'SIP-ID und SIP-Passwort des Geräts, nicht das Web-Login. Für sipgate trunking das manuelle Profil mit dessen Server verwenden.'},
    'easybell': {'name': 'easybell (VoIP-Rufnummer)', 'registrar': 'voip.easybell.de', 'domain': 'voip.easybell.de',
        'auth_mode': 'password', 'help_url': 'https://www.easybell.de/hilfe/telefon-konfiguration/ip-telefonanlagen-fuer-unsere-sip-trunks/antwort/asterisk-telefonanlagen/',
        'hint': 'SIP-Benutzername und SIP-Passwort aus my.easybell. Anmelde-Rufnummer standardmäßig 0049…; abweichende Verbindungsvorgaben übernehmen.'},
    'fritzbox': {'name': 'FRITZ!Box (lokales IP-Telefon)', 'registrar': 'fritz.box', 'domain': 'fritz.box',
        'auth_mode': 'password', 'help_url': 'https://fritz.com/apps/knowledge-base/FRITZ-Box-7412/42_IP-Telefon-an-FRITZ-Box-anmelden-und-einrichten/',
        'hint': 'In der FRITZ!Box ein IP-Telefon anlegen und dessen Benutzer/Passwort verwenden. Dort eingehende und ausgehende Rufnummern zuweisen. Bei DNS-Problemen die Router-IP als Registrar und Domain eintragen.'},
    'vodafone': {'name': 'Vodafone (Daten aus Zugangsschreiben)', 'auth_mode': 'password',
        'help_url': 'https://www.vodafone.de/downloadarea/EGF_Kundenanleitung_DSL_Webanleitung_140126_DVW_26.pdf',
        'hint': 'Registrar, Domain, SIP-Benutzer und Anmelde-ID exakt aus deinen Telefonie-Zugangsdaten übernehmen. DSL/Kabel und Netzvarianten haben unterschiedliche Werte; es gibt hier keinen universellen Server.'},
    '1und1': {'name': '1&1 (eigene SIP-Zugangsdaten)', 'auth_mode': 'password',
        'help_url': 'https://hilfe-center.1und1.de/',
        'hint': 'Telefonie-Passwort und SIP-Server aus den aktuellen Vertragsdaten übernehmen. Kein Internetzugangs- oder Control-Center-Passwort.'},
    'o2': {'name': 'o2 (eigene SIP-Zugangsdaten)', 'auth_mode': 'password',
        'help_url': 'https://www.o2online.de/service/router/',
        'hint': 'SIP-Zugangsdaten und Registrar deines Anschlusses eintragen. Vertrags- und Technikvarianten werden manuell konfiguriert.'},
    'custom': {'name': 'Anderer SIP-Anbieter / eigene PBX', 'auth_mode': 'password',
        'help_url': '', 'hint': 'Registrierendes SIP-Konto mit UDP oder TCP. Registrar, Domain und SIP-ID nach Anbietervorgabe. TLS/SRTP und reine IP-authentifizierte Business-Trunks sind noch nicht unterstützt.'},
}
ACCOUNT_DEFAULTS = {'registrar': '', 'domain': '', 'realm': '', 'outbound_proxy': '',
                    'client_user': '', 'contact_user': '', 'from_user': '', 'transport': 'udp', 'stun_server': ''}
SIP_USER = re.compile(r'^[A-Za-z0-9+][A-Za-z0-9_.+~-]{0,119}$')
HOST = re.compile(r'^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$')


def host(value, label, optional=False, port=False):
    if not isinstance(value, str):
        raise ValueError(f'{label}: ungültiger Server.')
    if optional and not value:
        return ''
    parts = value.split(':')
    if len(parts) > (2 if port else 1) or not HOST.fullmatch(parts[0]):
        raise ValueError(f'{label}: Hostname oder IPv4-Adresse eingeben, keine URL oder SIP-URI.')
    if len(parts) == 2 and (not parts[1].isdigit() or not 1 <= int(parts[1]) <= 65535):
        raise ValueError(f'{label}: ungültiger Port.')
    return value


def resolve(cfg):
    profile = PROVIDERS[cfg['provider']]
    account = {key: cfg.get(key) or profile.get(key, '') for key in ACCOUNT_DEFAULTS}
    account['transport'] = cfg.get('transport', 'udp')
    number, provider = cfg['phone_number'], cfg['provider']
    client = number
    if provider == 'easybell':
        client = '00' + number.lstrip('+')
    elif provider not in {'telekom_private', 'easybell'}:
        client = cfg['auth_username'].split('@')[0]
    account['client_user'] = cfg.get('client_user') or client
    account['contact_user'] = cfg.get('contact_user') or account['client_user']
    account['from_user'] = cfg.get('from_user') or account['client_user']
    account['domain'] = account['domain'] or account['registrar'].split(':')[0]
    return account


def validate_account(cfg):
    if any(not isinstance(cfg.get(key, ''), str) for key in ACCOUNT_DEFAULTS):
        raise ValueError('SIP-Server und IDs müssen Text sein.')
    account = resolve(cfg)
    host(account['registrar'], 'Registrar', port=True)
    host(account['domain'], 'SIP-Domain')
    host(account['outbound_proxy'], 'Outbound-Proxy', optional=True, port=True)
    host(account['stun_server'], 'STUN-Server', optional=True, port=True)
    realm = account['realm']
    if not isinstance(realm, str) or len(realm) > 120 or any(c in realm for c in '\r\n;[]\\'):
        raise ValueError('Ungültiger Authentifizierungs-Realm.')
    for key in ('client_user', 'contact_user', 'from_user'):
        if not isinstance(account[key], str) or not SIP_USER.fullmatch(account[key]):
            raise ValueError('Anmelde-ID, Contact-User und From-User: nur SIP-Benutzername ohne @Domain.')
    if cfg['transport'] not in {'udp', 'tcp'}:
        raise ValueError('Aktuell werden UDP und TCP unterstützt, kein TLS/SRTP.')
    return cfg
