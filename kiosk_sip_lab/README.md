# SIP Phone UI Lab

A separately installed Home Assistant OS test app for the redesigned SIP Phone administration interface.

The application has dedicated pages for overview, SIP accounts, phone numbers, kiosks and devices, contacts, network settings, and diagnostics. SIP credentials are edited only in SIP accounts. Numbers own their routing and ring targets. Each kiosk has a separate device identity and password.

## Installation

Add this repository to the Home Assistant app store, install **SIP Phone - UI Lab**, start it, and select **Open Web UI**. The regular gateway can stay installed and running. The lab has its own slug, data directory, browser session cookie, and port assignments.

The initial configuration is empty and the test telephone server is off. **View sample data** loads clearly marked fictional records without connecting to a provider. To enter real configuration, start a blank draft. Sample records cannot activate telephony.

## Editing and applying

Saving an account, number, kiosk, contact, or network form stores a draft. It does not restart Asterisk. **Apply changes** explicitly applies the saved revision. Enable the test telephone server in Network only when its separate configuration is ready.

This UI uses the existing gateway SIP implementation. It supports one number per SIP login; shared trunk registrations are not implemented. The UI separates these records without adding unsupported trunk behavior.

## Separate services

- SIP: default 5083, chosen separately from the production gateway.
- RTP: UDP 30200–30299.
- AMI: loopback TCP 5039.
- Optional LAN web phone: default 8092, disabled initially.
- Optional legacy intercom callback: default 8093.

The administration UI is available only through authenticated Home Assistant ingress. The test runtime remains off until explicitly applied. It does not import production configuration or provider credentials automatically. Provider registration limits still apply if additional real accounts are activated.

Passwords and keys are stored locally with restricted file permissions. API responses and configuration exports omit secrets. Blank password fields retain the saved secret only while the corresponding identity remains unchanged.

## Validation

CI checks draft validation, secret redaction and preservation, stale-revision rejection, explicit runtime activation, distinct ports, container startup with telephony disabled, and browser workflows at desktop and mobile widths.
