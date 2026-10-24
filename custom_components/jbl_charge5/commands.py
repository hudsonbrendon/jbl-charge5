"""Pure builders for JBL Charge 5 control commands.

Byte formats verified against the pembem22/connect-plus protocol spec.
"""

from __future__ import annotations

from .parser import EQ_BASS, EQ_CUSTOM, EQ_MID, EQ_SIGNATURE, EQ_TREBLE
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


def set_eq_custom(bass: int, mid: int, treble: int) -> bytes:
    """Activate the custom EQ with these levels (-scope..+scope, scope=2 on a Charge 5).

    -> AA 6E 08 C1 03 01 <bass> 02 <mid> 03 <treble>  (EQFragmentViewModel)
    """
    bands = ((EQ_BASS, bass), (EQ_MID, mid), (EQ_TREBLE, treble))
    payload = bytes([EQ_CUSTOM, len(bands)]) + b"".join(
        bytes([band, level & 0xFF]) for band, level in bands
    )
    return encode_frame(PacketType.SIMPLE_EQ_SET, payload)


def set_eq_signature() -> bytes:
    """Back to the default "JBL Signature" sound -> AA 6E 02 01 00."""
    return encode_frame(PacketType.SIMPLE_EQ_SET, bytes([EQ_SIGNATURE, 0x00]))
