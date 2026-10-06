# Einrichtung auf HAOS

Telefonseite ab **26.10.11**: **Telefon öffnen** startet mit den Wähltasten. **Kontakte öffnen** öffnet direkt Kontakte und Favoriten im Plugin. Ein Kontakt trägt die Nummer ein; erst **Anrufen** mit Bestätigung fordert den Anruf an. Die native KS-Gegensprechliste enthält weiterhin Kiosk-Geräte. SDK 1 hat keine Schnittstelle zum Eintragen von SIP-Telefonkontakten; dafür ist eine Änderung an Kiosk Satellite erforderlich.

Für HAOS auf einem unterstützten amd64-System (amd64). Kein separates Asterisk-Add-on erforderlich: Dieses Add-on enthält Asterisk und den SIP-Gateway.

## 1. Add-on installieren

1. Home Assistant → Einstellungen → Apps/Add-ons → Store öffnen.
2. Im Drei-Punkte-Menü **Repositories** wählen.
3. `https://github.com/Eibelucas/Kiosk-Satellite-SIP` hinzufügen.
4. **Kiosk Satellite SIP Gateway** öffnen und installieren. Das Image wird lokal gebaut; beim ersten Mal dauert das länger als ein Download.
5. Starten, **Beim Booten starten** aktivieren und **Weboberfläche öffnen** wählen.

Unter **Konfiguration** ist nur der Port der Kiosk-Telefonseite einstellbar (Standard `8088`). Die Anbieter-Einrichtung erfolgt in der Weboberfläche. Nach Änderung des Ports das Add-on neu starten.

Ab **26.10.6** weist Home Assistant den internen Ingress-Port dynamisch zu. Ein anderer Dienst auf `8099` verhindert die Einrichtung dadurch nicht mehr. Dazu liest das Add-on ausschließlich seine eigenen Informationen über die Supervisor-API mit der Standardrolle; der Supervisor-Token wird nicht angezeigt oder gespeichert.

**Bei einem vorhandenen Startfehler:** Im Add-on-Store nach Updates suchen, das **HA-Add-on auf 26.10.9 aktualisieren** und neu starten. Das Aktualisieren des Kiosk-Plugins allein repariert den HA-Container nicht. Anschließend **Weboberfläche öffnen**. Wenn dort ein belegter SIP-Port gemeldet wird, unter **Heimnetz → SIP-Port** einen freien Port eintragen, z. B. `5072`, und speichern. Am SIP-Telefon denselben Port setzen. Gespeicherte Rufnummern und Zugangsdaten bleiben erhalten; kein Neuinstallieren oder Löschen nötig.

Bei belegtem SIP-/AMI-Port bleibt die HA-Einrichtung erreichbar und zeigt den Fehler. Ein belegter LAN-Webport deaktiviert nur die Kiosk-Webseite: unter **Add-on-Konfiguration → gateway_port** einen freien Port wählen und neu starten. Der tatsächliche SIP-Status steht im Assistenten; ein erreichbares Add-on bedeutet nicht automatisch einen angemeldeten Anschluss.

Falls das Add-on nicht erscheint: Store neu laden und sicherstellen, dass die URL ohne `/tree/…`, `/releases/…` oder Dateipfad eingetragen ist. Die App unterstützt derzeit ausschließlich amd64.

## 2. Anbieter-Onboarding

Wähle deinen Anbieter. Die Profile sind Konfigurationshilfen, keine Bestätigung eines Live-Tests deines Anschlusses.

