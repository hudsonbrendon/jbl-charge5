"""Pure, I/O-free codec for the JBL/Harman 0xAA-framed control protocol.

Frame layout (from pembem22/connect-plus discussion #56):
    0xAA | packet_type | [length | payload...]
The length byte and payload are present only when there is a payload.
No checksum.
"""

from dataclasses import dataclass, field
from enum import IntEnum

PREAMBLE = 0xAA


class PacketType(IntEnum):
    ACK = 0x00
    SPEAKER_INFO_REQUEST = 0x11
    SPEAKER_INFO_RESPONSE = 0x12
    SPEAKER_INFO_SET = 0x15
    PLAY_SOUND = 0x31
    FIRMWARE_VERSION_REQUEST = 0x41
    FIRMWARE_VERSION_RESPONSE = 0x42
    FEEDBACK_REQUEST = 0x65
    FEEDBACK_RESPONSE = 0x66
    FEEDBACK_SET = 0x67


class Token(IntEnum):
    MODEL = 0x42
    COLOR = 0x43
    BATTERY = 0x44
    LINKED_DEVICES = 0x45
    AUDIO_CHANNEL = 0x46
    AUDIO_SOURCE = 0x47
    MAC = 0x48
    DEVICE_NAME = 0xC1


def encode_frame(packet_type: int, payload: bytes = b"") -> bytes:
    """Build a control frame. Length byte is omitted when payload is empty."""
    if not payload:
        return bytes([PREAMBLE, packet_type])
    if len(payload) > 0xFF:
        raise ValueError("payload too long for single-byte length field")
    return bytes([PREAMBLE, packet_type, len(payload)]) + payload


@dataclass(frozen=True)
class Frame:
    packet_type: int
    payload: bytes = field(default=b"")


def decode_frame(data: bytes) -> Frame:
    """Parse a single control frame. Raises ValueError on malformed input."""
    if len(data) < 2 or data[0] != PREAMBLE:
        raise ValueError(f"bad preamble or too short: {data.hex()}")
    packet_type = data[1]
    if len(data) == 2:
        return Frame(packet_type=packet_type, payload=b"")
    length = data[2]
    payload = data[3:]
    if len(payload) < length:
        raise ValueError(f"truncated payload: want {length}, got {len(payload)}")
    return Frame(packet_type=packet_type, payload=payload[:length])
