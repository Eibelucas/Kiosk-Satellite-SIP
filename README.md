# Kiosk Satellite SIP

Kiosk Satellite SIP adds SIP calling to [Kiosk Satellite](https://github.com/jxlarrea/kiosk-satellite). A floating phone button opens a native Android dialer. Calls connect to a telephone provider through a central Asterisk server.

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

## Installation and setup

Use the same repository URL for the Home Assistant app store and the Kiosk Satellite plugin manager:

```text
https://github.com/Eibelucas/Kiosk-Satellite-SIP
```

The plugin and setup assistant currently use German labels. Their exact wording appears in parentheses where needed.

1. In Home Assistant, open **Settings → Apps/Add-ons → Store → Repositories** and add the repository. Install and start **Kiosk Satellite SIP Gateway**.
2. Select **Open Web UI** and configure the provider, phone number, and local network. Select a default outgoing number (**Standardrufnummer für ausgehende Anrufe**).
3. Set the audio target to **SIP phone / Softphone 100** (**SIP-Telefon / Softphone 100**). For one device, configure extension 100 and its password. For multiple devices, add separate extensions from 101 to 199, each with its own password, under **Mehrere native Kiosks / SIP-Geräte**.
4. Install and enable **Kiosk Satellite SIP** in the Kiosk Satellite plugin manager.
5. Enter the connection details in the plugin:

| Plugin setting | Value |
| --- | --- |
| Server (**HAOS-IP / Asterisk**) | Local IPv4 address of the Home Assistant OS system |
| SIP port (**Asterisk SIP-Port**) | SIP port configured in the assistant; default 5070 |
| Extension (**Eigene Nebenstelle**) | Configured device extension, such as 100 or 101 |
| Device password (**SIP-Passwort dieses Geräts**) | Password assigned to that extension |
| Local SIP port (**Lokaler SIP-Port**) | Local signaling port on Android; default 5090 |
| Screen side (**Bildschirmseite**) | Phone button placement: right or left |
| Bottom offset (**Abstand vom unteren Rand (dp)**) | Distance from the bottom edge; default 88 dp, range 12–300 |

The status **Bereit · Nebenstelle …** confirms registration. Dial **600 in the native dialer** to run the local echo test. After a successful audio test, external phone numbers can be called.

[Detailed setup and troubleshooting](kiosk_sip/DOCS.md)

## Usage

Tap the phone button, enter a number, and select **Call** (**Anrufen**). The call view shows the destination, status, and duration. **Mute** (**Stumm**) mutes the microphone; **Hang up** (**Auflegen**) ends the call. Collapsing the panel keeps the call active. Hold **0** to insert a plus sign at the start of a number.

Incoming calls have **Answer** (**Annehmen**) and **Decline** (**Ablehnen**) controls. Internal calls between kiosks remain available through Kiosk Satellite intercom.

## Settings and data flow

The phone button has settings for screen side, bottom offset, and local SIP port. The plugin uses native overlays, host state and control APIs, and Android microphone/audio access. Host state checks detect active voice and intercom sessions.

The plugin sends SIP signaling and RTP call audio to the configured Asterisk server on the local network. Asterisk connects to the configured telephone provider for external calls. Provider credentials stay in the HAOS add-on; the plugin stores the password for its local device extension using a secret setting. The optional web phone page stores its configuration and contacts in the add-on.

The project does not add an analytics or telemetry service. External calls transmit call signaling and audio through the configured provider.

## Updates

Update the plugin and Home Assistant app separately. Version 26.10.13 includes the native dialer and multi-device management. Add-on 26.10.12 remains compatible with one device on extension 100.

Updating plugin 26.10.12 to 26.10.13 replaces the web phone launcher with the native dialer. Enter the SIP connection details once in the plugin. The plugin ID remains `kiosk-satellite-sip`. Existing provider and add-on settings are preserved.

If the separate **SIP Native Dialer Lab** plugin is installed, disable it before enabling the regular plugin. The two IDs store separate settings and cannot use the same SIP extension at the same time.

## Scope and limitations

The native dialer uses IPv4, UDP, and G.711 on the local network. In-call DTMF, hold, transfer, TLS/SRTP, and contact synchronization into the native dialer are not implemented.

Shared microphone management with Voice Satellite remains open. The plugin blocks new calls when it detects an active voice recording or intercom session. Bounded audio buffering limits backlog; actual voice delay depends on the device and network. A measured latency comparison is not yet available.

The web phone page with contacts and the KS intercom audio bridge remain available as alternative modes. Their setup and call flow are described in the [HAOS documentation](kiosk_sip/DOCS.md).

## Further information

- [Releases and package format](RELEASES.md)
- [Implementation and automated tests](native-lab/README.md)
- [Changelog](kiosk_sip/CHANGELOG.md)
- [Published releases](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases)

## License

Apache-2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Kiosk Satellite is a separate project and is not bundled.
