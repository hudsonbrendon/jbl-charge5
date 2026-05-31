from jbl_charge5.protocol import PacketType, decode_frame
from jbl_charge5.tokens import extract_battery


def test_real_charge5_battery_capture():
    # Captured from a real JBL Charge 5 on 2026-05-31 (speaker reported full).
    # Reply to Speaker-Info request 0xAA11 arrives as one token per 0x12 frame;
    # the battery frame was aa1203004464 (payload 00 44 64 -> 0x64 == 100%).
    frame = decode_frame(bytes.fromhex("aa1203004464"))
    assert frame.packet_type == PacketType.SPEAKER_INFO_RESPONSE
    assert extract_battery(frame.payload) == 100


def test_extract_battery_basic():
    # token 0x44 followed by battery percentage 0x4B == 75
    assert extract_battery(bytes([0x44, 0x4B])) == 75


def test_extract_battery_when_surrounded_by_other_tokens():
    # model token (0x42, len-prefixed) then battery then linked-devices
    payload = bytes([0x42, 0x01, 0x07, 0x44, 0x32, 0x45, 0x01, 0x00])
    assert extract_battery(payload) == 50


def test_extract_battery_absent_returns_none():
    assert extract_battery(bytes([0x45, 0x01, 0x00])) is None
