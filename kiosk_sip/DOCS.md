# Einrichtung auf Home Assistant OS

Das Add-on stellt einen Asterisk-Telefonserver und eine Weboberfläche für Anbieter, Rufnummern und Geräte bereit. Das Kiosk-Satellite-Plugin verbindet sich als SIP-Gerät mit diesem Server.

## Voraussetzungen und Betriebsarten

Unterstützt wird Home Assistant OS auf amd64-Systemen. Für das native Plugin sind Android 7/API 24 oder höher, Mikrofonberechtigung und eine Kiosk-Satellite-Version mit SDK-1-Overlays erforderlich.

| Betriebsart | Bedienung | Audio-Verbindung |
| --- | --- | --- |
| Nativer Dialer | Telefonknopf und Gesprächsansicht im KS-Plugin | SIP/RTP zwischen Android-Gerät und Asterisk |
| Web-Telefonseite mit SIP-Telefon | Browser mit Anrufpad und Kontakten | Angemeldetes SIP-Telefon wird zuerst angerufen |
| Web-Telefonseite mit KS-Intercom | Browser mit Anrufpad und Kontakten | Intercom-Brücke zu einem konfigurierten Kiosk |

Die folgenden Schritte richten den nativen Dialer ein. Die beiden Web-Betriebsarten sind unter [Web-Telefonseite und Intercom-Brücke](#web-telefonseite-und-intercom-brücke) beschrieben.

## 1. Add-on installieren

1. In Home Assistant **Einstellungen → Apps/Add-ons → Store** öffnen.
2. Im Drei-Punkte-Menü **Repositories** wählen und `https://github.com/Eibelucas/Kiosk-Satellite-SIP` hinzufügen.
3. **Kiosk Satellite SIP Gateway** installieren und starten. Das Image wird auf dem HAOS-System gebaut.
4. **Weboberfläche öffnen** wählen. Der Einrichtungsassistent ist über Home Assistant Ingress erreichbar.

Die Add-on-Konfiguration enthält den Port der optionalen LAN-Telefonseite: `gateway_port`, Standard **8088**. Anbieter, SIP-Port und Geräte werden im Einrichtungsassistenten verwaltet. Der Ingress-Port wird von Home Assistant zugewiesen.

## 2. Anbieter und Rufnummer einrichten

Unter **Anschluss** ein Anbieterprofil auswählen und die Rufnummer im internationalen Format mit `+` und Landesvorwahl eintragen. Für die Registrierung werden die zum SIP-Konto gehörenden Anmeldedaten verwendet.

| Profil | Konfiguration |
| --- | --- |
| Telekom Privatkunden | MagentaZuhause-Profil mit `tel.t-online.de`; Anschluss- oder Passwort-Anmeldung |
| sipgate | SIP-ID und Passwort des SIP-Geräts; Registrar `sipgate.de` |
| easybell | SIP-Kontodaten; Registrar `voip.easybell.de`; voreingestelltes Anmeldeformat `0049…` |
| FRITZ!Box | In der Telefonanlage eingerichtetes IP-Telefon mit zugewiesenen Rufnummern |
| Vodafone, 1&1, o2 | SIP-Server und Kontodaten gemäß Anbieter-Konfiguration |
| Anderer SIP-Anbieter / eigene PBX | Manuelle Registrierung mit Registrar, Domain und SIP-Konto |

Die Profile liefern Vorgaben für unterstützte Kontoarten. Die Verfügbarkeit eines konkreten Anschlusses und abweichende Vertrags- oder Servervorgaben müssen mit den Anbieterinformationen abgeglichen werden.

Unter **Weitere SIP-Einstellungen** stehen Anmelde-ID, eingehende Ziel-ID, Absender-ID, Realm, Proxy, Transport und STUN zur Verfügung. Serverfelder enthalten Hostnamen oder IPv4-Adressen; bei dafür vorgesehenen Feldern ist zusätzlich ein Port möglich. Anbieter-Verbindungen unterstützen UDP und TCP.

### Mehrere externe Rufnummern

Mit **Rufnummer hinzufügen** können bis zu acht separate SIP-Konten eingerichtet werden. Jede Rufnummer besitzt eine eigene Anbieter-Konfiguration und eine Regel für eingehende Anrufe:

- **Normal am gewählten Audio-Ziel klingeln**: eingehendes Gespräch.
- **Abweisen**: Registrierung bleibt möglich, eingehende Anrufe werden abgewiesen.
- **Durchsage von erlaubten Nummern**: separate Durchsage-Rufnummer mit Zugangsregeln.

**Dieses Konto registrieren** aktiviert die Anmeldung beim Anbieter. Unter **Standardrufnummer für ausgehende Anrufe** wird das für den nativen Dialer verwendete Konto ausgewählt. Die Auswahl **Keine ausgehenden Anrufe** deaktiviert dessen externe Route.

Konten auf demselben Registrar benötigen eindeutige eingehende Ziel-IDs. Bei lokalen Telefonanlagen werden eingehende und ausgehende Rufnummern zusätzlich in der Telefonanlage zugewiesen. Die Anzahl gleichzeitig verfügbarer Gespräche richtet sich nach Anschluss und Anbieter.

## 3. Heimnetz konfigurieren

| Feld | Bedeutung |
| --- | --- |
| IPv4-Adresse des HAOS-Systems | Lokale Adresse des Systems, auf dem das Add-on läuft |
| Heimnetz mit Netzmaske | Tatsächliches IPv4-Netz in CIDR-Schreibweise |
| SIP-Port | Lokaler Asterisk-Signalisierungsport; Standard 5070 |
| Öffentliche IPv4-Adresse | Optionale externe Adresse für eine entsprechende NAT-Konfiguration |

Die HAOS-Adresse und die Geräte müssen innerhalb des konfigurierten lokalen Netzes liegen. Die Netzmaske ergibt sich aus der Netzwerkkonfiguration; `/24` entspricht `255.255.255.0`. Eine feste DHCP-Zuordnung erleichtert die dauerhafte Geräteverbindung.

Der im Plugin eingetragene SIP-Port muss dem Wert im Assistenten entsprechen. Asterisk verwendet UDP **30000–30100** für RTP-Audio. Das native Plugin verwendet standardmäßig **5090** als lokalen SIP-Port.

## 4. SIP-Geräte einrichten

Eine SIP-Nebenstelle ist die lokale Kennung eines Telefongeräts am Asterisk-Server.

Unter **Telefon → Audio-Ziel** für den nativen Dialer **SIP-Telefon / Softphone 100** auswählen.

Für eine Einzelanmeldung steht Nebenstelle **100** zur Verfügung. Das zugehörige Passwort wird unter **Neues Passwort für SIP-Telefon 100** gesetzt. Für zusätzliche Kiosks unter **Mehrere native Kiosks / SIP-Geräte → Gerät hinzufügen** jeweils Name, Nebenstelle **101–199** und Passwort festlegen. Gerätepasswörter benötigen mindestens zwölf Zeichen.

Jede Nebenstelle ist einem Gerät zugeordnet. Eine neue Registrierung derselben Nebenstelle ersetzt die bisherige Registrierung. Unterschiedliche Nebenstellen ermöglichen den parallelen Betrieb mehrerer Kiosks.

Unter **Klingelnde SIP-Geräte für diese Rufnummer** können die Ziele eines eingehenden Anrufs eingeschränkt werden. Ohne Auswahl klingeln die aktivierten Geräte der Geräteliste; bei einer Einzelkonfiguration wird Telefon 100 verwendet. Sobald ein Gerät annimmt, endet das Klingeln auf den übrigen Zielen.

### Zugangsdaten im Überblick

| Zugang | Zweck | Einrichtung |
| --- | --- | --- |
| Anbieter-SIP-Konto | Registrierung externer Rufnummern | Schritt Anschluss im HA-Assistenten |
| Geräte-Nebenstelle und Passwort | Anmeldung eines Kiosks oder SIP-Telefons am lokalen Asterisk | Schritt Telefon und jeweiliges Gerät |
| Web-Benutzer und Passwort | Zugriff auf die optionale LAN-Telefonseite | Schritt Telefon, Bereich LAN-Zugriff |
| Intercom-Schlüssel | Verbindung der alternativen KS-Intercom-Brücke | KS-Intercom und Schritt Telefon |

## 5. Speichern und Plugin verbinden

1. Unter **Verbinden** die Zusammenfassung und Standardrufnummer prüfen.
2. **Speichern und Asterisk starten** wählen. Dabei werden laufende Gespräche unterbrochen.
3. Im Kiosk-Satellite-Plugin-Manager **Kiosk Satellite SIP** installieren oder aktualisieren und aktivieren.
4. Im Plugin die HAOS-IP, den SIP-Port, die Geräte-Nebenstelle und das zugehörige Passwort eintragen.

Die Anzeige **Bereit · Nebenstelle …** bestätigt die Registrierung des Plugins. Im HA-Assistenten zeigt **Verbindung prüfen** zusätzlich den Zustand von Asterisk und den Anbieter-Konten.

Bei späteren Änderungen behalten leere Passwortfelder die gespeicherten Werte für unveränderte Konten und Geräte bei. Anbieter- und Gerätepasswörter werden von der Einrichtungsoberfläche nicht zurückgegeben. Änderungen der LAN-Webadresse oder des Gateway-Ports erfordern zusätzlich einen Add-on-Neustart.

## 6. Audio und Anrufe prüfen

1. Nebenstelle **600 im nativen Dialer** wählen. Dieser Anruf verwendet den lokalen Echo-Kontext von Asterisk. Gesprochener Ton wird an das Gerät zurückgegeben.
2. Stummschaltung und Auflegen prüfen.
3. Die Anbieter-Rufnummer muss im Assistenten als **registriert** erscheinen.
4. Eine für den Test freigegebene externe Zielnummer im nativen Dialer wählen und **Anrufen** drücken. Die Gegenstelle wird direkt angerufen.
5. Für die Gegenprobe die eingerichtete externe Rufnummer anrufen und den Anruf am Kiosk annehmen.

Eingehende Anrufe werden im nativen Dialer manuell angenommen. Einklappen lässt ein Gespräch bestehen; **Auflegen** beendet es. Interne Kiosk-Gespräche stehen über die vorhandene KS-Gegensprechanlage zur Verfügung.

Für native SIP-Gespräche darf das Mikrofon nicht gleichzeitig von Voice Satellite oder einer anderen Aufnahme belegt sein. Die gemeinsame Mikrofonkoordination ist noch nicht umgesetzt; erkannte aktive Sprach- und Intercom-Sitzungen blockieren einen neuen Anruf.

## Web-Telefonseite und Intercom-Brücke

Die optionale Web-Telefonseite bietet Anrufpad, Kontakte, Favoriten und Kiosk-Karten. Sie kann über Home Assistant Ingress oder nach Aktivierung des LAN-Zugriffs über `http://<HAOS-IP>:<GATEWAY-PORT>/` geöffnet werden. Der LAN-Zugang verwendet den konfigurierten Web-Benutzernamen und das Web-Passwort.

Bei einem ausgehenden Web-Anruf werden Zielnummer und Anbieter-Konto ausgewählt. Nach Bestätigung wird zunächst das konfigurierte lokale Audio-Ziel angerufen. Erst nach dessen Annahme wählt Asterisk die externe Zielnummer. Die Web-Anzeige bestätigt die angeforderte Vermittlung; der Gesprächsaufbau erfolgt anschließend am Audio-Ziel.

Die Web-Seite kann ein angemeldetes SIP-Telefon oder die **Kiosk Satellite Intercom**-Brücke als Audio-Ziel verwenden. Für die Intercom-Brücke sind folgende Schritte erforderlich:

1. Intercom und Mikrofonberechtigung in Kiosk Satellite aktivieren. Für Freisprechen den entsprechenden Gesprächsmodus wählen.
2. Im HA-Assistenten **Audio-Ziel → Kiosk Satellite Intercom** auswählen.
3. Lokale Kiosk-IP, Identitätsport und gemeinsamen Intercom-Schlüssel eintragen. Der Identitätsport ist üblicherweise **2324**; der Intercom-Listener wird über die Geräteidentität ermittelt.
4. Einen freien Kiosk-Rückrufport auf HAOS festlegen; Standard **8090**. Der Kiosk muss diesen Port erreichen können.
5. Speichern, **Kiosk-Verbindung prüfen** und anschließend **Lokalen Kiosk-Echo-Test starten** verwenden. Den Testanruf am Kiosk annehmen und Audio sowie Auflegen prüfen.

Die Brücke unterstützt ein konfiguriertes Kiosk-Gerät und lokale HTTP-/WebSocket-Verbindungen. Verschlüsseltes KS-Intercom wird derzeit nicht unterstützt. Der SIP-Gerätemodus und die Intercom-Brücke sind unterschiedliche Audio-Ziele.

**Echo-Test der Web-Betriebsart:** Der Diagnoseknopf im HA-Assistenten verwendet ausdrücklich den lokalen Echo-Kontext. Das Web-Anrufpad verwendet den Anbieter-Kontext; die dort eingegebene Nummer 600 ist deshalb kein lokaler Echo-Test.

### Kontakte und Kiosk-Karten

Unter **Telefon → Kontakte und Kiosk-Karten** lassen sich Namen, Telefonnummern, Räume und Favoriten verwalten. Der Typ **Kiosk / Raumkarte** legt die Darstellung auf der Web-Telefonseite fest. Eine Auswahl trägt die Zielnummer ein; erst **Anrufen** und die Bestätigung fordern den Anruf an.

Diese Einträge gehören zur Web-Telefonseite. Die native KS-Gegensprechanlage verwaltet ihre Geräte selbst. Eine Übernahme der Kontakte in den nativen SIP-Dialer ist noch nicht umgesetzt.

## Separate Rufnummer für Durchsagen

Eine Rufnummer mit der Regel **Durchsage von erlaubten Nummern** verwendet eine eigene Absenderliste, optionale PIN und ein Dauerlimit. Andere Rufnummern behalten ihre jeweiligen Anrufregeln.

1. Ein separates Anbieter-Konto beziehungsweise eine separate Rufnummer hinzufügen.
2. Die Regel **Durchsage von erlaubten Nummern** wählen.
3. Erlaubte Absender im internationalen Format eintragen, eine Nummer pro Zeile.
4. Optional eine sechsstellige PIN setzen. Nach Verbindungsaufbau muss diese innerhalb von 15 Sekunden eingegeben werden. Eine reine Absendernummer kann gefälscht werden; die PIN ergänzt die Zugangsprüfung.
5. Das Dauerlimit festlegen: 10 bis 600 Sekunden, Standard 180.
6. Mit einem erlaubten sowie einem nicht erlaubten Absender testen.

Bei SIP-Audio wird Telefon 100 als Durchsageziel verwendet. Automatische Annahme über SIP-Header setzt ein entsprechend konfiguriertes Zielgerät voraus. Bei Intercom-Audio wird der einseitige Durchsage-Modus von Kiosk Satellite verwendet. Das Zielmikrofon überträgt dabei keinen Ton zurück.

Besetzte Ziele werden übersprungen. Weitere gleichzeitige Durchsagen werden abgewiesen. Die Durchsage endet beim Auflegen oder nach Ablauf des Dauerlimits. Die Nummernzuordnung im Router oder beim Anbieter wird durch diese Einstellungen nicht geändert.

## Fehlerbehebung

| Symptom | Prüfung |
| --- | --- |
| Add-on fehlt im Store | Repository-URL und amd64-Architektur prüfen; Store neu laden. |
| Asterisk startet nicht | Add-on-Protokoll, lokale HAOS-Adresse und belegte SIP-/AMI-Ports prüfen. |
| Plugin meldet SIP nicht angemeldet | HAOS-Adresse, SIP-Port, aktivierte Geräte-Nebenstelle und zugehöriges Passwort vergleichen. |
| Registrierung wechselt zwischen Geräten | Für jedes Gerät eine andere Nebenstelle verwenden; doppelte Plugin-Instanzen prüfen. |
| SIP 404 bei externem Anruf | Standardrufnummer und ausgehende Route prüfen; anschließend Zielnummer und Anbieterantwort prüfen. |
| Anbieter-Konto registriert sich nicht | Profil, Registrar, Kontodaten, DNS und Erreichbarkeit des SIP-Diensts prüfen. |
| Lokaler Echo-Test ohne Ton | Mikrofonberechtigung, aktive Sprachaufnahme, Audioausgabe, WLAN-Isolation und RTP-Verkehr prüfen. |
| Ton nur in einer Richtung | Lokales Netz, öffentliche Adresse und NAT-Konfiguration des RTP-Pfads prüfen. |
| Hohe Sprachverzögerung | Lokalen Echo-Test mit externem Gespräch vergleichen; Audioausgabe, Netzwerkauslastung und Paketverluste prüfen. |
| Web-Telefonseite nicht erreichbar | LAN-Zugriff, Gateway-Port und Web-Zugang prüfen; nach Adressänderungen Add-on neu starten. |
| Intercom-Kiosk nicht erreichbar | Kiosk-IP, Identitätsport, Intercom-Schlüssel und Rückrufport prüfen. |
| Speichern beendet ein Gespräch | Die Konfiguration startet Asterisk neu; Änderungen außerhalb laufender Gespräche durchführen. |

Die Web-Telefonseite ist für das lokale Netzwerk vorgesehen. AMI bindet an Loopback. Router-NAT, SIP-ALG, CGNAT oder DS-Lite können den externen Audio-Pfad beeinflussen; die erforderliche Konfiguration richtet sich nach Anschluss und Netzwerk.

## Daten, Updates und Backups

Konfiguration, Kontakte und Sitzungsschlüssel liegen im persistenten Add-on-Verzeichnis `/data`. SIP-Passwörter werden Asterisk lokal bereitgestellt; das Web-Passwort wird als Hash gespeichert. Add-on-Backups enthalten diese Daten und erfordern entsprechend geschützte Aufbewahrung.

Plugin und Add-on werden separat aktualisiert. Beim Wechsel vom Web-Telefonstarter 26.10.12 auf den nativen Dialer müssen die SIP-Verbindungsdaten einmal im Plugin gesetzt werden. Bei einem zusätzlich installierten **SIP Native Dialer Lab** ist dieses vor Aktivierung des regulären Plugins zu deaktivieren. Die [Hauptanleitung](../README.md#updates) beschreibt die Migration.

## Technische Grenzen und Prüfungen

Der native Dialer unterstützt IPv4, UDP und G.711. TLS/SRTP, DTMF während des Gesprächs, Halten, Vermitteln und native Kontaktsynchronisation sind noch nicht umgesetzt. Die gemeinsame Mikrofonverwaltung mit Voice Satellite ist offen. Die begrenzte Audiowarteschlange garantiert keine bestimmte Ende-zu-Ende-Latenz.

Automatisierte Tests verwenden simulierte SIP-Geräte, fiktive Zugangsdaten und lokale Asterisk-Instanzen. Sie prüfen Protokoll, Konfiguration, Audio-Brücke und Paketformat. Anschlusskompatibilität, Android-Akustik und reale Gesprächslatenz erfordern zusätzliche Messungen unter den jeweiligen Betriebsbedingungen.

## Weiterführende Dokumentation

- [Home Assistant: App-Repositories](https://developers.home-assistant.io/docs/apps/repository/)
- [Home Assistant: Ingress](https://developers.home-assistant.io/docs/apps/presentation/)
- [Asterisk: Outbound Registrations](https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/Configuring-Outbound-Registrations/)
- [Asterisk: NAT-Konfiguration](https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/Configuring-res_pjsip-to-work-through-NAT/)
- [Telekom: SIP-Client-Konfiguration](https://www.telekom.de/hilfe/internet-telefonie/telefonie/voice-over-ip-sip-client)
- [sipgate: SIP-Geräte](https://help.sipgate.de/cloud-telefonanlage/erste-schritte/alles-fur-den-start-mit-sipgate/wie-konfiguriere-ich-mein-voip-telefon-mit-sipgate)
- [easybell: Asterisk/PJSIP](https://www.easybell.de/hilfe/telefon-konfiguration/ip-telefonanlagen-fuer-unsere-sip-trunks/antwort/asterisk-telefonanlagen/)
- [FRITZ!Box: IP-Telefon einrichten](https://fritz.com/apps/knowledge-base/FRITZ-Box-7412/42_IP-Telefon-an-FRITZ-Box-anmelden-und-einrichten/)