| Profil | Vorgabe / Zugang |
| --- | --- |
| Telekom Privatkunden | `tel.t-online.de`, Anschluss-Anmeldung oder Telefonie-Daten; kein DeutschlandLAN/Regio |
| sipgate SIP-Gerät | `sipgate.de`, SIP-ID und Geräte-SIP-Passwort; kein trunking-Profil |
| easybell VoIP | `voip.easybell.de`, SIP-Zugang aus my.easybell; Anmelde-ID standardmäßig `0049…` |
| FRITZ!Box | Lokales IP-Telefon in der Box anlegen, dort Rufnummern zuweisen; Registrar/Domain `fritz.box` oder Router-IP |
| Vodafone, 1&1, o2 | Manuelle Profile: aktuelle SIP-Zugangsdaten des Anschlusses einschließlich Registrar/Domain übernehmen |
| Anderer Anbieter / PBX | Registrierendes SIP-Konto mit benutzerdefinierten Servern |

SIP-Benutzername und Passwort sind vom Web-Login getrennt. Groß-/Kleinschreibung bleibt erhalten; nur Telekom verlangt hier Kleinschreibung. Bei Anbieterwechsel ist ein neues SIP-Passwort nötig. Noch keine TLS/SRTP-Unterstützung und keine reinen IP-authentifizierten Trunks. UDP/TCP betrifft den Anbieter; Telefon 100 verwendet UDP.

Unter **Weitere SIP-Einstellungen** kannst du Client-User (Anmelde-ID), Contact-User (eingehende Ziel-ID), From-User, Realm, Proxy und STUN anpassen. Server als Hostname/IP, optional mit Port, niemals als `https://…` oder komplette SIP-URI eingeben. Bei Vodafone hängen diese Daten vom Anschluss/Netz ab.

Für Telekom gilt folgende Einordnung:

| Feld | Was du einträgst |
| --- | --- |
| Festnetznummer | Die eigene vollständige Rufnummer mit Landesvorwahl, ohne Leerzeichen |
| Telekom-Anmeldung | Zunächst Anschluss-Authentifizierung ohne Passwort, falls für deinen Zugang verfügbar; andernfalls Passwort-Anmeldung |
| Authentifizierungsname | Bei Passwort-Anmeldung: der gültige Telekom-Authentifizierungsname, in Kleinschreibung |
| Telekom-Passwort | Das zu diesem Zugang gehörende Telefonie-Passwort gemäß Telekom-Hilfe; nicht ungeprüft das separate E-Mail-Programm-Passwort |
| NAS-IP | Die eigene lokale IPv4-Adresse des HAOS-Systems; im Router dauerhaft zuordnen |
| Heimnetz | Das eigene IPv4-Heimnetz in CIDR-Schreibweise |
| SIP-Port | Standard `5070`; am SIP-Telefon denselben Port verwenden |
| Externe Adresse | Optional deine aktuelle öffentliche IPv4-Adresse, wenn die RTP/NAT-Konfiguration sie benötigt |
| Passwort für Telefon 100 | Ein eigenes, langes Passwort für das SIP-Telefon/Softphone |
| LAN-Zugriff | Aktivieren, damit der Kiosk die Telefonseite erreichen kann |
| Kiosk-Benutzer/Passwort | Eigener Zugang für die Web-Telefonseite; keine Telekom-Daten verwenden |

Der Assistent setzt Registrar, SIP-Domäne und Proxy-Ziel auf `tel.t-online.de`. Es wird kein bestimmter Telekom-Server als feste IP eingebaut; die SIP-Zielauflösung erfolgt per DNS. Bei Anschluss-Authentifizierung wird kein Passwort-Digest konfiguriert. Wird die Registrierung abgelehnt, gültige Telekom-Zugangsdaten verwenden und neu speichern.

**Speichern** schreibt die Konfiguration und startet Asterisk neu. Damit werden laufende Gespräche unterbrochen. Passwörter bleiben bei späterem Speichern erhalten, wenn ihre Eingabefelder leer bleiben; die Anschluss-Authentifizierung löscht ein vorher gespeichertes Telekom-Passwort. Die Oberfläche gibt gespeicherte Passwörter nicht zurück.

