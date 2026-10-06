# Kiosk Satellite SIP Gateway für HAOS

Asterisk und Telefon-Gateway in einem Add-on, mit deutschem Anbieter-Onboarding.

- amd64, passend für HAOS auf einem unterstützten amd64-System
- Einrichtung über Home Assistant Ingress
- Telekom, sipgate, easybell, FRITZ!Box und eigene SIP-Zugangsdaten
- Mehrere Rufnummern, normale Hauptrufnummer und separate Durchsagen mit Absenderliste/PIN
- SIP-Nebenstelle 100 und lokaler Echo-Test 600
- Anrufpad, Telefonkontakte und Kiosk-/Raumkarten mit Suche/Favoriten
- Optionaler LAN-Zugang mit eigenem Kiosk-Passwort

**Audio-Ziel wählen:** Ab 26.10.9 ist Kiosk Satellite Intercom mit nativer Anrufanzeige, Mikrofon und Lautsprecher verfügbar. Alternativ SIP-Telefon 100 verwenden. Ein konfigurierter Kiosk, gemeinsamer Intercom-Schlüssel und lokale HTTP/WS-Verbindung; TLS-Intercom ist noch nicht unterstützt. Kiosk-Karten sind die Kontaktanzeige im Anrufpad.

Alle Schritte und Gegenproben stehen im Tab **Dokumentation** bzw. in [DOCS.md](DOCS.md).
