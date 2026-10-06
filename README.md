# Kiosk Satellite SIP

Telefonseite ab **26.10.11**: **Telefon öffnen** startet mit den Wähltasten. **Kontakte öffnen** öffnet direkt Kontakte und Favoriten im Plugin. Ein Kontakt trägt die Nummer ein; erst **Anrufen** mit Bestätigung fordert den Anruf an. Die native KS-Gegensprechliste enthält weiterhin Kiosk-Geräte. SDK 1 hat keine Schnittstelle zum Eintragen von SIP-Telefonkontakten; dafür ist eine Änderung an Kiosk Satellite erforderlich.

## Auf deinem HAOS installieren

Für **HAOS auf einem unterstützten amd64-System** gibt es jetzt ein gemeinsames Add-on mit **Asterisk, Telefon-Gateway und deutschem Anbieter-Onboarding**.

1. HA → Einstellungen → Apps/Add-ons → Store → Drei-Punkte-Menü → Repositories.
2. `https://github.com/Eibelucas/Kiosk-Satellite-SIP` hinzufügen.
3. **Kiosk Satellite SIP Gateway** installieren und starten.
4. **Weboberfläche öffnen** und die vier Einrichtungsschritte durchgehen.
5. Das gewählte Audio-Ziel einrichten: für **Kiosk Satellite Intercom** Kiosk-IP, Identitätsport und gemeinsamen Intercom-Schlüssel hinterlegen; für **SIP-Telefon 100** das SIP-Telefon anmelden. Im Kiosk-Plugin die angezeigte **Gateway URL** setzen. Kiosk-Audio benötigt keine zusätzliche Anmeldung von Telefon 100.

Für den ersten Audio-Test den **lokalen Kiosk-Echo-Test** im HA-Assistenten verwenden. **600 im normalen Anrufpad ist kein sicherer lokaler Test:** Das Anrufpad verwendet den ausgehenden Anbieter-Kontext.

**[Vollständige Anleitung: Anbieter, mehrere Rufnummern und Durchsagen](kiosk_sip/DOCS.md)**. Sie steht auch im Dokumentations-Tab des Add-ons.

Für den Plugin-Manager und den HAOS-Add-on-Store dieselbe normale Repository-URL verwenden:

```text
https://github.com/Eibelucas/Kiosk-Satellite-SIP
```

**Aktueller Umfang:** Deutsches Onboarding für Telekom, sipgate, easybell, FRITZ!Box und manuelle Profile für Vodafone, 1&1, o2 bzw. andere registrierende SIP-Konten. Bis zu acht Rufnummern, eine normale Hauptrufnummer und separate Durchsage-Nummern mit erlaubten Absendern, optionaler PIN und begrenzter Dauer. Kontakte können als Kiosk-/Raumkarten mit Favoriten und Suche angezeigt werden.

**Audio ab 26.10.9:** Im HA-Assistenten zwischen **Kiosk Satellite Intercom** und SIP-Telefon **100** wählen. Die native Audio-Brücke verbindet Asterisk mit Mikrofon/Lautsprecher und Anrufanzeige eines konfigurierten Android-Kiosks. Normale Anrufe müssen am Kiosk angenommen werden; separate Durchsagen bleiben einseitig. Ein gemeinsamer Intercom-Schlüssel und erreichbares lokales Intercom sind erforderlich. Derzeit ein Kiosk-Gerät und lokale HTTP/WS-Verbindungen; TLS-Intercom wird nicht automatisch umgestellt. Kiosk-Karten bleiben zugeordnete Telefonkontakte. Das Plugin öffnet die Telefonseite, die Audio-Brücke läuft im HA-Add-on. **[Einrichtung und lokaler Audio-Test](kiosk_sip/DOCS.md#kiosk-satellite-als-audio-ziel-ab-26109)**.

**Updates:** Versionen im Format `26.10.1`, `26.10.2` usw.; Git-Tags mit `v` davor. Stabile Releases enthalten Plugin-ZIP, identisches Manifest und SHA-256-Datei. Die ZIP enthält genau `kiosk-satellite-plugin.json`, `plugin.jar` und `LICENSE`. Das HAOS-Add-on wird aus dem Repository gebaut und hat eine eigene Installation: Plugin und Add-on bei neuen Versionen jeweils aktualisieren. Gespeicherte Anschlussdaten bleiben in `/data` erhalten. Die historische Version `v0.1.0` bleibt verfügbar.

**[Release-Schritte und Prüfungen](RELEASES.md)**

## Historischer Standalone-Prototyp (für Entwickler)

Unofficial SIP/telephone extension for [Kiosk Satellite](https://github.com/jxlarrea/kiosk-satellite).

The project is split into two parts:

1. **Kiosk Satellite plugin** – adds a `Telefon öffnen` command and opens the configured phone UI inside Kiosk Satellite.
2. **SIP gateway** – serves a touch-friendly dial pad/contact page and talks to Asterisk through AMI for outbound call setup.

> The following describes the original standalone `gateway/` prototype, not the current HAOS add-on. Outbound call setup is implemented as an Asterisk AMI originate request. The bidirectional RTP ↔ Kiosk Satellite Intercom audio bridge and incoming-call injection are the next milestone.

## Planned architecture

```text
Kiosk Satellite
  └─ Kiosk Satellite SIP plugin
       └─ Phone UI (gateway)
            └─ Kiosk SIP Gateway
                 └─ Asterisk
                      └─ Telekom SIP / PSTN
```

## Current features

- Kiosk Satellite SDK 1 plugin
- Configurable gateway URL
- `Telefon öffnen` plugin command
- Responsive dial pad
- Local contact list from `gateway/contacts.json`
- Outbound Asterisk AMI `Originate`
- Optional caller ID and dial context configuration
- Docker image for the gateway
- GitHub Actions plugin build/release workflow

## Quick start

### 1. Gateway

Copy the example configuration:

```bash
cd gateway
cp .env.example .env
```

Edit the Asterisk AMI values, then run:

```bash
pip install -r requirements.txt
python app.py
```

The web UI defaults to `http://HOST:8088/`.

### 2. Kiosk Satellite plugin

Install a release ZIP from this repository in Kiosk Satellite's Plugin Manager. Configure `Gateway URL` to the URL from step 1 and run the `Telefon öffnen` command.

Plugin packages follow Kiosk Satellite SDK 1 and contain `kiosk-satellite-plugin.json`, `plugin.jar`, and `LICENSE`.

## Asterisk example

Enable an AMI user with the minimum permissions needed for `Originate` and set a dial context that can reach your Telekom SIP trunk.

Example environment values:

```env
AMI_HOST=192.168.1.20
AMI_PORT=5038
AMI_USERNAME=kioskphone
AMI_SECRET=change-me
ASTERISK_CHANNEL=PJSIP/100
ASTERISK_CONTEXT=from-kiosk-phone
ASTERISK_CALLER_ID=Kiosk <100>
```

For a user-entered destination number, the gateway originates the configured local channel and sends that number into the configured dialplan context.

## Security

Do not expose AMI to the internet. Keep the gateway and AMI on your trusted LAN/VPN, use an AMI account restricted to the required commands, and put authentication/TLS in front of the gateway before exposing it outside the LAN.

## Roadmap

- Incoming PSTN/SIP call → Kiosk Satellite Intercom ringing
- Answer/decline/hangup synchronization
- PCM16 16 kHz mono ↔ RTP media bridge
- Multiple kiosks / ring groups
- Call history
- Contact editing
- Home Assistant services/entities
- DTMF during an active call

## License

Apache-2.0. Kiosk Satellite is a separate project and is not bundled here.