**Danach das Add-on einmal neu starten**, wenn LAN-Zugriff oder NAS-Adresse geändert wurden. Der LAN-Webserver bindet beim Start an die eingetragene NAS-IP. Asterisk bindet den SIP-Port ebenfalls an diese IP.

## Mehrere Rufnummern und Hauptrufnummer

Unter **Rufnummer hinzufügen** legst du bis zu acht einzelne SIP-Konten an. Telekom: höchstens fünf aktive Konten, wobei andere SIP-Clients am Anschluss mitzählen. Jede Rufnummer hat einen Namen, eine eigene Anbieter-Konfiguration und einen Status. Gespeicherte Konten werden intern an ihrer Konto-ID erkannt; Umsortieren ändert ihre Passwörter nicht.

- **Normal auf Telefon 100 klingeln**: normale eingehende Gespräche, ohne Auto-Answer.
- **Abweisen**: Konto darf registriert bleiben, eingehende Anrufe werden abgewiesen. Geeignet zum Vorbereiten einer zweiten Nummer.
- **Dieses Konto registrieren** aus: keine Anmeldung beim Anbieter.
- **Standardrufnummer für ausgehende Anrufe**: deine normale Hauptrufnummer. Alternativ keine ausgehenden Anrufe. Das Anrufpad kann eine andere aktive normale Nummer auswählen.

Deine bestehenden Telekom-Daten werden als **Hauptrufnummer** übernommen. Alte `/data/telekom.json` bleibt der Speicherort; keine Passwörter ins Git-Repository kopieren. Bei Wechsel des SIP-Benutzers, Registrars oder der Anmelde-ID ist ein neues SIP-Passwort nötig.

Für die eingehende Zuordnung nutzt Asterisk die konkrete Ziel-ID: internationale Nummer, nationale deutsche Schreibweise und die konfigurierte Client-/Contact-ID. Konten auf demselben Registrar müssen eindeutige Ziel-IDs haben. Unbekannte Ziele werden abgewiesen und können keine externen Nummern wählen. Ein gemeinsamer SIP-Trunk mit einer Registrierung für mehrere Durchwahlen ist derzeit kein fertiges Trunk-Profil; lege separate SIP-Geräte/Konten an, soweit dein Anbieter dies unterstützt.

Bei einer FRITZ!Box für jede Rolle ein eigenes IP-Telefon anlegen und in der Box **nur die zugehörige eingehende Nummer** zuweisen. Sonst kann die Box schon vor dem Add-on mehrere Nummern auf denselben SIP-Benutzer zusammenführen.

## Eigene Rufnummer für Durchsagen

So richtest du das gewünschte Beispiel ein, ohne die Hauptnummer umzuwidmen:

| Konto | Rolle | Beispiel |
| --- | --- | --- |
| Hauptrufnummer | Normal auf Telefon 100 klingeln | `<HAUPTRUFNUMMER>` |
| Separate zweite Nummer | Durchsage von erlaubten Nummern | `<DURCHSAGE-RUFNUMMER>` |
| Erlaubter Absender für die zweite Nummer | Eigene vollständige Anrufernummer | `<ERLAUBTE-ANRUFERNUMMER>` |
| Standard ausgehend | Hauptrufnummer | Normale Gespräche verwenden die erste Nummer |

