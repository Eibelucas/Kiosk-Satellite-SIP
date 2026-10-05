# Kiosk Satellite SIP

Unofficial SIP/telephone extension for [Kiosk Satellite](https://github.com/jxlarrea/kiosk-satellite).

The project is split into two parts:

1. **Kiosk Satellite plugin** – adds a `Telefon öffnen` command and opens the configured phone UI inside Kiosk Satellite.
2. **SIP gateway** – serves a touch-friendly dial pad/contact page and talks to Asterisk through AMI for outbound call setup.

> Status: early development / v0.1.0. Outbound call setup is implemented as an Asterisk AMI originate request. The bidirectional RTP ↔ Kiosk Satellite Intercom audio bridge and incoming-call injection are the next milestone.

## Planned architecture

```text
Kiosk Satellite
  └─ Kiosk Satellite SIP plugin
       └─ Phone UI (gateway)
            └─ Kiosk SIP Gateway
                 └─ Asterisk
                      └─ Telekom SIP / PSTN
```

## Current features

- Kiosk Satellite SDK 1 plugin
- Configurable gateway URL
- `Telefon öffnen` plugin command
- Responsive dial pad
- Local contact list from `gateway/contacts.json`
- Outbound Asterisk AMI `Originate`
- Optional caller ID and dial context configuration
- Docker image for the gateway
- GitHub Actions plugin build/release workflow

## Quick start

### 1. Gateway

Copy the example configuration:

```bash
cd gateway
cp .env.example .env
```

Edit the Asterisk AMI values, then run:

```bash
pip install -r requirements.txt
python app.py
```

The web UI defaults to `http://HOST:8088/`.

### 2. Kiosk Satellite plugin

Install a release ZIP from this repository in Kiosk Satellite's Plugin Manager. Configure `Gateway URL` to the URL from step 1 and run the `Telefon öffnen` command.

Plugin packages follow Kiosk Satellite SDK 1 and contain `kiosk-satellite-plugin.json`, `plugin.jar`, and `LICENSE`.

## Asterisk example

Enable an AMI user with the minimum permissions needed for `Originate` and set a dial context that can reach your Telekom SIP trunk.

Example environment values:

```env
AMI_HOST=192.168.1.20
AMI_PORT=5038
AMI_USERNAME=kioskphone
AMI_SECRET=change-me
ASTERISK_CHANNEL=PJSIP/100
ASTERISK_CONTEXT=from-kiosk-phone
ASTERISK_CALLER_ID=Kiosk <100>
```

For a number such as `02161123456`, the gateway currently originates the configured local channel and sends the number into the configured dialplan context.

## Security

Do not expose AMI to the internet. Keep the gateway and AMI on your trusted LAN/VPN, use an AMI account restricted to the required commands, and put authentication/TLS in front of the gateway before exposing it outside the LAN.

## Roadmap

- Incoming PSTN/SIP call → Kiosk Satellite Intercom ringing
- Answer/decline/hangup synchronization
- PCM16 16 kHz mono ↔ RTP media bridge
- Multiple kiosks / ring groups
- Call history
- Contact editing
- Home Assistant services/entities
- DTMF during an active call

## License

Apache-2.0. Kiosk Satellite is a separate project and is not bundled here.
