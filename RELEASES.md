# Releases 26.10

Versionen folgen dem gewünschten Format Jahr.Monat.Update, z. B. `26.10.1`. Die Git-Tags heißen `v26.10.1`. Plugin und HAOS-Add-on verwenden dieselbe Version, müssen aber separat installiert/aktualisiert werden.

| Schritt | Release | Inhalt |
| --- | --- | --- |
| 1 | [26.10.1](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.1) | HAOS-Add-on mit Asterisk und Telekom-Onboarding |
| 2 | [26.10.2](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.2) | Mehrere Anbieter und manuelle SIP-Profile |
| 3 | [26.10.3](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.3) | Getrennte Rufnummern, normale Hauptrufnummer, Migration |
| 4 | [26.10.4](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.4) | Separate Durchsage-Nummer, Absenderliste, optionale PIN, einseitiges Audio |
| 5 | [26.10.5](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.5) | Kontakte als Kiosk-/Raumkarten, Favoriten, Suche und vollständige Anleitung |
| Korrektur | [26.10.6](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.6) | Dynamischer HA-Ingress-Port und erreichbare Einrichtung bei SIP-/LAN-Portkonflikten |
| Bereinigung | [26.10.7](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.7) | Allgemeine Dokumentation und neutrale Beispiele |
| Korrektur | [26.10.8](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.8) | Präzise Heimnetz-Prüfung und kein vorbelegtes Beispielnetz |
| Audio | [26.10.9](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.9) | Native Intercom-Audio-Brücke für ein Kiosk-Gerät, normales Klingeln, einseitige Durchsage und Echo-Test |

| Oberfläche | [26.10.10](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.10) | Responsive Einrichtung und Telefonseite, weniger Leerraum und kompaktere Übersicht |

| Telefonansicht | [26.10.11](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.11) | Wähltasten als Standard, weniger Text und direkter Kontakte-Befehl |

## Installieren und aktualisieren

Repository-URL für **Kiosk Satellite → Plugin-Manager → Repository hinzufügen**:

```text
https://github.com/Eibelucas/Kiosk-Satellite-SIP
```

Für **Home Assistant → Apps/Add-ons → Store → Repositories** dieselbe URL. Dort **Kiosk Satellite SIP Gateway** installieren, starten und die Weboberfläche öffnen. Die gesamte Einrichtung einschließlich Zugangsdaten erfolgt lokal dort. [Anleitung](kiosk_sip/DOCS.md).

Die Releases sind öffentlich, stabil, kein Draft und kein Pre-Release. Der Workflow `build-plugin.yml` reagiert auf `release: published`, baut den getaggten Quellstand und lädt drei Dateien als `github-actions[bot]` hoch:

- `kiosk-satellite-sip-VERSION.zip`
- `kiosk-satellite-plugin.json`
- `kiosk-satellite-sip-VERSION.zip.sha256`

Der Upload erfolgt nach Prüfung der ZIP: genau Manifest, `plugin.jar` mit Android-DEX und `LICENSE` im Root. Das Manifest in der ZIP und als Asset muss bytegleich sein. Die SHA-256-Datei enthält den tatsächlichen ZIP-Hash und den Dateinamen. Die Prüfung läuft in jedem Plugin-Build, auch für neue stabile Releases.

## Automatisierte Prüfungen

[GitHub Actions](https://github.com/Eibelucas/Kiosk-Satellite-SIP/actions) prüft:

- Konfiguration, Migration, Anbieter, Mehrfachkonten und eindeutige Ziel-IDs.
- Redaktion und Erhalt von Geheimnissen; Konfigurationsdateien mit eingeschränkten Rechten.
- Socket-basierte HA-Ingress-Prüfung, LAN-Anmeldung, CSRF und Ratenlimits.
- Ausgehende Anrufe nur auf aktiven normalen Konten; tatsächliche AMI-Anfrage für das ausgewählte Konto.
- amd64-Docker-Image und echte Asterisk-Instanz.
- Echte lokale SIP-Digest-Anmeldung mit Sonderzeichen im Passwort.
- Lokalen DNS-Testserver für SIP-SRV und drei lokale SIP-Anbieterkonten.
- Normales Klingeln auf der Hauptnummer, Abweisung der zweiten Nummer und unbekannter Ziele.
- Abweisung fremder/anonymer Absender auf der Durchsage-Nummer.
- Auto-Answer-Header nur auf der Durchsage, tatsächliche RTP-Übertragung zum Ziel und stummes Zielmikrofon.
- Kontakt-/Kiosk-Karten und JavaScript-Syntax.
- Native Intercom-Signalisierung, HMAC-Token, Annahme/Auflegen, 16-kHz-Audio in beide Richtungen und kein Mikrofon-Rückweg bei Durchsagen.
- Echten Asterisk-AudioSocket-Pfad mit lokalem Echo und simuliertem Kiosk; kein externer Anruf.

Dabei werden ausschließlich fiktive Zugangsdaten und lokale Testserver verwendet. Es wird kein externer Testanruf gewählt. Die unterschiedlichen realen Anbieteranschlüsse, Router-NAT, das Header-Auto-Answer deines Geräts und Home-Assistant-Supervisor auf dem eingesetzten HAOS-System müssen vor Ort geprüft werden.

## Verbleibende Grenze

Audio geht wahlweise über SIP-Telefon **100** oder die native Audio-Brücke zu einem konfigurierten Kiosk Satellite Intercom. Kiosk-Audio verwendet derzeit lokale HTTP/WS-Verbindungen; TLS-Intercom wird abgewiesen und bleibt unverändert. Kiosk-Karten sind die Darstellung von Kontakten im Anrufpad, keine automatisch registrierten nativen Intercom-Peers. TLS/SRTP, reine IP-authentifizierte Trunks und gemeinsame Trunk-Registrierungen für mehrere Durchwahlen sind keine fertigen Profile.
