# Setup on Home Assistant OS

The add-on provides an Asterisk telephone server and a web interface for providers, phone numbers, and devices. The Kiosk Satellite plugin registers with this server as a SIP device.

## Requirements and operating modes

Home Assistant OS on amd64 systems is supported. The native plugin requires Android 7/API 24 or later, microphone permission, and a Kiosk Satellite version with SDK 1 overlays.

| Mode | Controls | Audio connection |
| --- | --- | --- |
| Native dialer | Phone button and call view in the KS plugin | SIP/RTP between Android and Asterisk |
| Web phone with a SIP phone | Browser keypad and contacts | The registered SIP phone is called first |
| Web phone with KS intercom | Browser keypad and contacts | Intercom bridge to one configured kiosk |

The steps below configure the native dialer. The two web modes are described under [Web phone and intercom bridge](#web-phone-and-intercom-bridge).

The setup assistant currently uses German labels. Exact labels are included in parentheses where needed.

## 1. Install the add-on

1. Open **Settings → Apps/Add-ons → Store** in Home Assistant.
2. Select **Repositories** from the menu and add `https://github.com/Eibelucas/Kiosk-Satellite-SIP`.
3. Install and start **Kiosk Satellite SIP Gateway**. The image is built on the HAOS system.
4. Select **Open Web UI**. Home Assistant ingress provides access to the setup assistant.

The add-on configuration includes `gateway_port`, the port of the optional LAN web phone page; its default is **8088**. Provider accounts, the SIP port, and devices are managed in the setup assistant. Home Assistant assigns the ingress port.

## 2. Configure a provider and phone number

In the connection step (**Anschluss**), choose a provider profile and enter the phone number in international format, including `+` and the country code. Registration uses the credentials associated with the SIP account.

| Profile | Configuration |
| --- | --- |
| Telekom residential | MagentaZuhause profile with `tel.t-online.de`; access-based or password authentication |
| sipgate | Device SIP ID and password; registrar `sipgate.de` |
| easybell | SIP account credentials; registrar `voip.easybell.de`; default registration number format `0049…` |
| FRITZ!Box | An IP phone configured in the PBX with assigned phone numbers |
| Vodafone, 1&1, o2 | SIP servers and credentials specified by the provider |
| Other SIP provider / custom PBX | Manual registration with registrar, domain, and SIP account |

Profiles supply defaults for supported account types. Availability for a particular connection and any contract- or server-specific requirements must be checked against the provider's configuration.

Advanced SIP settings (**Weitere SIP-Einstellungen**) include client user, incoming destination ID, caller ID user, realm, proxy, transport, and STUN. Server fields take hostnames or IPv4 addresses; some also accept a port. Provider connections support UDP and TCP.

### Multiple external numbers

Use **Add number** (**Rufnummer hinzufügen**) to configure up to eight separate SIP accounts. Each number has its own provider configuration and incoming call rule:

- **Normal ringing** (**Normal am gewählten Audio-Ziel klingeln**): an incoming call.
- **Reject** (**Abweisen**): registration can stay enabled while incoming calls are rejected.
- **Announcements from allowed numbers** (**Durchsage von erlaubten Nummern**): a dedicated announcement number with access rules.

**Register this account** (**Dieses Konto registrieren**) enables provider registration. The default outgoing number (**Standardrufnummer für ausgehende Anrufe**) selects the account used by the native dialer. **No outgoing calls** (**Keine ausgehenden Anrufe**) disables its external route.

Accounts on the same registrar need unique incoming destination IDs. Local PBXs also assign incoming and outgoing numbers in their own configuration. The provider and connection determine how many simultaneous calls are available.

## 3. Configure the local network

| Field | Meaning |
| --- | --- |
| HAOS IPv4 address (**IPv4-Adresse des HAOS-Systems**) | Local address of the system running the add-on |
| Local network and mask (**Heimnetz mit Netzmaske**) | Actual IPv4 network in CIDR notation |
| SIP port (**SIP-Port**) | Local Asterisk signaling port; default 5070 |
| Public IPv4 address (**Öffentliche IPv4-Adresse**) | Optional external address for the applicable NAT configuration |

The HAOS address and devices must be within the configured local network. The prefix follows the network configuration; `/24` corresponds to `255.255.255.0`. A fixed DHCP assignment helps keep the device connection stable.

The plugin's SIP port must match the assistant. Asterisk uses UDP ports **30000–30100** for RTP audio. The native plugin's default local SIP port is **5090**.

## 4. Configure SIP devices

A SIP extension is a local device identity on the Asterisk server.

For the native dialer, open the phone step and set the audio target to **SIP phone / Softphone 100** (**Telefon → Audio-Ziel → SIP-Telefon / Softphone 100**).

Extension **100** is available for a single device. Set its password under **Neues Passwort für SIP-Telefon 100**. For additional kiosks, use **Mehrere native Kiosks / SIP-Geräte → Gerät hinzufügen** and assign a name, an extension from **101–199**, and a password. Device passwords require at least twelve characters.

Each extension belongs to one device. A new registration on the same extension replaces the previous registration. Separate extensions allow multiple kiosks to stay registered independently.

Ringing targets can be restricted under **Klingelnde SIP-Geräte für diese Rufnummer**. With no selection, enabled devices in the device list ring; a single-device configuration uses phone 100. Answering on one device stops ringing on the others.

### Credentials at a glance

| Credentials | Purpose | Configuration |
| --- | --- | --- |
| Provider SIP account | Register external phone numbers | Connection step in the HA assistant |
| Device extension and password | Register a kiosk or SIP phone with local Asterisk | Phone step and the corresponding device |
| Web username and password | Access the optional LAN web phone page | Phone step, LAN access section |
| Intercom key | Connect the alternative KS intercom bridge | KS intercom and the phone step |

## 5. Save and connect the plugin

1. In the final connection step (**Verbinden**), review the summary and default outgoing number.
2. Select **Save and start Asterisk** (**Speichern und Asterisk starten**). This interrupts active calls.
3. Install or update **Kiosk Satellite SIP** in the KS plugin manager and enable it.
4. Enter the HAOS address, SIP port, device extension, and its password in the plugin.

The status **Bereit · Nebenstelle …** confirms plugin registration. **Verbindung prüfen** in the HA assistant also shows Asterisk and provider account status.

When editing unchanged accounts or devices later, leaving password fields blank preserves their stored values. The setup interface does not return provider or device passwords. Changes to the LAN web address or gateway port also require an add-on restart.

## 6. Test audio and calls

1. Dial **600 in the native dialer**. This uses Asterisk's local echo context and plays captured speech back to the device.
2. Check mute and hangup.
3. The provider number must appear as registered (**registriert**) in the assistant.
4. Enter an external number approved for the test and select **Call** (**Anrufen**). The remote party is called directly.
5. Call the configured external number from another phone and answer at the kiosk.

Incoming calls require manual acceptance. Collapsing the panel keeps a call active; **Hang up** (**Auflegen**) ends it. Internal kiosk calls remain available through KS intercom.

Native SIP calls require the microphone to be free from Voice Satellite or other recording. Shared microphone coordination is not implemented; detected active voice and intercom sessions block a new call.

## Web phone and intercom bridge

The optional web phone page includes a keypad, contacts, favorites, and kiosk cards. It is available through Home Assistant ingress or, after enabling LAN access, at `http://<HAOS-IP>:<GATEWAY-PORT>/`. LAN access uses the configured web username and password.

For outgoing web calls, select a destination and provider account. After confirmation, Asterisk calls the configured local audio target first. Once that target answers, it dials the external number. The web status confirms that the callback was requested; call setup continues at the audio target.

The web page can use a registered SIP phone or the **Kiosk Satellite Intercom** bridge. To configure the bridge:

1. Enable intercom and microphone permission in KS. Select hands-free mode for speakerphone use.
2. Select **Kiosk Satellite Intercom** as the audio target in the HA assistant.
3. Enter the local kiosk address, identity port, and shared intercom key. The identity port is usually **2324**; the intercom listener is discovered from the device identity.
4. Set an available callback port on HAOS; the default is **8090**. The kiosk must be able to reach it.
5. Save, run **Check kiosk connection** (**Kiosk-Verbindung prüfen**), then **Start local kiosk echo test** (**Lokalen Kiosk-Echo-Test starten**). Accept the test call at the kiosk and check audio and hangup.

The bridge supports one configured kiosk and local HTTP/WebSocket connections. Encrypted KS intercom is not currently supported. SIP devices and the intercom bridge are separate audio targets.

**Echo testing in web mode:** The diagnostic button in the HA assistant explicitly uses the local echo context. The web keypad uses the provider context, so entering 600 there is not a local echo test.

### Contacts and kiosk cards

The contacts section (**Telefon → Kontakte und Kiosk-Karten**) manages names, phone numbers, rooms, and favorites. The **Kiosk / Raumkarte** type controls display on the web phone page. Selecting a card prepares the destination; the call action and confirmation request the call.

These entries belong to the web phone page. Native KS intercom manages its own devices. Contact synchronization into the native SIP dialer is not implemented.

## Dedicated announcement number

A number configured for **Announcements from allowed numbers** uses its own caller allowlist, optional PIN, and duration limit. Other numbers retain their own call rules.

1. Add a separate provider account or phone number.
2. Select **Durchsage von erlaubten Nummern**.
3. Enter allowed callers in international format, one per line.
4. Optionally set a six-digit PIN. It must be entered within 15 seconds after connection. Caller ID can be spoofed; the PIN adds an access check.
5. Set a duration limit from 10 to 600 seconds; the default is 180.
6. Test with both an allowed and a disallowed caller.

SIP announcements use phone 100 as the target. Automatic answer through SIP headers requires a suitably configured target device. Intercom announcements use KS's one-way announcement mode. The target microphone does not send audio back.

Busy targets are skipped, and additional simultaneous announcements are rejected. An announcement ends at hangup or the duration limit. These settings do not change number assignments in a router or provider account.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Add-on missing from the store | Check the repository URL and amd64 architecture, then reload the store. |
| Asterisk does not start | Check add-on logs, the local HAOS address, and occupied SIP/AMI ports. |
| Plugin reports SIP not registered | Compare the HAOS address, SIP port, enabled device extension, and its password. |
| Registration switches between devices | Use a separate extension for each device and check for duplicate plugin instances. |
| SIP 404 on an external call | Check the default outgoing number and route, then the destination and provider response. |
| Provider account does not register | Check the profile, registrar, credentials, DNS, and SIP service connectivity. |
| No audio in the local echo test | Check microphone permission, active recording, output routing, Wi-Fi isolation, and RTP traffic. |
| One-way audio | Check the local network, public address, and RTP NAT configuration. |
| High voice delay | Compare the local echo test with an external call; check output routing, network load, and packet loss. |
| Web phone page unavailable | Check LAN access, gateway port, and web credentials; restart after address changes. |
| Intercom kiosk unavailable | Check the kiosk address, identity port, intercom key, and callback port. |
| Saving ends a call | Saving restarts Asterisk; make configuration changes outside active calls. |

The web phone page is intended for the local network. AMI binds to loopback. Router NAT, SIP ALG, CGNAT, and DS-Lite can affect external audio; configuration depends on the connection and network.

## Data, updates, and backups

Configuration, contacts, and session keys are stored in the persistent add-on directory `/data`. SIP passwords are provided locally to Asterisk; the web password is stored as a hash. Add-on backups contain these records and require protected storage.

Update the plugin and add-on separately. Switching from web launcher 26.10.12 to the native dialer requires entering SIP details once in the plugin. Disable any separate **SIP Native Dialer Lab** plugin before enabling the regular plugin. See the [migration guide](../README.md#updates).

## Technical limitations and checks

The native dialer supports IPv4, UDP, and G.711. TLS/SRTP, in-call DTMF, hold, transfer, and native contact synchronization are not implemented. Shared microphone management with Voice Satellite remains open. A bounded audio queue does not guarantee a particular end-to-end latency.

Automated tests use simulated SIP devices, fictional credentials, and local Asterisk instances. They check protocol behavior, configuration, the audio bridge, and package format. Connection compatibility, Android acoustics, and actual call latency require measurements under deployment conditions.

## Further reading

- [Home Assistant: app repositories](https://developers.home-assistant.io/docs/apps/repository/)
- [Home Assistant: ingress](https://developers.home-assistant.io/docs/apps/presentation/)
- [Asterisk: outbound registrations](https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/Configuring-Outbound-Registrations/)
- [Asterisk: NAT configuration](https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/Configuring-res_pjsip-to-work-through-NAT/)
- [Telekom: SIP client configuration](https://www.telekom.de/hilfe/internet-telefonie/telefonie/voice-over-ip-sip-client)
- [sipgate: SIP devices](https://help.sipgate.de/cloud-telefonanlage/erste-schritte/alles-fur-den-start-mit-sipgate/wie-konfiguriere-ich-mein-voip-telefon-mit-sipgate)
- [easybell: Asterisk/PJSIP](https://www.easybell.de/hilfe/telefon-konfiguration/ip-telefonanlagen-fuer-unsere-sip-trunks/antwort/asterisk-telefonanlagen/)
- [FRITZ!Box: IP phone setup](https://fritz.com/apps/knowledge-base/FRITZ-Box-7412/42_IP-Telefon-an-FRITZ-Box-anmelden-und-einrichten/)
