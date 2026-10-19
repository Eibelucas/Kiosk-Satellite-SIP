# Native Dialer Lab

Dieser Entwicklungszweig erprobt ein natives Telefon in Kiosk Satellite. Er ist **kein fertiges Release**. Der bestehende HAOS-Code bleibt erhalten; der experimentelle Plugin-Build verwendet die separate ID `kiosk-satellite-sip-native-lab` und Version `26.10.13-lab.1`.

## Bedienung

- Ein schwebender Telefonknopf sitzt rechts unten, mit einstellbarer Seite und Abstand zur Navbar.
- Antippen klappt ein natives Android-Wählfeld aus demselben Overlay auf. Kein Browser, kein WebView und kein Browser-Bestätigungsdialog.
- **Anrufen** sendet direkt einen SIP INVITE an Asterisk. Es gibt keinen Rückruf zum eigenen Kiosk und keinen lokalen Annehmen-Schritt für ausgehende Anrufe.
- Die Ansicht folgt Verbindungsaufbau, Klingeln beim Ziel, Gesprächsdauer, Abbruch und Auflegen. Stumm schickt stille Audiodaten.
- Gedrückthalten der 0 fügt am Anfang ein Plus ein. Das native Wählfeld öffnet keine zusätzliche Bildschirmtastatur.
- Einklappen lässt einen laufenden Anruf bestehen. Der Telefonknopf öffnet die Gesprächssteuerung wieder.
- Eingehende SIP-Anrufe behalten **Annehmen / Ablehnen**. Sie werden nicht automatisch angenommen.

## Aufbau

`Telefonknopf → nativer Dialer → SIP-Nebenstelle 100 → bestehender Asterisk → Hauptrufnummer / Anbieter`

Audio läuft direkt zwischen dem Plugin und Asterisk über G.711/RTP. Die bisherigen Anbieter-Zugangsdaten bleiben im HAOS-Add-on. Das Plugin braucht nur dessen lokale IP, SIP-Port und das **SIP-Passwort von Telefon 100**. Dieses Passwort nutzt den SDK-Einstellungstyp `secret`.

Das ist ein zweiter Audioansatz neben der bisherigen nativen KS-Intercom-Brücke. Er verwendet deren Rückrufmechanismus nicht und ändert keine globale automatische Annahme.

## Am eigenen Gerät ausprobieren

1. Eine aktuelle Kiosk-Satellite-Version mit nativen SDK-Overlays, `secret`-Einstellungen und den dokumentierten Host-Zuständen verwenden (Referenz-SDK vom 19.10.2026; Navbar nennt 2026.10.23 als Mindeststand).
2. Im bestehenden HAOS-Add-on als Audio-Ziel **SIP-Telefon 100** auswählen, dessen Passwort setzen und die Konfiguration speichern. HAOS-IP, lokales Netz und SIP-Port müssen zum Gerät passen.
3. Andere SIP-Geräte auf Nebenstelle 100 abmelden. Asterisk lässt nur eine Registrierung zu.
4. Die Lab-ZIP über **Plugin-Manager → Developer Tools → Install from ZIP** installieren. Noch kein Community-/Stable-Release dieses Experiments veröffentlichen.
5. Im Lab-Plugin HAOS-IP, den tatsächlichen Asterisk-SIP-Port (Vorgabe `5070`) und das Telefon-100-Passwort eintragen. Lokaler Plugin-Port ist `5090`.
6. Für diesen Audioversuch Wake Word und andere Mikrofonaufnahmen pausieren. Das Plugin verändert keine dauerhafte Wake-Word-Einstellung. Bei gemeldeter aktiver Aufnahme oder Intercom-/Sprachsitzung blockiert es den Anruf.
7. Erst den Telefonknopf und das Ein-/Ausklappen prüfen. Danach **600 im nativen Dialer** wählen: Die Anmeldung als Telefon 100 landet im bestehenden `from-phone`-Kontext, der 600 ausdrücklich lokal als Echo behandelt. Dies ist etwas anderes als 600 in der alten Web-Telefonseite.
8. Mikrofonberechtigung, beidseitiges Echo, Stumm, Auflegen, Gegenstellen-Auflegen, Einklappen während eines Gesprächs und Plugin-Deaktivierung prüfen. Erst danach einen gewünschten externen Anruf versuchen.

