"""Turn the frames a Charge 5 sends back into a SpeakerInfo.

Layouts are taken from the JBL Portable APK (v6.9.33, com.harman.sdk) and
checked against live captures (docs/PROTOCOL.md):

- 0x12 Speaker-Info: one token per frame, payload ``00 <token> [len] <value>``.
- 0x42 firmware: each byte printed as a decimal and joined with "." (the app's
  ReqVerCommand.formatVersion), so ``00 08 06 00`` -> "0.8.6.0".
- 0x66 feedback tones: ``<01 on | 00 off>``.
- 0x6D simple EQ: ``<scope> <active category> {<category> <n> {<type> <int8>}*n}*``.
- 0x82 analytics: big-endian u16 counters, Charge 5 order from
  ConnectingActivityViewModel.processDeviceAnalytics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .protocol import Frame, PacketType, Token

# Token 0x47 values (com.harman.sdk CommandProcessor audio-source switch).
AUDIO_SOURCES = {0: "none", 1: "bluetooth", 2: "aux", 3: "receiver", 4: "fm", 5: "dab"}

EQ_SIGNATURE = 0x01  # "JBL Signature" (EQ off)
EQ_CUSTOM = 0xC1
EQ_BASS, EQ_MID, EQ_TREBLE = 1, 2, 3

# ponytail: analytics units aren't in the APK; power_on_time grew ~1/min live,
# so all durations are treated as minutes.
ANALYTICS_FIELDS = (
    "app_connections",
    "app_connected_time",
    "critical_temperature",
    "power_bank_time",
    "play_time",
    "play_time_battery",
    "charging_time",
    "power_on_count",
    "power_on_time",
    "aux_play_time",
    "usb_pd_charging_time",
    "popular_volume_usage",
    "popular_volume_level",
)


@dataclass
class SpeakerInfo:
    """Everything one poll learns about the speaker; None when a reply is missing."""

    battery: int | None = None
    charging: bool | None = None
    source: str | None = None
    source_connected: bool | None = None
    name: str | None = None
    model: int | None = None
    color: int | None = None
    channel: int | None = None
    mac: str | None = None
    firmware: str | None = None
    feedback_tones: bool | None = None
    eq_preset: str | None = None
    eq_scope: int | None = None
    eq_bass: int | None = None
    eq_mid: int | None = None
    eq_treble: int | None = None
    analytics: dict[str, int] = field(default_factory=dict)
    raw: dict[int, str] = field(default_factory=dict)


def _token_value(payload: bytes) -> tuple[int, bytes] | None:
    """Split a `00 <token> [len] <value>` payload into (token, value), or None."""
    if len(payload) < 3 or payload[0] != 0x00:
        return None
    token = payload[1]
    if token == Token.DEVICE_NAME:
        # length-prefixed: 00 C1 <len> <bytes>
        length = payload[2]
        return token, payload[3 : 3 + length]
    return token, payload[2:]


def _int8(b: int) -> int:
    """Read a byte as a signed int8."""
    return b - 256 if b > 127 else b


def _bcd(b: int) -> str:
    """The app reads each byte's hex digits as decimal (0x10 -> "10")."""
    h = f"{b:02x}"
    return str(int(h)) if h.isdigit() else str(b)


def _parse_token(info: SpeakerInfo, payload: bytes) -> None:
    """Apply one Speaker-Info (0x12) token to ``info``."""
    parsed = _token_value(payload)
    if parsed is None:
        return
    token, value = parsed
    info.raw[token] = value.hex()
    if not value:
        return
    if token == Token.BATTERY:
        info.battery = value[0] & 0x7F
        info.charging = bool(value[0] & 0x80)
    elif token == Token.AUDIO_SOURCE:
        info.source = AUDIO_SOURCES.get(value[0], f"unknown_{value[0]}")
        info.source_connected = value[0] != 0x00
    elif token == Token.DEVICE_NAME:
        info.name = value.decode("utf-8", errors="replace")
    elif token == Token.MODEL:
        info.model = int.from_bytes(value, "big")
    elif token == Token.COLOR:
        info.color = value[0]
    elif token == Token.AUDIO_CHANNEL:
        info.channel = value[0]
    elif token == Token.MAC:
        info.mac = ":".join(f"{b:02x}" for b in value)


def _parse_eq(info: SpeakerInfo, p: bytes) -> None:
    """Apply a simple-EQ (0x6D) reply to ``info``."""
    if len(p) < 2:
        return
    info.eq_scope, active = p[0], p[1]
    info.eq_preset = {EQ_SIGNATURE: "signature", EQ_CUSTOM: "custom"}.get(active)
    i = 2
    while i + 2 <= len(p):
        category, n = p[i], p[i + 1]
        params = p[i + 2 : i + 2 + 2 * n]
        i += 2 + 2 * n
        if category != EQ_CUSTOM:
            continue  # numbers always show the custom slot, even while Signature plays
        values = {params[j]: _int8(params[j + 1]) for j in range(0, len(params) - 1, 2)}
        info.eq_bass = values.get(EQ_BASS, 0)
        info.eq_mid = values.get(EQ_MID, 0)
        info.eq_treble = values.get(EQ_TREBLE, 0)


def parse_speaker_info(frames: list[Frame]) -> SpeakerInfo:
    """Fold every reply frame of one poll into a SpeakerInfo."""
    info = SpeakerInfo()
    for frame in frames:
        p = frame.payload
        if frame.packet_type == PacketType.SPEAKER_INFO_RESPONSE:
            _parse_token(info, p)
        elif frame.packet_type == PacketType.FIRMWARE_VERSION_RESPONSE and p:
            info.firmware = ".".join(_bcd(b) for b in p)
        elif frame.packet_type == PacketType.FEEDBACK_RESPONSE and p:
            info.feedback_tones = p[0] == 0x01
        elif frame.packet_type == PacketType.SIMPLE_EQ_RESPONSE:
            _parse_eq(info, p)
        elif frame.packet_type == PacketType.ANALYTICS_RESPONSE:
            counters = [
                int.from_bytes(p[i : i + 2], "big") for i in range(0, len(p) - 1, 2)
            ]
            info.analytics = dict(zip(ANALYTICS_FIELDS, counters, strict=False))
    return info
