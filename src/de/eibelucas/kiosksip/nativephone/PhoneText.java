// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

import java.util.*;

/** English is the default; the plugin's Language setting can select German. */
final class PhoneText {
    private static final Map<String,String> DE=new HashMap<>();
    static {
        DE.put("Enter an extension from 100 to 199.","Nebenstelle von 100 bis 199 eingeben.");
        DE.put("Check the PBX address, ports and device SIP password.","SIP-Adresse, Ports und Geräte-SIP-Passwort prüfen.");
        DE.put("Number: 3 to 20 digits, with optional +, * or #.","Nummer: 3 bis 20 Ziffern, optional +, * oder #.");
        DE.put("This device is not registered yet.","Das Gerät ist noch nicht angemeldet.");
        DE.put("Only IPv4 is supported.","Nur IPv4 wird unterstützt.");
        DE.put("Could not process the call.","Anruf konnte nicht verarbeitet werden.");
        DE.put("SIP connection failed. Check the address, port, password and microphone.","SIP-Verbindung fehlgeschlagen. IP, Port, Passwort und Mikrofon prüfen.");
        DE.put("Audio interrupted. Call ended.","Audio unterbrochen. Gespräch beendet.");
        DE.put("No answer / timeout.","Keine Antwort / Zeitüberschreitung.");
        DE.put("A call is already active.","Es läuft bereits ein Anruf.");
        DE.put("SIP not registered.","SIP nicht angemeldet.");
        DE.put("Connecting …","Verbindet …");
        DE.put("Could not prepare audio. Check microphone permission.","Audio konnte nicht vorbereitet werden. Mikrofonberechtigung prüfen.");
        DE.put("Ringing …","Klingelt beim Ziel …");
        DE.put("Call cancelled.","Anruf abgebrochen.");
        DE.put("Call ended: SIP ","Anruf beendet: SIP ");
        DE.put("Invalid SIP destination.","Ungültiges SIP-Ziel.");
        DE.put("SIP proxies with Record-Route are not supported.","SIP-Proxys mit Record-Route werden nicht unterstützt.");
        DE.put("Connected","Verbunden");
        DE.put("Audio unavailable. Check microphone permission and audio access.","Audio nicht verfügbar. Mikrofon und Audio-Zugriff prüfen.");
        DE.put("Incoming call","Eingehender Anruf");
        DE.put("Call ended.","Gespräch beendet.");
        DE.put("Audio unavailable.","Audio nicht verfügbar.");
        DE.put("Cancelling …","Wird abgebrochen …");
        DE.put("Call declined.","Anruf abgelehnt.");
        DE.put("Connection ended.","Verbindung beendet.");
        DE.put("Missing Digest challenge","Digest challenge fehlt");
        DE.put("Unsupported SIP authentication","Nicht unterstützte SIP-Anmeldung");
        DE.put("Unsupported qop","qop nicht unterstützt");
        DE.put("Phone","Telefon");
        DE.put("Close","Schließen");
        DE.put("Dial a number","Nummer wählen");
        DE.put("Destination number","Zielnummer");
        DE.put("Delete digit","Ziffer löschen");
        DE.put("0, hold for plus","0, gedrückt halten für Plus");
        DE.put("Call","Anrufen");
        DE.put("Answer","Annehmen");
        DE.put("Mute","Stumm");
        DE.put("Hang up","Auflegen");
        DE.put("Open phone","Telefon öffnen");
        DE.put("Unmute microphone","Mikrofon einschalten");
        DE.put("Decline","Ablehnen");
        DE.put("Cancel","Abbrechen");
        DE.put("Show call","Gespräch anzeigen");
        DE.put("Microphone muted","Mikrofon stumm");
        DE.put("Set up SIP: PBX address, extension and device password.","SIP einrichten: PBX-Adresse, Nebenstelle und Gerätepasswort.");
        DE.put("Native overlays unavailable. Update Kiosk Satellite.","Native Overlays fehlen. Kiosk Satellite aktualisieren.");
        DE.put("Ready · Extension ","Bereit · Nebenstelle ");
        DE.put("SIP not registered","SIP nicht angemeldet");
        DE.put("Audio is busy with Voice Satellite or intercom.","Audio ist durch Voice Satellite oder Intercom belegt.");
        DE.put("Preparing call audio …","Anruf-Audio wird vorbereitet …");
        DE.put("Wake word is being restored. Try again shortly.","Wake Word wird wiederhergestellt. Gleich erneut versuchen.");
        DE.put("Cannot read wake word state. Pause wake word in Kiosk Satellite before calling.","Wake-Word-Status nicht verfügbar. Wake Word vor dem Anruf in Kiosk Satellite pausieren.");
        DE.put("Cannot read wake word mute state. Pause wake word in Kiosk Satellite before calling.","Wake-Word-Stummschaltung nicht verfügbar. Wake Word vor dem Anruf in Kiosk Satellite pausieren.");
        DE.put("Wake word still owns the microphone. Pause wake word in Kiosk Satellite before calling.","Wake Word belegt weiterhin das Mikrofon. Wake Word vor dem Anruf in Kiosk Satellite pausieren.");
        DE.put("Cannot mute wake word. Pause wake word in Kiosk Satellite before calling.","Wake Word konnte nicht stummgeschaltet werden. Vor dem Anruf in Kiosk Satellite pausieren.");
        DE.put("Could not restore wake word. Check its mute switch in Kiosk Satellite.","Wake Word konnte nicht wiederhergestellt werden. Den Stummschalter in Kiosk Satellite prüfen.");
    }
    private final boolean german;
    PhoneText(String language){german="Deutsch".equals(language);}
    String get(String english){
        if(english==null)return "";
        if(!german)return english;
        String translated=DE.get(english);
        if(translated!=null)return translated;
        String prefix="Call ended: SIP ";
        if(english.startsWith(prefix))return DE.get(prefix)+english.substring(prefix.length());
        return english;
    }
}
