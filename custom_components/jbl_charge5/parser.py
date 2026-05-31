"""Turn a burst of Speaker-Info (0x12) frames into a SpeakerInfo.

Each 0x12 payload is `00 <token> [len] <value...>`. Most tokens carry a
fixed-size value; 0xC1 (name) is length-prefixed; 0x48 (MAC) is 6 raw bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .protocol import Frame, PacketType, Token


@dataclass
class SpeakerInfo:
    battery: int | None = None
    source_connected: bool | None = None
    name: str | None = None
    model: int | None = None
    color: int | None = None
    channel: int | None = None
    mac: str | None = None
    raw: dict[int, str] = field(default_factory=dict)


def _token_value(payload: bytes) -> tuple[int, bytes] | None:
    """Payload is `00 <token> [len] <value>`. Return (token, value) or None."""
    if len(payload) < 3 or payload[0] != 0x00:
        return None
    token = payload[1]
    if token == Token.DEVICE_NAME:
        # length-prefixed: 00 C1 <len> <bytes>
        length = payload[2]
        return token, payload[3 : 3 + length]
    return token, payload[2:]


def parse_speaker_info(frames: list[Frame]) -> SpeakerInfo:
    info = SpeakerInfo()
    for frame in frames:
        if frame.packet_type != PacketType.SPEAKER_INFO_RESPONSE:
            continue
        parsed = _token_value(frame.payload)
        if parsed is None:
            continue
        token, value = parsed
        info.raw[token] = value.hex()
        if not value:
            continue
        if token == Token.BATTERY:
            info.battery = value[0]
        elif token == Token.AUDIO_SOURCE:
            info.source_connected = value[0] == 0x01
        elif token == Token.DEVICE_NAME:
            info.name = value.decode("ascii", errors="replace")
        elif token == Token.MODEL:
            info.model = int.from_bytes(value, "big")
        elif token == Token.COLOR:
            info.color = value[0]
        elif token == Token.AUDIO_CHANNEL:
            info.channel = value[0]
        elif token == Token.MAC:
            info.mac = ":".join(f"{b:02x}" for b in value)
    return info
