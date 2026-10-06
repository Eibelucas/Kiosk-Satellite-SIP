# 26.10.9

- Audio-Ziel Kiosk Satellite Intercom: Asterisk-20-AudioSocket mit 8-kHz-PCM, Umwandlung auf 16 kHz und nativer Intercom-WebSocket-Verbindung.
- Normale Anrufe klingeln am Kiosk; erst Annehmen öffnet Audio und verbindet den Anruf.
- Separate Durchsagen behalten Absenderliste/PIN/Dauerlimit und verwenden einseitigen Kiosk-Intercom-Modus.
- Signierte Rückmeldungen, Token-Wiederverwendungsschutz, lokale Schlüsselablage ohne Ausgabe in Status/API/Logs.
- Verbindung prüfen und lokaler Kiosk-Echo-Test im Assistenten. Eigene Geräte-IP, Identitätsport und gemeinsamer Schlüssel.
- Der Kiosk-Intercom-Port wird aus seiner Identität übernommen. Ein konfiguriertes Kiosk-Gerät, lokales HTTP/WS; verschlüsseltes Intercom wird abgewiesen und nicht umgestellt.
- Das bisherige SIP-Telefon 100 bleibt als alternative Audio-Ausgabe erhalten.

# 26.10.8

- Unterscheidet private Geräte-IP, falsches Heimnetz und unzulässige Netz-/Broadcast-Adressen in der Fehlermeldung.
- Bei der Ersteinrichtung ist kein Beispielnetz mehr vorbelegt; das eigene Netz muss ausdrücklich eingetragen werden.
- Die Zusammenfassung zeigt das eingetragene Heimnetz mit Netzmaske.
- Bestehende lokale Konfigurationen und SIP-Funktionen bleiben erhalten.

# 26.10.7

- Allgemeine HAOS-Anleitung ohne persönliche Hardwarebezüge.
- Neutrale Eingabehinweise statt ortsbezogener Rufnummern- und Netzbeispiele.
- Tests verwenden ausdrücklich fiktive Rufnummern und ein unabhängiges Testnetz.
- Standalone-Gateway startet ohne voreingestellten Beispielkontakt.
- Bestehende lokale Anschlussdaten werden nicht verändert.

# 26.10.6

- HA-Ingress nutzt den Supervisor-Port statt fest 8099; behebt `Address in use` beim Start im Host-Netzwerk.
- Bei belegtem SIP-/AMI-Port bleibt die HA-Einrichtung offen und zeigt einen konkreten Hinweis; nach Korrektur ist Speichern erneut möglich.
- Bei belegtem LAN-Webport bleibt HA-Ingress offen; Gateway-Port in der Add-on-Konfiguration ändern und neu starten.
- Asterisk gilt erst mit beiden geladenen SIP-Transporten als bereit. Fehlstarts werden aufgeräumt.
- Regressionsprüfung mit belegten Ports 8099/5070, simuliertem Supervisor, Zugriffsschutz und sauberem Beenden.
- Anschlussdaten bleiben erhalten. Audio-Bridge zu Kiosk Satellite weiterhin nicht implementiert.

# 26.10.5

- Kontakte als Kiosk-/Raumkarten mit Favoriten und Suche anzeigen.
- Kontaktbearbeitung im HA-Assistenten; normale Kontakte aus älteren Versionen bleiben erhalten.
- Karte auswählen bereitet den Anruf vor; kein automatisches Wählen.
- Vollständige Anbieter-, Rufnummern-, Durchsage- und Update-Anleitung im Repository.

# 26.10.4

- Separate Durchsage-Rufnummer mit erlaubten Absendernummern.
- Einseitiger Audio-Pfad zum SIP-Telefon/Lautsprecher 100; Zielmikrofon bleibt stumm.
- Optionaler Auto-Answer per SIP-Header, nur für die Durchsage-Rolle.
- Optionale sechsstellige PIN, begrenzte Dauer und Schutz vor parallelen Durchsagen.
- Normale Anrufe behalten normales Klingeln und normale Hauptrufnummer.

# 26.10.3

- Bis zu acht getrennte Rufnummernkonten mit eigenen Anbietern, Zugangsdaten und Status.
- Hauptrufnummer für normale ausgehende Anrufe, weitere normale Rufnummern im Anrufpad auswählbar.
- Eingehend normale Anrufe oder Abweisen; unbekannte Zielnummern werden abgewiesen.
- Eindeutiges Routing auch bei mehreren Konten auf demselben SIP-Registrar.
- Bestehende Einzelkonto-Konfiguration wird übernommen.

# 26.10.2

- Anbieter-Auswahl: Telekom, sipgate, easybell, FRITZ!Box und manuelle Profile für Vodafone, 1&1, o2 und eigene SIP-Konten.
- Individuelle SIP-ID, Registrar, Domain, Proxy, Realm sowie UDP/TCP.
- Gespeicherte Zugangsdaten werden bei Anbieterwechsel nicht übernommen.
- Release-ZIP und SHA-256 werden vor dem Upload geprüft.

# 26.10.1

- HAOS-Add-on mit Asterisk und deutschem Telekom-Onboarding.
- Geschützte HA-Einrichtung, lokale Telefonseite und SIP-Nebenstelle 100.
- Echte lokale SIP-Anmeldung mit Sonderzeichen im Passwort wird in CI geprüft.

# Changelog

## 0.1.0

- HAOS-Add-on mit Asterisk 20 aus Alpine Linux.
- Deutsches Onboarding für Telekom Privatkunden.
- Lokale Speicherung von Zugangsdaten, Ingress-Einrichtung und gesicherter LAN-Zugang.
- Registrierung von SIP-Telefon 100, Echo-Test 600 und Anrufauslösung über lokalen AMI.
- Statusanzeige für Asterisk, Telekom-Registrierung und SIP-Telefon.
- Keine Kiosk-Intercom-Audio-Bridge enthalten.
