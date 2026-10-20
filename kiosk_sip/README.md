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
