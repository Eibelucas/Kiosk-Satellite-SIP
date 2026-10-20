# Kiosk Satellite SIP Gateway for HAOS

This add-on includes the Asterisk telephone server and a web interface for configuring SIP providers, phone numbers, and devices. Installation is supported on Home Assistant OS with amd64 architecture.

- Provider profiles and manual SIP configuration.
- Up to eight external SIP accounts with separate numbers and call rules.
- Individual SIP extensions and passwords for multiple kiosks.
- Ringing targets for each external phone number.
- Local echo test on extension 600 for registered SIP devices.
- Optional web phone page with contacts and kiosk cards.
- Alternative audio bridge to Kiosk Satellite intercom.
- Dedicated announcement numbers with caller allowlists, an optional PIN, and a duration limit.

For the native KS dialer, select **SIP phone / Softphone 100** (**SIP-Telefon / Softphone 100**) as the audio target. Device management defines each device extension and password. Provider registration stays centralized in the add-on.

The alternative **Kiosk Satellite Intercom** bridge connects one configured kiosk through a shared intercom key. It uses local HTTP/WebSocket connections and currently does not support TLS intercom.

[Setup, operating modes, and troubleshooting](DOCS.md)
