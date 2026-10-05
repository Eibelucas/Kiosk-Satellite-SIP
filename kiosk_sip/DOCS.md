# Einrichtung auf HAOS

Für HAOS direkt auf einem UGREEN DXP2800 (amd64). Kein UGOS, keine zusätzliche VM und kein separates Asterisk-Add-on erforderlich: Dieses Add-on enthält Asterisk und den SIP-Gateway.

## 1. Add-on installieren

1. Home Assistant → Einstellungen → Apps/Add-ons → Store öffnen.
2. Im Drei-Punkte-Menü **Repositories** wählen.
3. `https://github.com/Eibelucas/Kiosk-Satellite-SIP` hinzufügen.
4. **Kiosk Satellite SIP Gateway** öffnen und installieren. Das Image wird lokal gebaut; beim ersten Mal dauert das länger als ein Download.
5. Starten, **Beim Booten starten** aktivieren und **Weboberfläche öffnen** wählen.

Unter **Konfiguration** ist nur der Port der Kiosk-Telefonseite einstellbar (Standard `8088`). Die Anbieter-Einrichtung erfolgt in der Weboberfläche. Nach Änderung des Ports das Add-on neu starten.

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
| Festnetznummer | Deine vollständige Nummer, international: aus `02161…` wird `+492161…` |
| Telekom-Anmeldung | Zunächst Anschluss-Authentifizierung ohne Passwort, falls für deinen Zugang verfügbar; andernfalls Passwort-Anmeldung |
| Authentifizierungsname | Bei Passwort-Anmeldung: der gültige Telekom-Authentifizierungsname, in Kleinschreibung |
| Telekom-Passwort | Das zu diesem Zugang gehörende Telefonie-Passwort gemäß Telekom-Hilfe; nicht ungeprüft das separate E-Mail-Programm-Passwort |
| NAS-IP | Die lokale IPv4-Adresse deines DXP2800, z. B. `192.168.2.20`; im Router dauerhaft zuordnen |
| Heimnetz | Dein tatsächliches Netz, z. B. `192.168.2.0/24` bei Netzmaske `255.255.255.0` |
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
| Hauptrufnummer | Normal auf Telefon 100 klingeln | `+4921611234567` (Beispieldaten ersetzen) |
| Separate zweite Nummer | Durchsage von erlaubten Nummern | `+4921611234568` (Beispieldaten ersetzen) |
| Erlaubter Absender für die zweite Nummer | Eigene vollständige Anrufernummer | `+491701234567` (Beispieldaten ersetzen) |
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

Die Durchsage nutzt Asterisk Page mit stummem Zielmikrofon. Sie kann derzeit **SIP-Telefon bzw. SIP-Lautsprecher 100** erreichen. Das Kiosk-Plugin hat noch keine direkte Audio-Bridge zu Kiosk Satellite Intercom: Allein die Plugin-Installation lässt den Android-Kiosk deshalb noch keine SIP-Durchsage abspielen. Verwende vorerst ein passendes SIP-Gerät/Softphone. Ohne aktiviertes/unterstütztes Header-Auto-Answer klingelt dieses Ziel und muss angenommen werden.

Besetzte Ziele werden übersprungen; Anrufe werden nicht erzwungen unterbrochen. Jeweils eine Durchsage läuft; weitere werden abgewiesen. Der Raum endet beim Auflegen des Absenders oder beim Dauerlimit. Es gibt keine Aufzeichnung und keine externe Weiterleitung an die erlaubten Absendernummern.

Die Einstellungen hier ändern nicht die Nummernzuordnung im Router oder beim Anbieter. Bestehende Haustelefone dort behalten ihre bisherigen Zuordnungen; bei Bedarf die zweite Nummer dort von normalem Klingeln ausnehmen. Bei der FRITZ!Box pro Rolle ein eigenes IP-Telefonkonto und nur die zugehörige Nummer zuweisen.

## 3. SIP-Telefon anmelden und Audio testen

Das installierte Kiosk-Plugin ist derzeit ein Launcher für die Telefonseite. **Es nimmt SIP-/RTP-Audio noch nicht über Kiosk Satellite Intercom entgegen.** Verwende für den ersten Test ein SIP-Telefon oder eine SIP-Softphone-App im selben Heimnetz.

| Telefon-Einstellung | Wert |
| --- | --- |
| Server/Domain/Registrar | NAS-IP, z. B. `192.168.2.20` |
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
3. Dein SIP-Telefon **100 klingelt zuerst**.
4. Auf Telefon 100 annehmen. Erst danach wählt Asterisk die externe Zielnummer über Telekom.
5. Zum Beenden auf dem SIP-Telefon auflegen.

Die Weboberfläche meldet die Annahme einer Rückruf-Anfrage, nicht das erfolgreiche Zustandekommen des externen Gesprächs. Es gibt derzeit weder Kiosk-Audio, DTMF-Tasten während eines Gesprächs noch einen Auflegen-Button im Gateway.

Eingehende Telekom-Anrufe werden auf SIP-Telefon 100 weitergeleitet. Voraussetzung: Telekom-Registrierung, korrekte Zuordnung des eingehenden SIP-Servers und funktionierende Netzwerk-/Audio-Verbindung. Sie klingeln noch nicht über die Intercom-Funktion im Kiosk. Es werden keine automatischen Testanrufe ausgelöst.

## Fehler beheben

| Symptom | Nächster Schritt |
| --- | --- |
| Asterisk startet nicht | Add-on-Protokoll lesen. NAS-IP muss auf HAOS tatsächlich vorhanden und SIP-Port frei sein. |
| Telekom: abgelehnt | Rufnummer/Anschlusstyp prüfen, ggf. zur Passwort-Anmeldung wechseln. Authentifizierungsname und Rufnummer sind unterschiedliche Felder. |
| Telekom: wartet | DNS, Internetzugang und SIP-Verkehr am Router prüfen. Beim Verbindungsaufbau kurz warten, dann Status aktualisieren. |
| Telefon 100 fehlt | NAS-IP, Port, UDP, Benutzer `100` und dessen eigenes Passwort prüfen. Beide Geräte müssen im angegebenen Heimnetz liegen. |
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

Es werden keine nativen Kiosk-Satellite-Intercom-Peers angelegt. Online-Status oder Präsenz werden nicht vorgetäuscht. Kiosk-Karten verwenden die von dir zugeordnete Telefonnummer und den normalen SIP-Rückruf auf Telefon 100. Noch keine internen Kiosk-Nebenstellen oder direkte Android-Audio-Bridge. Normale Telefonkontakte aus älteren Versionen bleiben erhalten.
