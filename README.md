# Kiosk Satellite SIP

Kiosk Satellite SIP ergänzt [Kiosk Satellite](https://github.com/jxlarrea/kiosk-satellite) um Telefonie über einen SIP-Anschluss. Ein schwebender Telefonknopf öffnet einen nativen Android-Dialer. Gespräche werden über einen zentralen Asterisk-Telefonserver mit dem Telefonanbieter verbunden.

Das Projekt besteht aus zwei separat installierten Komponenten:

| Komponente | Aufgabe |
| --- | --- |
| Kiosk-Satellite-Plugin | Nummerneingabe, Gesprächsanzeige, Mikrofon und Lautsprecher am Android-Gerät |
| Home-Assistant-OS-App | Asterisk-Telefonserver, Anbieteranbindung, Rufnummern und Geräteverwaltung |

Mehrere Kiosks können eigene SIP-Nebenstellen verwenden. Eine Nebenstelle ist die lokale Kennung eines Telefongeräts am Server. Für jede externe Rufnummer lässt sich festlegen, welche Geräte bei einem eingehenden Anruf klingeln. Sobald ein Gerät annimmt, endet das Klingeln an den übrigen Geräten.

## Voraussetzungen

- Home Assistant OS (HAOS) auf einem amd64-System.
- Android 7/API 24 oder höher und eine Kiosk-Satellite-Version mit SDK-1-Overlays und geheimen Plugin-Einstellungen.
- Ein unterstütztes SIP-Konto oder eine lokale Telefonanlage mit SIP-Zugang.
- Netzwerkverbindung zwischen Android-Gerät und Home-Assistant-System sowie Mikrofonberechtigung für Kiosk Satellite.

Anbieterprofile sind für Telekom Privatkunden, sipgate, easybell und FRITZ!Box enthalten. Weitere registrierende SIP-Konten können über manuelle Profile eingerichtet werden.

## Installation und Einrichtung

Für die Home-Assistant-App und den Kiosk-Satellite-Plugin-Manager gilt dieselbe Repository-URL:

```text
https://github.com/Eibelucas/Kiosk-Satellite-SIP
```

1. In Home Assistant unter **Einstellungen → Apps/Add-ons → Store → Repositories** das Repository hinzufügen. **Kiosk Satellite SIP Gateway** installieren und starten.
2. **Weboberfläche öffnen** und Anbieter, Rufnummer sowie lokale Netzwerkadresse einrichten. Eine **Standardrufnummer für ausgehende Anrufe** auswählen.
3. Als Audio-Ziel **SIP-Telefon / Softphone 100** wählen. Für ein Gerät die Nebenstelle 100 mit Passwort einrichten. Für mehrere Geräte unter **Mehrere native Kiosks / SIP-Geräte** getrennte Nebenstellen von 101 bis 199 mit jeweils eigenem Passwort anlegen.
4. **Kiosk Satellite SIP** im Plugin-Manager von Kiosk Satellite installieren und aktivieren.
5. Die Verbindungsdaten im Plugin eintragen:

| Plugin-Einstellung | Wert |
| --- | --- |
| HAOS-IP / Asterisk | Lokale IPv4-Adresse des Home-Assistant-OS-Systems |
| Asterisk SIP-Port | Im Einrichtungsassistenten festgelegter SIP-Port; Standard 5070 |
| Eigene Nebenstelle | Nummer des eingerichteten SIP-Geräts, beispielsweise 100 oder 101 |
| SIP-Passwort dieses Geräts | Passwort der zugehörigen Geräte-Nebenstelle |

Die Anzeige **Bereit · Nebenstelle …** bestätigt die Registrierung. Die Nebenstelle **600** im nativen Dialer führt einen lokalen Echo-Test aus. Nach erfolgreichem Audiotest können externe Telefonnummern gewählt werden.

[Ausführliche Einrichtung und Fehlerbehebung](kiosk_sip/DOCS.md)

## Bedienung

Den Telefonknopf antippen, eine Nummer eingeben und **Anrufen** wählen. Die Gesprächsansicht zeigt Zielnummer, Status und Gesprächsdauer. **Stumm** schaltet das Mikrofon aus, **Auflegen** beendet das Gespräch. Einklappen schließt nur die Ansicht; das Gespräch bleibt bestehen. Gedrückthalten der Taste **0** fügt am Anfang einer Nummer ein Pluszeichen ein.

Eingehende Gespräche werden mit **Annehmen** oder **Ablehnen** bedient. Interne Gespräche zwischen Kiosks stehen weiterhin über die Gegensprechanlage von Kiosk Satellite zur Verfügung.

## Updates

Plugin und Home-Assistant-App werden separat aktualisiert. Version 26.10.13 enthält den nativen Dialer und die Mehrgeräteverwaltung. Das Add-on 26.10.12 ist weiterhin mit einer einzelnen Nebenstelle 100 verwendbar.

Beim Update von Plugin 26.10.12 auf 26.10.13 ersetzt der native Dialer den bisherigen Web-Telefonstarter. Die SIP-Verbindungsdaten müssen einmalig im Plugin gesetzt werden. Die Plugin-ID bleibt `kiosk-satellite-sip`. Gespeicherte Anbieter- und Add-on-Konfigurationen bleiben erhalten.

Bei einer vorhandenen Installation des separaten **SIP Native Dialer Lab** dieses Plugin vor Aktivierung des regulären Plugins deaktivieren. Die beiden Plugin-IDs führen getrennte Einstellungen und können dieselbe SIP-Nebenstelle nicht gleichzeitig verwenden.

## Funktionsumfang und Grenzen

Der native Dialer verwendet IPv4, UDP und G.711 im lokalen Netzwerk. DTMF während eines Gesprächs, Halten, Vermitteln, TLS/SRTP und die Übernahme von Kontakten in den nativen Dialer sind noch nicht umgesetzt.

Die gemeinsame Mikrofonverwaltung mit Voice Satellite ist noch offen. Bei erkannter aktiver Sprachaufnahme oder Intercom-Sitzung blockiert das Plugin einen neuen Anruf. Die Audiopufferung begrenzt Rückstau; die tatsächliche Sprachverzögerung ist von Gerät und Netzwerk abhängig. Ein gemessener Latenzvergleich liegt nicht vor.

Die Web-Telefonseite mit Kontakten und die Audio-Brücke zu KS-Intercom bleiben als alternative Betriebsarten verfügbar. Deren Einrichtung und Anrufablauf sind in der [HAOS-Dokumentation](kiosk_sip/DOCS.md) beschrieben.

## Weitere Informationen

- [Releases und Paketformat](RELEASES.md)
- [Implementierung und automatisierte Tests](native-lab/README.md)
- [Änderungsprotokoll](kiosk_sip/CHANGELOG.md)
- [Veröffentlichte Versionen](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases)

## Lizenz

Apache-2.0; siehe [LICENSE](LICENSE) und [NOTICE](NOTICE). Kiosk Satellite ist ein separates Projekt und wird nicht mitgeliefert.
