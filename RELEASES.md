# Releases 26.10

Versions use the year.month.update format, for example `26.10.1`. Git tags include a `v` prefix, such as `v26.10.1`. The plugin and HAOS add-on use the same version but must be installed or updated separately.

| Version | Changes |
| --- | --- |
| [26.10.1](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.1) | HAOS add-on with Asterisk and Telekom setup |
| [26.10.2](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.2) | Multiple providers and manual SIP profiles |
| [26.10.3](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.3) | Separate number accounts, default outgoing number, and migration |
| [26.10.4](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.4) | Dedicated announcement number, caller allowlist, optional PIN, and one-way audio |
| [26.10.5](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.5) | Contact and kiosk cards, favorites, search, and setup guide |
| [26.10.6](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.6) | Dynamic HA ingress port and setup access during SIP/LAN port conflicts |
| [26.10.7](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.7) | General documentation and neutral examples |
| [26.10.8](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.8) | Precise local-network validation and no prefilled example network |
| [26.10.9](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.9) | Native intercom audio bridge for one kiosk, incoming calls, announcements, and echo test |
| [26.10.10](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.10) | Responsive setup and web phone page |
| [26.10.11](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.11) | Default keypad view and direct contacts command |
| [26.10.12](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.12) | Incoming caller number display and caller privacy handling |
| [26.10.13](https://github.com/Eibelucas/Kiosk-Satellite-SIP/releases/tag/v26.10.13) | Native SIP calls, multiple devices, ring groups, compact call view, and bounded audio buffering |

## Installing and updating

Repository URL for **Kiosk Satellite → Plugin Manager → Add plugin**:

```text
https://github.com/Eibelucas/Kiosk-Satellite-SIP
```

Use the same URL under **Home Assistant → Apps/Add-ons → Store → Repositories**. Install and start **Kiosk Satellite SIP Gateway**, then open its web interface. Provider and device configuration is managed locally there. See the [setup guide](kiosk_sip/DOCS.md).

Starting with 26.10.13, the regular plugin replaces the web phone launcher. Enter the HAOS address, SIP port, extension, and device password once. Disable any separate Lab plugin before enabling the regular plugin. See [migration](README.md#updates).

Regular releases are public stable releases. The `build-plugin.yml` workflow responds to `release: published`, builds the tagged source, and uploads three files as `github-actions[bot]`:

- `kiosk-satellite-sip-VERSION.zip`
- `kiosk-satellite-plugin.json`
- `kiosk-satellite-sip-VERSION.zip.sha256`

Before upload, the ZIP is checked for exactly three root entries: the manifest, `plugin.jar` containing Android DEX, and `LICENSE`. The manifest inside the ZIP must be byte-identical to the standalone asset. The SHA-256 file records the actual ZIP hash and filename. Every plugin build runs these checks.

## Automated checks

[GitHub Actions](https://github.com/Eibelucas/Kiosk-Satellite-SIP/actions) checks:

- Configuration, migration, provider accounts, and unique incoming destination IDs.
- Redaction and preservation of credentials, and restricted configuration file permissions.
- HA ingress, LAN authentication, CSRF protection, and rate limits.
- Outgoing calls on enabled normal accounts and the AMI request for the selected web phone account.
- The amd64 Docker image and a real Asterisk instance.
- SIP Digest authentication, including passwords with special characters.
- Local SIP-SRV resolution and multiple simulated provider accounts.
- Incoming routing, rejected numbers, and unknown destinations.
- Announcement allowlists, PINs, automatic-answer headers, and one-way RTP audio.
- Web contacts, kiosk cards, and JavaScript syntax.
- Intercom signaling, signed callbacks, answer/hangup behavior, and two-way 16 kHz audio.
- The Asterisk AudioSocket path with a local echo target and simulated kiosk.
- Native SIP call state and bounded audio queues under playback stalls.

These checks use fictional credentials and local test servers. Real provider compatibility, router NAT, device audio, and Home Assistant Supervisor behavior require validation in the deployment environment.

## Remaining limitations

The regular plugin uses native SIP audio with a separate device extension and manual acceptance of incoming calls. Shared microphone coordination with KS/Voice Satellite and measured latency comparisons remain open.

The alternative web phone page uses a SIP phone or the audio bridge to one configured Kiosk Satellite intercom device. The bridge uses local HTTP/WebSocket connections and does not support TLS intercom. Kiosk cards are web contact entries. TLS/SRTP, IP-authenticated trunks, and shared trunk registrations for multiple direct-dial numbers are not complete supported profiles.
