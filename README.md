# Kiosk Satellite SIP

Ab **26.10.13** öffnet ein schwebender Telefonknopf einen nativen Android-Dialer im KS-Design. Ausgehende Anrufe laufen direkt per SIP über deinen Asterisk zum Anbieter: **Anrufen** benötigt keine zusätzliche Annahme am eigenen Kiosk. Eingehende Anrufe bleiben manuell anzunehmen.

- Telefonknopf mit einstellbarer Seite und Abstand zur Navbar; antippen zum Ausklappen.
- Gesprächsansicht mit einer Zielnummer, Verbindungsstatus, Dauer, Stumm und Auflegen. Einklappen lässt das Gespräch bestehen.
- Getrennte Nebenstellen für mehrere Kiosks und Klingelgruppen je externer Rufnummer. Nimmt ein Kiosk an, hören die anderen auf zu klingeln.
- RTP-Empfang und Wiedergabe arbeiten getrennt; die PCM-Warteschlange ist auf 60 ms begrenzt. Android erhält kleinere Pufferanforderungen. Die tatsächliche Ende-zu-Ende-Latenz hängt weiterhin vom Gerät und der Verbindung ab.
- Interne Kiosk-Anrufe übernimmt weiterhin KS-Intercom.

## Installieren

Für Plugin-Manager und HAOS-App-Store dieselbe Repository-URL verwenden:

```text
https://github.com/Eibelucas/Kiosk-Satellite-SIP
```

1. HA → Einstellungen → Apps/Add-ons → Store → Repositories: URL hinzufügen. **Kiosk Satellite SIP Gateway** auf einem unterstützten amd64-System installieren oder aktualisieren und starten.
2. **Weboberfläche öffnen**: SIP-Anbieter, Anschluss und Heimnetz einrichten. Unter **Standardrufnummer für ausgehende Anrufe** deine gewünschte Hauptrufnummer auswählen.
3. Für den nativen Dialer **SIP-Telefon / Softphone 100** als Audio-Ziel wählen. Ein lokales Geräte-SIP-Passwort für Telefon 100 hinterlegen oder unter **Mehrere native Kiosks / SIP-Geräte** eigene Geräte 101–199 mit jeweils anderem Passwort anlegen. Die Anbieter-Zugangsdaten bleiben im Add-on.
4. **Kiosk Satellite SIP** im KS-Plugin-Manager aus dem Repository installieren oder aktualisieren. Erfordert eine aktuelle KS-Version mit SDK-1-Overlays und Android 7/API 24 oder höher.
5. Im Plugin **HAOS-IP / Asterisk**, den **tatsächlichen Asterisk SIP-Port** (Vorgabe 5070), **Eigene Nebenstelle** und **SIP-Passwort dieses Geräts** setzen. IP und Port entsprechen den Werten im HA-Assistenten; keine Web- oder Remote-Admin-Ports verwenden.
6. Für den ersten Audiotest Wake Word und andere Mikrofonaufnahmen pausieren. **600 im nativen Dialer** ist der lokale Asterisk-Echo-Test. Danach beidseitigen Ton, Stumm und Auflegen mit einem gewünschten externen Anruf prüfen.

Für mehrere Geräte das Add-on ebenfalls auf **26.10.13** aktualisieren. Das bisherige Add-on 26.10.12 bleibt für die Nebenstelle **100** verwendbar. Pro Gerät wird eine eigene Registrierung geführt. Welche Kiosks bei einer externen Rufnummer klingeln, lässt sich im HA-Assistenten auswählen; ohne Auswahl klingeln alle aktiven Geräte der Geräteliste.

## Update von 26.10.12 oder vom Lab

Die reguläre Plugin-ID bleibt **kiosk-satellite-sip**. Das Update ersetzt den alten Web-Telefonstarter durch den nativen Dialer. Die bisherige **Gateway URL** reicht dafür nicht: die vier SIP-Einstellungen aus Schritt 5 müssen einmal gesetzt werden. Geräte-SIP-Passwort, Anbieter-Passwort und Web-Passwort sind unterschiedliche Zugänge.

Das separate Plugin **SIP Native Dialer Lab** vor Aktivierung des regulären Plugins deaktivieren. Seine Einstellungen werden wegen der anderen Plugin-ID nicht automatisch übernommen. Beide Plugins mit derselben Nebenstelle gleichzeitig zu betreiben verdrängt die Registrierung und kann den lokalen SIP-Port belegen.

Anschlussdaten, Kontakte und bestehende Add-on-Einstellungen bleiben in `/data` erhalten. Kontakte und Favoriten sind weiter über die vorhandene Web-Telefonseite verfügbar; der neue native Dialer enthält noch keine Kontaktsynchronisation. **600 in der alten Web-Telefonseite ist kein lokaler Echo-Test**, da diese Seite den ausgehenden Anbieter-Kontext verwendet.

## Dokumentation und Grenzen

- [HAOS-Einrichtung, Anbieter und Durchsagen](kiosk_sip/DOCS.md)
- [Native Implementierung und Testumfang](native-lab/README.md)
- [Release-Verlauf und Paketprüfung](RELEASES.md)
- [Aktuelles Release](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/latest)

Der native Dialer verwendet IPv4, UDP und G.711 zu einem Asterisk im LAN. TLS/SRTP, DTMF während des Gesprächs, Halten und Vermitteln sind noch nicht umgesetzt. Die gemeinsame Mikrofonverwaltung mit KS/Voice Satellite ist offen: erkannte aktive Aufnahme oder Intercom-Sitzung blockiert den Anruf. Die neue Audiopufferung ist automatisiert getestet, ihre Wirkung auf die Sprachverzögerung muss noch am Gerät verglichen werden. Ein externer Anruf mit der vorherigen Lab-Version wurde vom Nutzer bestätigt.

Das Add-on bietet weiterhin mehrere Anbieter und bis zu acht externe SIP-Konten, die bisherige KS-Intercom-Audio-Brücke und die Web-Telefonseite. Der ursprüngliche Standalone-Prototyp liegt unter `gateway/`.

## Lizenz

Apache-2.0; [Attribution](NOTICE). Kiosk Satellite ist ein separates Projekt und wird nicht mitgeliefert.