1. Deine Hauptnummer als normales Konto lassen.
2. Zweites SIP-Konto hinzufügen, dessen eigene Rufnummer und eigene passende Zugangsdaten eintragen.
3. Bei **Eingehende Anrufe** die Rolle **Durchsage von erlaubten Nummern** wählen.
4. Die tatsächlichen erlaubten Absender international mit `+` eintragen, eine pro Zeile. Kein Platzhalter, keine anonyme Nummer. Die nationale deutsche und `0049…`-Schreibweise werden im eingehenden Anruf ebenfalls berücksichtigt.
5. Optional eine **PIN mit sechs Ziffern** setzen. Eine angezeigte Absendernummer kann gefälscht sein: Die Nummernliste ist keine sichere Authentifizierung. Die PIN ergänzt sie. Zum Entfernen ausdrücklich **Gespeicherte PIN entfernen** wählen; ein leeres Feld behält sie.
6. **Auto-Answer auf Telefon/Lautsprecher 100 anfordern** bei Bedarf aktivieren. Am SIP-Gerät Auto-Answer **nur bei passenden SIP-Headern** konfigurieren, nicht pauschal bei jedem Anruf. Unterstützt werden `Call-Info: …;answer-after=0` und `Alert-Info: …;info=alert-autoanswer`; die konkrete Geräteunterstützung prüfen.
7. Maximale Dauer setzen (10 bis 600 Sekunden, Standard 180), speichern und Status beider Nummern prüfen.
8. Von der erlaubten Nummer die **zweite Nummer** anrufen. Bei PIN: Nach Verbindungsaufbau innerhalb von 15 Sekunden die sechs Ziffern eingeben, eventuell mit `#` abschließen. Es gibt kein gesprochenes PIN-Menü. Danach sprechen.
9. Gegenprobe von einer fremden Nummer und mit unterdrückter Rufnummer: Der Anruf muss abgewiesen werden. Die Hauptnummer weiterhin separat auf normales Klingeln testen.

Bei SIP-Audio nutzt die Durchsage Asterisk Page mit stummem Zielmikrofon auf Telefon/Lautsprecher 100. Ohne unterstütztes Header-Auto-Answer muss dieses Ziel angenommen werden. Bei Kiosk-Audio nutzt sie den nativen Intercom-Durchsage-Modus: Kiosk Satellite spielt den Hinweis und die Stimme über seinen Lautsprecher ab; sein Mikrofon wird nicht zurück an den Absender gesendet. Durchsagen müssen am Kiosk erlaubt sein. Nicht stören und besetzte Kiosks werden respektiert.

Besetzte Ziele werden übersprungen; Anrufe werden nicht erzwungen unterbrochen. Jeweils eine Durchsage läuft; weitere werden abgewiesen. Der Raum endet beim Auflegen des Absenders oder beim Dauerlimit. Es gibt keine Aufzeichnung und keine externe Weiterleitung an die erlaubten Absendernummern.

Die Einstellungen hier ändern nicht die Nummernzuordnung im Router oder beim Anbieter. Bestehende Haustelefone dort behalten ihre bisherigen Zuordnungen; bei Bedarf die zweite Nummer dort von normalem Klingeln ausnehmen. Bei der FRITZ!Box pro Rolle ein eigenes IP-Telefonkonto und nur die zugehörige Nummer zuweisen.

## 3. SIP-Telefon anmelden und Audio testen

Das Kiosk-Plugin öffnet die Telefonseite. Die Audio-Verbindung ist separat im HA-Add-on wählbar: natives Kiosk Satellite Intercom oder ein SIP-Telefon. Die folgenden Telefon-100-Schritte gelten nur für SIP-Audio.

| Telefon-Einstellung | Wert |
| --- | --- |
| Server/Domain/Registrar | Die eigene lokale IPv4-Adresse des HAOS-Systems |
| Port | `5070` oder dein eingestellter SIP-Port |
| Transport | UDP |
| Benutzername | `100` |
| Authentifizierungs-ID | `100` |
| Passwort | Dein im Assistenten gesetztes Passwort für Telefon 100 |
| Codecs | G.711 A-law oder µ-law (PCMA/PCMU) |

1. Registrierung einschalten. In der HA-Weboberfläche auf **Aktualisieren** drücken. Telefon 100 muss angemeldet sein.
2. Auf dem SIP-Telefon **600** wählen. Dieser lokale Echo-Test ruft niemanden extern an. Wenn du dich selbst hörst, ist der lokale Audio-Pfad vorhanden.
3. Status der gewünschten Rufnummer prüfen: **registriert**. **wartet** ist kein Erfolgsnachweis; Registrierung kann einige Sekunden dauern.

