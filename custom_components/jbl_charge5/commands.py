"""Pure builders for JBL Charge 5 control commands.

Byte formats verified against the pembem22/connect-plus protocol spec.
"""

from __future__ import annotations

from .protocol import PacketType, Token, encode_frame

# Audio channel values (Speaker-Info token 0x46 / Speaker-Info-Set payload).
CHANNEL_MONO = 0x00
CHANNEL_LEFT = 0x01
CHANNEL_RIGHT = 0x02


def play_sound() -> bytes:
    """Make the speaker emit its feedback tone (find-my-speaker) -> AA 31."""
    return encode_frame(PacketType.PLAY_SOUND)


def set_audio_channel(channel: int) -> bytes:
    """Set the PartyBoost stereo channel (e.g. left -> AA 15 03 00 46 01)."""
    return encode_frame(
        PacketType.SPEAKER_INFO_SET, bytes([0x00, Token.AUDIO_CHANNEL, channel])
    )


def set_feedback_tones(enabled: bool) -> bytes:
    """Enable/disable the speaker feedback tones (on -> AA 67 01 01)."""
    return encode_frame(PacketType.FEEDBACK_SET, bytes([0x01 if enabled else 0x00]))
