import pytest

from jbl_charge5.protocol import Frame, PacketType, decode_frame, encode_frame


def test_encode_no_payload_omits_length_byte():
    # connect-plus spec: play-sound is just AA 31, no length byte.
    assert encode_frame(PacketType.PLAY_SOUND) == bytes([0xAA, 0x31])


def test_encode_with_payload_includes_length():
    # spec: enable feedback sounds = AA 67 01 01
    assert encode_frame(0x67, b"\x01") == bytes([0xAA, 0x67, 0x01, 0x01])


def test_encode_multibyte_payload_length():
    # spec: set left channel = AA 15 03 00 46 01
    assert encode_frame(0x15, bytes([0x00, 0x46, 0x01])) == bytes(
        [0xAA, 0x15, 0x03, 0x00, 0x46, 0x01]
    )


def test_speaker_info_request_is_aa11():
    # No payload => no length byte.
    assert encode_frame(PacketType.SPEAKER_INFO_REQUEST) == bytes([0xAA, 0x11])


def test_decode_no_payload_frame():
    frame = decode_frame(bytes([0xAA, 0x31]))
    assert frame == Frame(packet_type=0x31, payload=b"")


def test_decode_frame_with_payload():
    frame = decode_frame(bytes([0xAA, 0x12, 0x02, 0x44, 0x4B]))
    assert frame == Frame(packet_type=0x12, payload=bytes([0x44, 0x4B]))


def test_decode_rejects_bad_preamble():
    with pytest.raises(ValueError, match="preamble"):
        decode_frame(bytes([0xBB, 0x12, 0x00]))


def test_decode_rejects_truncated_payload():
    # length says 5 but only 1 payload byte present
    with pytest.raises(ValueError, match="truncated"):
        decode_frame(bytes([0xAA, 0x12, 0x05, 0x44]))
