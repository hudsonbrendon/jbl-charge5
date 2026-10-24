"""Pure, I/O-free codec for the JBL/Harman 0xAA-framed control protocol.

Frame layout (pembem22/connect-plus #56, confirmed in the JBL Portable APK's
com.harman.sdk.utils.PacketFormat / BaseCommand):
    0xAA | packet_type | [length | payload...]
The app always sends the length byte (``AA 11 00``); the speaker also accepts
the bare ``AA 11`` form we send for payload-less requests. No checksum.
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
    SIMPLE_EQ_REQUEST = 0x6C
    SIMPLE_EQ_RESPONSE = 0x6D
    SIMPLE_EQ_SET = 0x6E
    ANALYTICS_REQUEST = 0x81
    ANALYTICS_RESPONSE = 0x82
    UNSUPPORTED = 0xEE


class Token(IntEnum):
    MODEL = 0x42
    COLOR = 0x43
    BATTERY = 0x44
    LINKED_DEVICES = 0x45
    AUDIO_CHANNEL = 0x46
    AUDIO_SOURCE = 0x47
    MAC = 0x48
    MAC_CRC16 = 0x4A
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


def _frame_size(data: bytes) -> int:
    """Bytes a frame starting at data[0] occupies (bare 2-byte frames allowed)."""
    return 2 if len(data) <= 2 else 3 + data[2]


def reassemble(chunks: list[bytes]) -> list[Frame]:
    """Turn raw GATT notifications into frames.

    The speaker splits frames longer than its notification size across several
    notifications (seen live: the 0x6D EQ reply arrives as 11 + 10 bytes), and a
    continuation may itself start with 0xAA. So a chunk only starts a new frame
    once the pending one has all the bytes its length byte promised.
    """
    frames: list[Frame] = []
    pending = b""
    for chunk in chunks:
        if pending and len(pending) < _frame_size(pending):
            pending += chunk
        else:
            pending = chunk
        while pending and len(pending) >= _frame_size(pending):
            size = _frame_size(pending)
            try:
                frames.append(decode_frame(pending[:size]))
            except ValueError:
                pass  # not an 0xAA frame; drop it
            pending = pending[size:]
    return frames