Nur ein SIP-Gerät gleichzeitig auf Nebenstelle 100 verwenden. Ein neu angemeldetes Gerät ersetzt die bisherige Registrierung.

### Kiosk Satellite als Audio-Ziel ab 26.10.9

1. **Das HA-Add-on auf 26.10.9 aktualisieren**, neu starten und die Weboberfläche öffnen. Ein Plugin-Update allein installiert die Audio-Brücke nicht.
2. Am Android-Kiosk in **Einstellungen → Intercom** Intercom aktivieren und die Mikrofonberechtigung erlauben. Den gemeinsamen Intercom-Schlüssel anzeigen/kopieren. **Talk mode → Hands free** liefert Gegensprechen ohne gedrückte Sprechtaste; Push-to-talk funktioniert mit der Sprechtaste. Nicht stören verhindert Anrufe.
3. Im HA-Assistenten **Telefon → Audio-Ziel → Kiosk Satellite Intercom** auswählen. Die eigene lokale Kiosk-IP und den Identitätsport eintragen. Meist ist dies der Remote-Admin-Port **2324**. Der separate, dynamische Intercom-Listener-Port wird aus der Identitätsantwort übernommen. Alternativ ist sein aktueller Port direkt verwendbar. Keine IP/Rufnummer aus Anleitungen übernehmen.
4. Den gleichen **Intercom-Schlüssel** eintragen. Er bleibt lokal in der Add-on-Konfiguration mit eingeschränkten Dateirechten und wird nicht vom Status-/Setup-API zurückgegeben. Leer lassen behält ihn bei unveränderter Kiosk-IP. Bei Wechsel des Kiosks erneut eintragen.
5. Einen freien **Kiosk-Rückrufport** wählen, Standard **8090**. Der Kiosk muss die eigene HAOS-IP auf diesem TCP-Port erreichen können. Nur Meldungen der eingetragenen Kiosk-IP mit gültigem Einmal-Token für den aktiven Anruf werden angenommen. AudioSocket und FastAGI binden ausschließlich Loopback an dynamische Ports. Keine Router-Portfreigabe einrichten.
6. **Speichern und Asterisk starten**, anschließend **Kiosk-Verbindung prüfen**. Bei Änderung der LAN-Webadresse zusätzlich das Add-on neu starten. Es wird beim Speichern kein Anruf gestartet.
7. **Lokalen Kiosk-Echo-Test starten** drücken. Am Kiosk erscheint ein Anruf. **Annehmen**, sprechen und sich selbst hören; am Kiosk auflegen. Der Test wählt ausschließlich die lokale Asterisk-Echo-Nebenstelle 600, keine externe Nummer. Die Diagnose zeigt gesendete und empfangene Audio-Frames.
8. Erst danach eine eigene Testnummer im Anrufpad eingeben und **Anrufen** bestätigen. Der Kiosk klingelt zuerst. Erst nach dem Annehmen wird die externe Zielnummer gewählt. Ein normaler eingehender Anruf klingelt entsprechend am Kiosk.
9. Für separate Durchsagen am Kiosk **Accept announcements** erlauben. Die bisherige Absenderliste/PIN und das Dauerlimit bleiben aktiv. Ein erlaubter Durchsage-Anruf verwendet den einseitigen Intercom-Modus; das Kiosk-Mikrofon wird verworfen. Mit fremder/unterdrückter Absendernummer und mit Nicht stören gegenprüfen.