Zum Zurückkehren das Lab-Plugin deaktivieren und das bisherige Audio-Ziel wieder wählen. Anbieter- und Kontaktkonfiguration werden vom Lab-Plugin nicht geschrieben.

## Was automatisiert geprüft wird

`python tools/test_native.py` kompiliert SDK und Plugin gegen Android 35 und prüft echte UDP-SIP-Pakete gegen einen lokalen simulierten PBX. Die Medienquelle ist dabei ein Testobjekt: **Diese Tests öffnen kein echtes Mikrofon und bestätigen keine Audioqualität.**

- Digest-Anmeldung und authentifizierter ausgehender INVITE.
- Direkter Anruf ohne lokale Annahme.
- Mikrofonstart erst nach erfolgreicher Gegenstellen-Antwort.
- Doppelte SIP-Antworten, Abbruch vor dem Klingeln und Annahme/Abbruch-Kollision.
- Besetzt, eingehende manuelle Annahme, Gegenstellen-Auflegen und Plugin-Stopp.
- Abweisung von SIP-Antworten aus fremden UDP-Quellen.
- UDP-Wiederholungen, verspätete Antworten alter Anrufe, Medienfehler und G.711-/SDP-Grundfunktionen.
- Getrennter Zustand für geöffnetes Overlay und laufenden Anruf.

Der Build erzeugt eine Android-DEX-ZIP mit Manifest und Prüfsumme. GitHub Actions baut den Entwicklungszweig und hängt die ZIP als Workflow-Artefakt an; es wird kein Stable-Release erzeugt.

## Offene Grenzen

- Native Android-Darstellung, Mikrofon, Lautsprecher und Akustik wurden noch nicht auf dem Zielgerät geprüft. Es ist kein Android-Gerät mit dieser Sitzung verbunden.
- Für eine dauerhafte Integration fehlt die gemeinsame Mikrofon-/Audio-Fokus-Verwaltung mit KS und Voice Satellite. Das Lab blockiert bei erkennbarer Belegung, ersetzt aber keine vom Host koordinierte Audiositzung. Diese Grenze muss vor einer Übernahme gelöst werden.
- Ein direkt erreichbarer IPv4-Asterisk im LAN, UDP, G.711, eine Nebenstelle und die in HA konfigurierte Hauptrufnummer. Keine SIP-Proxys mit Record-Route, TLS/SRTP, DTMF während des Gesprächs, Halten, Vermitteln oder Mehrfachgespräche.
- Kontaktsynchronisation, Favoriten und Kontoauswahl sind noch nicht in den nativen Dialer übertragen.
- Der RTP-Prototyp nutzt direkte Android-Audio-APIs und lokalen Audio-Fokus, hat aber noch keinen Jitterpuffer und keine eigene Echo-Unterdrückung. Erkannte Aufnahme-/Wiedergabefehler beenden den Anruf; WLAN-Wechsel und ausbleibende RTP-Pakete brauchen weitere Gerätetests und Fehlerbehandlung.
- SIP-Timer und Abbruchfälle werden erprobt, der SIP-Code ist kein vollständiger RFC-3261-Stack. Kein produktiver Dauereinsatz ohne weitere Prüfung.

## Quellen und Lizenz

- [Kiosk Satellite Community SDK](https://github.com/jxlarrea/kiosk-satellite-plugins): SDK-Quellen, KsTheme und Overlay-Vertrag (Apache-2.0).
- [Navbar](https://github.com/dimatx/kiosk-satellite-navbar): Vorbild für einen langlebigen nativen Overlay mit aufklappenden Bedienelementen. Keine Navbar-Plugin-Quellen übernommen.
- [meiser79 SIP Phone](https://github.com/meiser79/kiosk-satellite-sip-phone): `SipMessage`, `SipDigest` und die Grundlage für `AndroidG711` (Apache-2.0). Paketnamen und Audio-Lebenszyklus wurden angepasst; der ausgehende SIP-Controller und Dialer wurden hier ergänzt.

Attribution steht außerdem in `NOTICE` und im mit der ZIP gelieferten `LICENSE`.
