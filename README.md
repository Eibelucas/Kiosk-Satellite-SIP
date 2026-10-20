# SIP Phone for Kiosk Satellite

SIP Phone for Kiosk Satellite adds SIP calling to [Kiosk Satellite](https://github.com/jxlarrea/kiosk-satellite). A floating phone button opens a native Android dialer. Calls connect to a telephone provider through a central Asterisk server.

The project has two separately installed components:

| Component | Purpose |
| --- | --- |
| Kiosk Satellite plugin | Number entry, call controls, microphone, and speaker on Android |
| Home Assistant OS app | Asterisk server, provider connection, phone numbers, and devices |

Each kiosk can use its own SIP extension: a local device identity on the server. Each external phone number can ring selected devices. Answering on one device stops the others from ringing.

## Requirements

- Home Assistant OS (HAOS) on an amd64 system.
- Android 7/API 24 or later and a Kiosk Satellite version with SDK 1 overlays and secret plugin settings.
- A supported SIP account or a local PBX with SIP access.
- Network connectivity between Android and HAOS, and microphone permission for Kiosk Satellite.

Provider profiles are included for Telekom residential service, sipgate, easybell, and FRITZ!Box. Other registering SIP accounts can use manual profiles.

## Installation

### Install in Kiosk Satellite

Use the button below to open the plugin in Kiosk Satellite, review its details, and select **Trust and install**.

[![Install in Kiosk Satellite](https://kiosksatellite.com/img/badges/plugin-add.svg)](https://kiosksatellite.com/redirect/plugin/?repository=Eibelucas/Kiosk-Satellite-SIP)

### Manual installation

1. Open **Settings → Plugin Manager** in Kiosk Satellite and turn on **Enable Plugins**.
2. Select **Add plugin**, enter the repository URL below, and select **Preview**.
3. Review the plugin details and select **Trust and install**.

```text
https://github.com/Eibelucas/Kiosk-Satellite-SIP
```

## Gateway and SIP setup

Add the same repository URL to the Home Assistant app store and configure the gateway before making calls.

The plugin settings and default dialer language are English. Select **Language → Deutsch** for German call controls and status messages. The gateway administration workspace uses German labels, quoted below where needed.

1. In Home Assistant, open **Settings → Apps/Add-ons → Store → Repositories** and add the repository. Install and start **Kiosk Satellite SIP Gateway**.
2. Select **Open Web UI**. Configure the provider under **SIP-Zugänge**, the external number and its ring targets under **Rufnummern**, and the server address and SIP port under **Netzwerk**. Choose the outgoing default under **Ausgehend standardmäßig**.
3. Add devices under **Kiosks & Geräte**, using an individual extension from 101 to 199 and password for each device. Existing installations retain extension 100 and its stored password. Save the editors and select **Änderungen anwenden** to activate the configuration. Native SIP devices are the default audio target.
4. Enable the installed **SIP Phone for Kiosk Satellite** plugin in the Kiosk Satellite plugin manager.
5. Enter the connection details in the plugin:

| Plugin setting | Value |
| --- | --- |
| PBX address | Local IPv4 address of the Home Assistant OS system |
| PBX SIP port | SIP port configured under Network; default 5070 |
| Device extension | Configured device extension, such as 100 or 101 |
| Device SIP password | Password assigned to that extension |
| Local SIP port | Local signaling port on Android; default 5090 |
| Screen side | Phone button placement: right or left |
| Bottom offset (dp) | Distance from the bottom edge; default 88 dp, range 12–300 |
| Language | English (default) or Deutsch for call controls and runtime status |

The status **Ready · Extension …** confirms registration. Dial **600 in the native dialer** to run the local echo test. After a successful audio test, external phone numbers can be called.

[Detailed setup and troubleshooting](kiosk_sip/DOCS.md)

## Usage

Tap the phone button, enter a number, and select **Call**. The call view shows the destination, status, and duration. **Mute** mutes the microphone; **Hang up** ends the call. Collapsing the panel keeps the call active. Hold **0** to insert a plus sign at the start of a number.

Incoming calls have **Answer** and **Decline** controls. Internal calls between kiosks remain available through Kiosk Satellite intercom.

## Settings and data flow

The phone button has settings for screen side, bottom offset, and local SIP port. The plugin uses native overlays, host state and control APIs, and Android microphone/audio access. Host state checks detect active Voice Satellite turns and intercom sessions. Before a user places or answers a call, the plugin reads the wake word mute state, mutes wake word when needed, and waits for listening to stop. It restores the previous mute state after the call ends, is cancelled, or fails. Incoming ringing alone does not mute wake word.

The plugin sends SIP signaling and RTP call audio to the configured Asterisk server on the local network. The RTP destination in SDP must match the PBX IP address resolved for the SIP connection, and received RTP must match the negotiated PBX address and port. Asterisk must anchor call audio; a separate media host or direct media is not supported. Asterisk connects to the configured telephone provider for external calls. Provider credentials stay in the HAOS add-on; the plugin stores the password for its local device extension using a secret setting. The optional web phone page stores its configuration and contacts in the add-on.

The project does not add an analytics or telemetry service. External calls transmit call signaling and audio through the configured provider.

## Updates

Update the plugin and Home Assistant app separately. Add-on 26.10.17 introduces the administration workspace and migrates existing provider credentials, routing, device identities and ports automatically. Version 26.10.16 changes the display name to **SIP Phone for Kiosk Satellite** and adds the Language setting. The repository URL, plugin ID, SIP settings, and stored device password remain the same. Version 26.10.13 includes the native dialer and multi-device management. Add-on 26.10.12 remains compatible with one device on extension 100.

Updating plugin 26.10.12 to 26.10.13 replaces the web phone launcher with the native dialer. Enter the SIP connection details once in the plugin. The plugin ID remains `kiosk-satellite-sip`. Existing provider and add-on settings are preserved.

If the separate **SIP Native Dialer Lab** plugin is installed, disable it before enabling the regular plugin. The two IDs store separate settings and cannot use the same SIP extension at the same time.

## Scope and limitations

The native dialer uses IPv4, UDP, and G.711 on the local network. In-call DTMF, hold, transfer, TLS/SRTP, and contact synchronization into the native dialer are not implemented.

Active Voice Satellite turns and intercom sessions block or end SIP calls. Continuous wake word listening is handled by temporary muting rather than being treated as an active voice turn. This uses the host's wake word controls; it is not a shared microphone lease.

Automatic microphone release depends on the Kiosk Satellite version, wake word engine, and device. If muting fails or listening continues, **pause wake word in Kiosk Satellite before placing or answering a call**. The dialer reports this requirement and does not start call audio. Physical microphone release across Android devices has not been verified by the automated tests.

End a call before disabling or updating the plugin. Disabling the plugin or stopping Kiosk Satellite during a call can leave wake word muted; check its mute switch in Kiosk Satellite and re-enable it if needed. The host revokes plugin controls before shutdown, so restoration after session revocation is unavailable.

Bounded audio buffering limits backlog; actual voice delay depends on the device and network. A measured latency comparison is not yet available.

The web phone page with contacts and the KS intercom audio bridge remain available as alternative modes. Their setup and call flow are described in the [HAOS documentation](kiosk_sip/DOCS.md).

## Further information

- [Releases and package format](RELEASES.md)
- [Implementation and automated tests](native-lab/README.md)
- [Changelog](kiosk_sip/CHANGELOG.md)
- [Published releases](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases)

## License

Apache-2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Kiosk Satellite is a separate project and is not bundled.
