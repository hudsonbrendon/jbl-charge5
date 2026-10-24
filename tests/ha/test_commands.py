from custom_components.jbl_charge5.commands import (
    CHANNEL_LEFT,
    CHANNEL_MONO,
    CHANNEL_RIGHT,
    play_sound,
    set_audio_channel,
    set_feedback_tones,
)


def test_play_sound():
    assert play_sound() == bytes([0xAA, 0x31])


def test_set_audio_channel_left():
    # connect-plus spec: set left channel = AA 15 03 00 46 01
    expected = bytes([0xAA, 0x15, 0x03, 0x00, 0x46, 0x01])
    assert set_audio_channel(CHANNEL_LEFT) == expected


def test_set_audio_channel_mono_and_right():
    assert set_audio_channel(CHANNEL_MONO) == bytes(
        [0xAA, 0x15, 0x03, 0x00, 0x46, 0x00]
    )
    assert set_audio_channel(CHANNEL_RIGHT) == bytes(
        [0xAA, 0x15, 0x03, 0x00, 0x46, 0x02]
    )


def test_set_feedback_tones():
    assert set_feedback_tones(True) == bytes([0xAA, 0x67, 0x01, 0x01])
    assert set_feedback_tones(False) == bytes([0xAA, 0x67, 0x01, 0x00])


def test_set_eq_custom_and_signature():
    from custom_components.jbl_charge5.commands import set_eq_custom, set_eq_signature

    assert set_eq_custom(1, 0, -2).hex() == "aa6e08c1030101020003fe"
    assert set_eq_signature().hex() == "aa6e020100"
