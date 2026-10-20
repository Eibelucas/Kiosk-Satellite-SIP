# SIP Phone Gateway

A Home Assistant OS app for SIP provider registration, external phone calls, multiple kiosk endpoints, and optional announcement routing.

## Administration

Open the web interface from Home Assistant. The administration workspace has separate pages for:

- **SIP accounts:** provider profiles, servers, authentication and transport.
- **Phone numbers:** external numbers, incoming call rules, ring targets and the outgoing default.
- **Kiosks & devices:** device names, individual SIP extensions and passwords, addresses and rooms.
- **Contacts:** the phone book for the optional web phone.
- **Network:** server address, local network, SIP port, telephone runtime and LAN web access.
- **Diagnostics:** provider and device registration, runtime state and configuration export.

Saving an editor stores a draft. **Apply changes** explicitly updates the running telephone server. Failed runtime activation restores the previous saved runtime configuration. Disabling the telephone server remains effective after an app restart.

## Existing installations

The first start of version 26.10.17 migrates existing gateway settings into the workspace. Provider passwords, the web login hash, device passwords, phone numbers, call rules and configured ports are preserved. Migration does not rewrite the active runtime configuration. Extension 100 remains available for existing clients and appears in the device list; additional devices use extensions 101–199.

Install the update on the existing app to retain its data. A separately installed UI Lab has its own data directory and does not automatically import gateway credentials.

## Installation and operation

Add the repository to the Home Assistant app store and install **Kiosk Satellite SIP Gateway**. Home Assistant OS on amd64 is supported. Open the app web interface to configure it.

For native kiosk calling, enable the SIP Phone plugin in Kiosk Satellite. Set its PBX address and SIP port to this gateway, and use the device extension and password from **Kiosks & devices**. Provider credentials remain on the gateway. Dial 600 from a registered native SIP kiosk for the local echo test.

The optional LAN web phone is available at /phone after LAN access and its separate web login are configured. The administration API is available only through authenticated Home Assistant ingress. Changing LAN access requires an app restart.

The gateway supports one external number per SIP login, up to eight accounts and up to 99 additional devices. Shared trunk registrations are not implemented. Ring targets belong to each number. Internal kiosk communication remains available through Kiosk Satellite.

Passwords, keys and PINs are omitted from configuration API responses and exports. Blank password fields retain an existing secret only while the associated identity remains unchanged. Keep a Home Assistant backup before upgrading.

## Web phone and intercom bridge

The optional web phone page includes a keypad, contacts, favorites, and kiosk cards. It is available through Home Assistant ingress or, after enabling LAN access, at `http://<HAOS-IP>:<GATEWAY-PORT>/phone`. LAN access uses the configured web username and password.

For outgoing web calls, select a destination and provider account. After confirmation, Asterisk calls the configured local audio target first. Once that target answers, it dials the external number. The web status confirms that the callback was requested; call setup continues at the audio target.

The web page can use a registered SIP phone or the **Kiosk Satellite Intercom** bridge. To configure the bridge:

1. Enable intercom and microphone permission in KS. Select hands-free mode for speakerphone use.
2. Open **Kiosks & devices → Additional audio targets** and select the alternative KS intercom bridge.
3. Enter the local kiosk address, identity port, and shared intercom key. The identity port is usually **2324**; the intercom listener is discovered from the device identity.
4. Set an available callback port on HAOS; the default is **8090**. The kiosk must be able to reach it.
5. Save the editor, select **Apply changes**, then open **Diagnostics** and use **Check bridge** (**Brücke prüfen**) and **Bridge echo** (**Brücken-Echo**). Accept the test call at the kiosk and check audio and hangup.

The bridge supports one configured kiosk and local HTTP/WebSocket connections. Encrypted KS intercom is not currently supported. SIP devices and the intercom bridge are separate audio targets.

**Echo testing in web mode:** The diagnostic button in the administration workspace explicitly uses the local echo context. The web keypad uses the provider context, so entering 600 there is not a local echo test.

### Contacts and kiosk cards

The **Contacts** page manages names, phone numbers, rooms, and favorites. The **Kiosk / Raumkarte** type controls display on the web phone page. Selecting a card prepares the destination; the call action and confirmation request the call.

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
| No audio in the local echo test | Check microphone permission, active voice/intercom sessions, output routing, Wi-Fi isolation, and RTP traffic. If automatic muting does not release capture, pause wake word in KS before calling. |
| One-way audio | Check the local network, public address, and RTP NAT configuration. |
| High voice delay | Compare the local echo test with an external call; check output routing, network load, and packet loss. |
| Web phone page unavailable | Check LAN access, gateway port, and web credentials; restart after address changes. |
| Intercom kiosk unavailable | Check the kiosk address, identity port, intercom key, and callback port. |
| Applying changes ends a call | Applying restarts Asterisk; apply configuration changes outside active calls. |

The web phone page is intended for the local network. AMI binds to loopback. Router NAT, SIP ALG, CGNAT, and DS-Lite can affect external audio; configuration depends on the connection and network.

## Data, updates, and backups

Configuration, contacts, and session keys are stored in the persistent add-on directory `/data`. SIP passwords are provided locally to Asterisk; the runtime web login uses a password hash. Saved drafts can contain changed secrets and use restricted file permissions. Add-on backups contain these records and require protected storage.

Update the plugin and add-on separately. Switching from web launcher 26.10.12 to the native dialer requires entering SIP details once in the plugin. Disable any separate **SIP Native Dialer Lab** plugin before enabling the regular plugin. See the [migration guide](../README.md#updates).

## Technical limitations and checks

The native dialer supports IPv4, UDP, and G.711. TLS/SRTP, in-call DTMF, hold, transfer, and native contact synchronization are not implemented. Wake word coordination uses temporary host muting rather than a shared microphone lease. The RTP destination must equal the configured PBX address resolved for the SIP connection; separate media hosts and direct media are not supported. A bounded audio queue does not guarantee a particular end-to-end latency.

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