**Umfang und Grenzen:** Ein konfiguriertes Kiosk-Gerät, 16-kHz-PCM-Audio über den nativen Intercom-WebSocket. Kiosk Satellite kümmert sich um Mikrofon, Lautsprecher, seine Anrufanzeige und Echo-Unterdrückung. Die Brücke verwendet derzeit lokale HTTP/WS-Verbindungen. Wenn der Kiosk verschlüsseltes Intercom verlangt, wird die Verbindung mit Hinweis abgewiesen; die Einstellung wird nicht verändert. TLS-Intercom, mehrere Audio-Kiosks pro Anruf und externe Internet-Nutzung sind nicht enthalten. Ein echtes Android-Gerät, Mikrofonberechtigungen, Talk mode und Router-NAT sind nach dem automatisierten Echo-Test noch vor Ort zu prüfen.

Bei **Kiosk nicht erreichbar** die IP und den Identitätsport prüfen. Bei **anderer Schlüssel** den Intercom-Schlüssel beider Seiten vergleichen. Bei Klingeln ohne Audio den HAOS-Rückrufport, Mikrofonberechtigung, Talk mode und Audio-Frame-Zähler prüfen. Beim Auflegen muss die Anrufanzeige schließen. Der SIP-Telefon-Modus 100 bleibt wählbar; ein Update stellt bestehende Installationen nicht automatisch auf Kiosk-Audio um.

## 4. Kiosk verbinden

1. Im Kiosk Satellite Plugin-Manager das Plugin **Kiosk Satellite SIP** öffnen.
2. **Gateway URL** auf `http://NAS-IP:8088/` setzen. Bei geändertem Gateway-Port diesen verwenden.
3. **Telefon öffnen** ausführen.
4. Mit dem Kiosk-Benutzernamen und Kiosk-Passwort anmelden.
5. Kontakte im HA-Assistenten unter **Telefon → Kontakte und Kiosk-Karten** hinzufügen, oder direkt die Wähltasten verwenden.

Die Home-Assistant-Ingress-URL gehört nicht in die Plugin-Einstellung. Verwende die normale LAN-URL inklusive abschließendem `/`.

## 5. Erster externer Anruf

1. Eine eigene Testnummer auswählen/eingeben.
2. **Anrufen** drücken und die Rückruf-Anfrage bestätigen.
3. Das gewählte Audio-Ziel klingelt zuerst: bei **Kiosk Satellite Intercom** der konfigurierte Kiosk, bei **SIP-Telefon 100** das angemeldete SIP-Telefon.
4. Dort annehmen. Erst danach wählt Asterisk die externe Zielnummer über die ausgewählte normale Anbieter-Rufnummer. Kiosk-Audio benötigt keine Anmeldung von Telefon 100.
5. Zum Beenden am Kiosk bzw. SIP-Telefon auflegen.

Die Weboberfläche meldet die Annahme einer Rückruf-Anfrage, nicht das erfolgreiche Zustandekommen des externen Gesprächs. Der Bestätigungsdialog ist ein nativer Browser-/WebView-Dialog mit **OK** und **Abbrechen**. Abbrechen startet keine Anfrage; OK fordert zunächst den Rückruf auf das gewählte Audio-Ziel an. Solange der Dialog offen ist, wird keine Anruf-Anfrage gesendet. Die Anzeige auf dem eigenen Android-Kiosk muss vor Ort geprüft werden. DTMF-Tasten während eines Gesprächs und ein Auflegen-Button im Gateway sind derzeit nicht enthalten.

**Lokaler Test:** Für Kiosk-Audio ausschließlich **Lokalen Kiosk-Echo-Test starten** im HA-Assistenten verwenden. Dieser eigene API-Pfad wählt 600 im lokalen Echo-Kontext. **600 in das normale Anrufpad einzugeben ist kein lokaler Echo-Test:** `api/call` verwendet den Anbieter-Kontext und kann die Nummer über den Anbieter wählen. Der erste echte Telefon-Test sollte bewusst eine eigene, freigegebene Zielnummer verwenden.

