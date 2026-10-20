# Kiosk Satellite SIP Gateway für HAOS

Das Add-on enthält den Asterisk-Telefonserver und die Weboberfläche zur Einrichtung von SIP-Anbietern, Rufnummern und Geräten. Die Installation wird auf Home Assistant OS mit amd64-Architektur unterstützt.

- Anbieterprofile und manuelle SIP-Konfiguration.
- Bis zu acht externe SIP-Konten mit getrennten Rufnummern und Anrufregeln.
- Eigene SIP-Nebenstellen und Passwörter für mehrere Kiosks.
- Klingelziele je externer Rufnummer.
- Lokaler Echo-Test auf Nebenstelle 600 für angemeldete SIP-Geräte.
- Optionale Web-Telefonseite mit Kontakten und Kiosk-Karten.
- Alternative Audio-Brücke zu Kiosk Satellite Intercom.
- Separate Durchsage-Rufnummern mit Absenderliste, optionaler PIN und Dauerlimit.

Für den nativen KS-Dialer wird als Audio-Ziel **SIP-Telefon / Softphone 100** gewählt. Die Geräteverwaltung stellt die jeweilige Nebenstelle und deren Passwort bereit. Die Anbieteranmeldung bleibt zentral im Add-on.

Die alternative **Kiosk Satellite Intercom**-Brücke verbindet ein konfiguriertes Kiosk-Gerät über den gemeinsamen Intercom-Schlüssel. Sie nutzt lokale HTTP-/WebSocket-Verbindungen und unterstützt derzeit kein TLS-Intercom.

[Einrichtung, Betriebsarten und Fehlerbehebung](DOCS.md)
