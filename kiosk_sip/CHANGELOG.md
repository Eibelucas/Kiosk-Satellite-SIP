# 26.10.18

- Support numeric SIP device extensions with 1–79 digits, including 6000–6299, in the plugin and gateway.
- Accept custom extensions in device editors and ring targets while retaining extension 100 compatibility and echo service 600.
- Prevent configured local device identities from falling through to the external provider dial plan.
- Verify simultaneous 6000/6299 SIP registration, ring-group cancellation, password retention and editor persistence.

# 26.10.17

- Add separate administration pages for SIP accounts, numbers, kiosks, contacts, network and diagnostics.
- Preserve existing SIP credentials, device identities, routing and ports during automatic workspace migration.
- Save drafts independently from explicit runtime application, with rollback on activation failure.
- Keep telephone runtime disablement across restarts and retain extension 100 for existing clients.

# 26.10.16

- Rename the plugin to **SIP Phone for Kiosk Satellite** while preserving its ID and existing settings.
- Use English metadata and default UI text; select **Language → Deutsch** for German call controls and status messages.
- Temporarily mute wake word before a user places or answers a call, wait for listening to stop, and restore the previous mute state after hangup, cancellation, or failure. Incoming ringing alone does not mute it.
- Restrict the SDP RTP destination to the resolved PBX address and connect the RTP socket to that endpoint.
- Remove the unused web-phone plugin class and obsolete test wording.

Active Voice Satellite turns and intercom still block or end calls. If the host cannot mute wake word or release its microphone, pause wake word in Kiosk Satellite before calling. End calls before disabling or updating the plugin; interruption after host access is revoked can require manually restoring the wake word mute switch.

Automated checks exercise the mute lifecycle, cancellation races, media redirection rejection, SIP signaling, and package format. Physical microphone release and latency on Android devices still require device testing.

# 26.10.15

- Correct the manifest icon name to be relative to the assets directory, as required by Kiosk Satellite.
- Keep the icon at assets/icon.png in the release ZIP and validate the asset path during packaging.

# 26.10.14

- Add a 256 × 256 plugin icon to the manifest and release package.
- Add the official Install in Kiosk Satellite badge and installation instructions.
- Verify the packaged icon's size, dimensions, and source bytes before publishing.

# 26.10.13