Normale eingehende Anbieter-Anrufe klingeln am gewählten Audio-Ziel. Voraussetzung: Anbieter-Registrierung, korrekte Zuordnung der eingehenden Rufnummer und funktionierende Netzwerk-/Audio-Verbindung. Separate Durchsage-Rufnummern behalten ihre Absenderliste/PIN und das Dauerlimit. Es werden keine automatischen Testanrufe ausgelöst.

## Fehler beheben

| Symptom | Nächster Schritt |
| --- | --- |
| Asterisk startet nicht | Add-on-Protokoll lesen. NAS-IP muss auf HAOS tatsächlich vorhanden und SIP-Port frei sein. |
| `Address in use` auf `8099` / Ingress-Traceback | HA-Add-on auf 26.10.9 aktualisieren und neu starten; Ingress verwendet den von HA zugewiesenen Port. |
| `transport-udp`: `Address in use` | HA-Weboberfläche → Heimnetz → SIP-Port auf einen freien Port ändern und speichern; Telefon 100 auf denselben Port ändern. |
| AMI-Port `5038` belegt | Anderen lokalen Asterisk-/AMI-Dienst prüfen. Beide Dienste dürfen denselben Loopback-Port nicht gleichzeitig verwenden. |
| Telekom: abgelehnt | Rufnummer/Anschlusstyp prüfen, ggf. zur Passwort-Anmeldung wechseln. Authentifizierungsname und Rufnummer sind unterschiedliche Felder. |
| Telekom: wartet | DNS, Internetzugang und SIP-Verkehr am Router prüfen. Beim Verbindungsaufbau kurz warten, dann Status aktualisieren. |
| Private NAS-IP wird beim Speichern abgelehnt | Unter Heimnetz mit Netzmaske das tatsächliche lokale Netz eintragen. Eine private IP allein genügt nicht: Sie muss in diesem Netz liegen. Die Netzmaske in HA oder am Router prüfen; /24 entspricht 255.255.255.0. |
| Telefon 100 fehlt | NAS-IP, Port, UDP, Benutzer `100` und dessen eigenes Passwort prüfen. Beide Geräte müssen im angegebenen Heimnetz liegen. |
| Anrufen-Taste deaktiviert | Die ausgewählte ausgehende Rufnummer muss aktiviert, normal und beim Anbieter registriert sein. Unter Telefon das gewünschte Audio-Ziel prüfen: Kiosk Satellite Intercom braucht eine gestartete Audio-Brücke; SIP-Telefon 100 braucht ein angemeldetes SIP-Telefon. Für Kiosk-Audio ist Telefon 100 nicht erforderlich. Bei leerer Zielnummer wird keine Anfrage ausgelöst. |
| Echo-Test ohne Ton | Zuerst WLAN-Isolation, lokale Firewall und UDP/RTP prüfen; Telekom ist am lokalen Echo-Test nicht beteiligt. |
| Lokaler Ton funktioniert, extern kein/einseitiger Ton | NAT prüfen. Asterisk verwendet UDP `30000–30100` für RTP; Heimnetz und ggf. öffentliche IPv4 korrekt setzen. STUN ist ein Hilfsmittel, kein Ersatz für passende NAT-Regeln. |
| Kiosk-Seite unerreichbar | LAN-Zugriff aktivieren, Kiosk-Passwort setzen, Add-on neu starten, NAS-IP/Port prüfen. |
| Anmeldung nach Passwortänderung verloren | Erneut mit dem neuen Kiosk-Zugang anmelden. Bestehende Sitzungen werden ungültig. |
| Neue Konfiguration beendet ein Gespräch | Speichern startet Asterisk neu. Änderungen außerhalb laufender Gespräche durchführen. |

Keine pauschalen Portfreigaben anlegen. AMI `5038` bindet ausschließlich an Loopback; die Telefon-Weboberfläche ist nur für dein Heimnetz gedacht. Die Telekom-Hilfe beschreibt die je nach Router/Firewall erforderlichen SIP/RTP-Verbindungen. Dieses Add-on kann Routerregeln, SIP-ALG, CGNAT oder DS-Lite nicht automatisch reparieren. Bei wechselnder öffentlicher IPv4 eine manuell eingetragene externe Adresse aktualisieren und neu speichern.

