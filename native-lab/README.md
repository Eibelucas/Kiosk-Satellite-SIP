# Native SIP dialer implementation

The native dialer is part of the regular `kiosk-satellite-sip` plugin starting with version 26.10.13. This page describes architecture and test coverage. Installation and usage are covered in the [main guide](../README.md).

## Architecture

```text
Android kiosk with SIP plugin
  → local SIP extension on Asterisk
  → configured provider account
  → external phone number
```

A persistent Android overlay displays the phone button and expandable dialer. Styling and colors come from the Kiosk Satellite SDK. Outgoing calls use SIP INVITE directly; microphone capture starts after the remote party answers. Incoming calls require local acceptance.

Call state is independent of whether the overlay is expanded. Cancellation, remote hangup, plugin shutdown, and media failures release the associated resources.

## SIP devices and phone numbers

Asterisk maintains separate authentication and registration for each enabled SIP device. Extension 100 supports one device; additional devices use unique numeric extensions with 1–79 digits. The bundled gateway reserves extension 600 for the echo test. A new registration for an extension replaces its previous registration.

External phone numbers can ring individual devices or a group. When one device answers, Asterisk sends CANCEL to the remaining targets. Internal device calls are handled by KS intercom rather than the SIP dialer.

## Audio

The plugin sends G.711 audio over RTP between Android and Asterisk. Capture and playback use Android audio APIs in communication mode. RTP reception and speaker playback run on separate threads.

The PCM queue holds at most 480 samples, or 60 ms at 8 kHz. When a backlog develops, older frames are dropped. Duplicate and late RTP sequences are not replayed. The requested Android playback buffer is 320 frames, or 40 ms; Android may enforce a larger minimum.

These values describe local buffering, not total call latency. A measured comparison on Android devices is not yet available. An adaptive jitter buffer and a shared audio lease with KS/Voice Satellite are not implemented. Before a user places or answers a call, WakeWordGuard reads and preserves the mute state, requests temporary muting, and waits for listening to stop. It restores the previous state after normal completion, cancellation, or failure, including cancellation while a mute callback is pending. Ringing alone does not acquire this guard. A host that cannot release capture requires manually paused wake word. Stop cannot restore state because KS revokes the session first; the README documents the recovery.

AndroidG711 accepts an SDP RTP address only when it equals the PBX address already resolved by NativeSipClient. Its UDP socket is connected to that negotiated PBX endpoint, and receive checks also enforce the address and port. A private address alone is insufficient. The phone therefore requires the PBX to anchor media.

## Automated checks

`python tools/test_native.py` compiles the SDK and plugin against the Android APIs. SIP tests use a local simulated telephone server and simulated media. They cover:

- Digest registration and authenticated SIP requests.
- Outgoing and incoming calls, cancellation, answer races, and hangup.
- UDP retransmissions and rejection of responses from foreign sources.
- Independent device identities and call state.
- G.711 conversion, SDP, and resource cleanup after media failures.
- Wake word mute ownership, prior-muted and disabled states, delayed callbacks, cancellation, failure, bounded polling, and session revocation.
- Rejection of SDP media redirection to other private, public, or loopback addresses, including an outgoing call response before simulated capture starts.
- English defaults and the optional German UI.
- Bounded audio queues during playback stalls, variable packet sizes, duplicates, and sequence wraparound.

Add-on CI also tests configuration and API behavior, plus real Asterisk instances with multiple local test devices, ring groups, and the audio bridge. Tests use fictional credentials. These checks do not measure Android audio quality or end-to-end latency over a provider connection.

`tools/build.py` builds the Android DEX package. `tools/verify_package.py` validates the plugin ID, manifest, ZIP contents, and SHA-256 checksum. The build environment requires JDK 21 and an Android SDK; `JAVA_HOME` and `ANDROID_HOME` point to those installations.

## Origins and license

Development initially used the separate plugin ID `kiosk-satellite-sip-native-lab`. Earlier test installations use that ID; the current regular ID is `kiosk-satellite-sip`.

- [Kiosk Satellite Community SDK](https://github.com/jxlarrea/kiosk-satellite-plugins): SDK, theme, and overlay contract.
- [Navbar](https://github.com/dimatx/kiosk-satellite-navbar): reference for native overlay controls.
- [SIP Phone](https://github.com/meiser79/kiosk-satellite-sip-phone): basis for SIP messages, Digest, and G.711 conversion.

License and attribution details are in [NOTICE](../NOTICE) and [LICENSE](../LICENSE).
