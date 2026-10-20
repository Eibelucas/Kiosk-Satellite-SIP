# Implementierung des nativen SIP-Dialers

Der native Dialer ist ab Version 26.10.13 Bestandteil des regulären Plugins `kiosk-satellite-sip`. Diese Seite beschreibt Architektur und Testumfang. Die [Hauptanleitung](../README.md) behandelt Installation und Bedienung.

## Aufbau

```text
Android-Kiosk mit SIP-Plugin
  → lokale SIP-Nebenstelle am Asterisk
  → eingerichtetes Anbieter-Konto
  → externe Telefonnummer
```

Ein langlebiges Android-Overlay zeigt den Telefonknopf und den ausklappbaren Dialer. Darstellung und Farben stammen aus dem Kiosk-Satellite-SDK. Ausgehende Anrufe verwenden direkt SIP INVITE; die Mikrofonaufnahme startet nach Annahme durch die Gegenstelle. Eingehende Anrufe erfordern eine lokale Annahme.

Der Zustand eines Gesprächs ist unabhängig davon, ob das Overlay ausgeklappt ist. SIP-Abbruch, Gegenstellen-Auflegen, Plugin-Stopp und Medienfehler schließen die zugehörigen Ressourcen.

## SIP-Geräte und Rufnummern

Asterisk verwaltet für jedes aktivierte SIP-Gerät eine eigene Authentifizierung und Registrierung. Nebenstelle 100 ist für eine Einzelanmeldung vorgesehen; 101–199 stehen für zusätzliche Geräte zur Verfügung. Eine neue Registrierung derselben Nebenstelle ersetzt die bisherige.

Externe Rufnummern können einzelne Geräte oder eine Gruppe als Klingelziel verwenden. Nimmt ein Gerät an, sendet Asterisk CANCEL an die übrigen Ziele. Interne Geräteanrufe sind nicht Teil des SIP-Dialers; dafür steht KS-Intercom zur Verfügung.

## Audio

Das Plugin überträgt G.711-Audio mit RTP zwischen Android und Asterisk. Aufnahme und Wiedergabe verwenden Android-Audio-APIs im Kommunikationsmodus. RTP-Empfang und Lautsprecher laufen in getrennten Threads.

Die PCM-Warteschlange enthält höchstens 480 Samples beziehungsweise 60 ms bei 8 kHz. Bei Rückstau werden alte Frames verworfen. Doppelte oder verspätete RTP-Sequenzen werden nicht erneut wiedergegeben. Für den Android-Wiedergabepuffer werden 320 Frames beziehungsweise 40 ms angefordert; Android kann einen größeren Mindestpuffer vorgeben.

Diese Werte beschreiben die lokale Pufferung, nicht die gesamte Gesprächslatenz. Ein gemessener Vergleich auf Android-Geräten liegt nicht vor. Ein adaptiver Jitterpuffer und eine gemeinsame Audio-Lease mit KS/Voice Satellite sind noch nicht umgesetzt.

## Automatisierte Prüfungen

`python tools/test_native.py` kompiliert SDK und Plugin gegen die Android-Schnittstellen. SIP-Tests verwenden einen lokalen simulierten Telefonserver und eine simulierte Medienquelle. Sie prüfen:

- Digest-Registrierung und authentifizierte SIP-Anfragen.
- Ausgehende und eingehende Gespräche, Abbruch, Annahme-Kollisionen und Auflegen.
- UDP-Wiederholungen und Abweisung von Antworten aus fremden Quellen.
- Getrennte Geräteidentitäten und Gesprächszustände.
- G.711-Konvertierung, SDP und Ressourcenfreigabe bei Medienfehlern.
- Begrenzte Audiowarteschlange bei Wiedergabestau, variable Paketgrößen, Duplikate und Sequenzüberlauf.

Die Add-on-CI prüft zusätzlich Konfiguration und API sowie reale Asterisk-Instanzen mit mehreren lokalen Testgeräten, Klingelgruppen und Audio-Brücke. Dabei werden fiktive Zugangsdaten verwendet. Diese Prüfungen messen weder die Android-Audioqualität noch die Ende-zu-Ende-Latenz eines Anbieteranschlusses.

`tools/build.py` erstellt das Android-DEX-Paket. `tools/verify_package.py` kontrolliert Plugin-ID, Manifest, ZIP-Inhalt und SHA-256-Prüfsumme. Die Build-Umgebung benötigt JDK 21 und ein Android-SDK; `JAVA_HOME` und `ANDROID_HOME` verweisen auf diese Installationen.

## Herkunft und Lizenz

Die Entwicklung erfolgte zunächst unter der separaten Plugin-ID `kiosk-satellite-sip-native-lab`. Diese ID wird für frühere Testinstallationen verwendet; die aktuelle reguläre ID lautet `kiosk-satellite-sip`.

- [Kiosk Satellite Community SDK](https://github.com/jxlarrea/kiosk-satellite-plugins): SDK, Theme und Overlay-Vertrag.
- [Navbar](https://github.com/dimatx/kiosk-satellite-navbar): Referenz für native Overlay-Bedienelemente.
- [SIP Phone](https://github.com/meiser79/kiosk-satellite-sip-phone): Grundlage für SIP-Nachrichten, Digest und G.711-Konvertierung.

Lizenz- und Herkunftsangaben stehen in [NOTICE](../NOTICE) und [LICENSE](../LICENSE).