## Daten und Backups

Anschlusskonfiguration, Kontakte, Sitzungsschlüssel und AMI-Schlüssel liegen im persistenten Add-on-Verzeichnis `/data`. SIP-Passwörter müssen Asterisk lokal im Klartext zur Verfügung stehen. Das Kiosk-Webpasswort wird als Hash gespeichert. Diese Daten sind nicht Teil des GitHub-Repositories, gehören aber zu Add-on-Backups; behandle solche Backups entsprechend vertraulich.

## Offizielle Quellen

- [Telekom: SIP-Client-Einstellungen](https://www.telekom.de/hilfe/internet-telefonie/telefonie/voice-over-ip-sip-client)
- [Home Assistant: App-/Add-on-Repositories](https://developers.home-assistant.io/docs/apps/repository/)
- [Home Assistant: Ingress und Präsentation](https://developers.home-assistant.io/docs/apps/presentation/)
- [Home Assistant: Dynamischer Ingress-Port bei Host-Netzwerk](https://developers.home-assistant.io/docs/apps/configuration/)
- [Home Assistant: Supervisor-API / App-Informationen](https://developers.home-assistant.io/docs/api/supervisor/endpoints/)
- [Asterisk: Outbound Registrations](https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/Configuring-Outbound-Registrations/)
- [Asterisk: NAT-Konfiguration](https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/Configuring-res_pjsip-to-work-through-NAT/)

Stand: 6. Oktober 2026. Der Build wird in CI geprüft. Eine echte Telekom-Registrierung und Gespräche müssen mit deinen lokalen Anschlussdaten getestet werden.

### Quellen für weitere Anbieter

- [sipgate SIP-Geräte](https://help.sipgate.de/cloud-telefonanlage/erste-schritte/alles-fur-den-start-mit-sipgate/wie-konfiguriere-ich-mein-voip-telefon-mit-sipgate)
- [easybell Asterisk/PJSIP](https://www.easybell.de/hilfe/telefon-konfiguration/ip-telefonanlagen-fuer-unsere-sip-trunks/antwort/asterisk-telefonanlagen/)
- [FRITZ!Box IP-Telefon](https://fritz.com/apps/knowledge-base/FRITZ-Box-7412/42_IP-Telefon-an-FRITZ-Box-anmelden-und-einrichten/)
- [Vodafone DSL-Zugangsdaten](https://www.vodafone.de/downloadarea/EGF_Kundenanleitung_DSL_Webanleitung_140126_DVW_26.pdf)

## Kontakte als Kiosks anzeigen

1. Im HA-Assistenten unter **Telefon** den Bereich **Kontakte und Kiosk-Karten** öffnen.
2. **Kontakt hinzufügen** wählen. Anzeigename und erreichbare Telefonnummer eintragen.
3. Für eine Raumkarte den Typ **Kiosk / Raumkarte** wählen; optional Raum und Favorit setzen.
4. Speichern. Auf der Telefonseite erscheinen die Karten unter **Kontakte**; **Kiosks** filtert nur Kiosk-Karten. Die Suche findet Namen, Räume und Nummern.
5. Eine Karte auswählen. Sie setzt die Zielnummer im Anrufpad. Erst **Anrufen** und die Rückruf-Bestätigung starten den Anruf.

Es werden keine nativen Kiosk-Satellite-Intercom-Peers angelegt. Online-Status oder Präsenz werden nicht vorgetäuscht. Kiosk-Karten verwenden die von dir zugeordnete Telefonnummer und den Rückruf auf das gewählte Audio-Ziel. Es werden keine zusätzlichen internen Kiosk-Nebenstellen angelegt. Normale Telefonkontakte aus älteren Versionen bleiben erhalten.