- Native SIP dialer with a floating phone button and direct outgoing call setup.
- Call view with destination, status, duration, mute, hangup, and centered icons.
- Separate SIP devices 101–199 with individual passwords and ring groups per external number. Extension 100 remains compatible.
- Separate RTP reception and playback, a PCM queue bounded to 60 ms, and smaller Android buffer requests.
- Existing plugin ID `kiosk-satellite-sip`; updating from the web phone launcher requires one-time SIP configuration. [Update guide](../README.md#updates).

# 26.10.12

- Incoming kiosk calls display the caller number supplied by the provider instead of the account label.
- Asterisk caller privacy is respected: anonymous calls and missing or invalid caller numbers have separate display labels.
- Caller numbers are used only for the local KS call display, without new storage in status, configuration, or logs.
- Tests cover FastAGI, intercom callbacks, and real Asterisk with fictional caller data.
- Number configuration, outgoing call flow, audio, and announcement permissions are unchanged.

# 26.10.11

- Web phone page with a compact sidebar connection status and no introductory heading.
- The keypad is the default view before contacts load. Loading contacts preserves an already selected view.
- A direct contacts command opens existing contacts and favorites.
- Selecting a contact prepares a number; calling still requires the call action and confirmation.
- The native KS intercom list is unchanged. SDK 1 has no phone-contact or speed-dial registration API.
- Stored contacts, numbers, settings, and SIP/audio behavior are preserved.

# 26.10.10

- Setup uses wide screens with the form and status side by side and related fields in two columns.
- Compact web phone sidebar, multiple contact columns, and a smaller keypad with large controls.
- Sections stack on narrow screens; long contact and status text can wrap.
- Additional test guidance is expandable; kiosk echo and connection checks remain accessible.
- Corrected kiosk audio and local echo documentation without changing SIP/audio behavior or stored settings.
- The isolated SIP test staggers its three simulated account registrations and retry timing to avoid transaction collisions. Production timing is unchanged.

# 26.10.9

- Kiosk Satellite intercom audio target using Asterisk 20 AudioSocket at 8 kHz, conversion to 16 kHz, and a native intercom WebSocket.
- Normal calls ring the kiosk; accepting opens audio and connects the call.
- Dedicated announcements retain allowlists, PINs, and duration limits and use one-way kiosk intercom audio.
- Signed callbacks, replay protection, and local keys excluded from status/API/log output.
- Connection check and local kiosk echo test in the setup assistant.
- The intercom listener port is obtained from device identity. One configured kiosk and local HTTP/WebSocket connections are supported; encrypted intercom is rejected without changing device settings.
- SIP phone 100 remains available as an alternative audio output.

# 26.10.8

- Validation distinguishes private device addresses, incorrect local networks, and invalid network/broadcast addresses.
- Initial setup no longer prefills an example network; the deployment network must be entered.
- The summary shows the configured network and prefix.
- Existing local configuration and SIP functionality are preserved.

# 26.10.7

- General HAOS guide without hardware-specific personal references.
- Neutral field guidance instead of location-specific number and network examples.
- Tests use fictional phone numbers and an independent test network.
- The standalone gateway starts without a preconfigured example contact.
- Existing local account data is unchanged.

# 26.10.6

- HA ingress uses the Supervisor-assigned port instead of fixed port 8099, resolving host-network startup conflicts.
- Setup stays accessible during SIP/AMI port conflicts and supports saving after correction.
- During LAN web port conflicts, HA ingress remains accessible so the gateway port can be changed.
- Asterisk is ready only after both SIP transports load. Failed starts are cleaned up.
- Regression coverage for occupied ports 8099/5070, a simulated Supervisor, access control, and clean shutdown.
- Existing account data is preserved. The kiosk intercom audio bridge was not implemented in this version.

# 26.10.5

- Contacts displayed as kiosk/room cards with favorites and search.
- Contact editing in the HA assistant; existing contacts are preserved.
- Selecting a card prepares a call without dialing automatically.
- Complete provider, number, announcement, and update documentation.

# 26.10.4

- Dedicated announcement number with allowed caller numbers.
- One-way audio to SIP phone/speaker 100; the target microphone remains muted.
- Optional automatic answer through SIP headers for announcements only.
- Optional six-digit PIN, bounded duration, and protection against parallel announcements.
- Normal calls retain standard ringing and the default outgoing number.

# 26.10.3

- Up to eight separate number accounts with individual providers, credentials, and status.
- Default outgoing number, with other normal numbers selectable in the web dialer.
- Incoming calls can ring or be rejected; unknown destinations are rejected.
- Unique routing for multiple accounts on the same SIP registrar.
- Existing single-account configuration is migrated.

# 26.10.2

- Provider selection for Telekom, sipgate, easybell, FRITZ!Box, and manual Vodafone, 1&1, o2, or custom accounts.
- Individual SIP ID, registrar, domain, proxy, realm, and UDP/TCP.
- Stored credentials are not reused after changing the provider.
- Release ZIP and SHA-256 are checked before upload.

# 26.10.1

- HAOS add-on with Asterisk and a German-language Telekom setup flow.
- Protected HA setup, local web phone page, and SIP extension 100.
- CI verifies real local SIP registration with special characters in the password.

# 0.1.0

- HAOS add-on with Asterisk 20 from Alpine Linux.
- German-language setup for Telekom residential service.
- Local credential storage, ingress setup, and protected LAN access.
- SIP phone 100 registration, echo test 600, and call setup through local AMI.
- Status for Asterisk, provider registration, and the SIP phone.
- No kiosk intercom audio bridge in this version.
