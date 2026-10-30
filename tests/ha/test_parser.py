from custom_components.jbl_charge5.parser import SpeakerInfo, parse_speaker_info
from custom_components.jbl_charge5.protocol import decode_frame

# Real burst captured from a JBL Charge 5 on 2026-05-31 (battery was 100%).
REAL_FRAMES_HEX = [
    "aa120f00c10c4a424c204368617267652035",  # name "JBL Charge 5"
    "aa120400422040",  # model 0x2040
    "aa1203004301",  # color 0x01
    "aa1203004464",  # battery 0x64 = 100
    "aa1203004600",  # channel 0x00
    "aa1203004701",  # source state 0x01 (connected)
    "aa12080048aabbccddeeff",  # MAC aa:bb:cc:dd:ee:ff
]


def _frames():
    return [decode_frame(bytes.fromhex(h)) for h in REAL_FRAMES_HEX]


def test_parse_real_burst():
    info = parse_speaker_info(_frames())
    assert isinstance(info, SpeakerInfo)
    assert info.battery == 100
    assert info.source_connected is True
    assert info.name == "JBL Charge 5"
    assert info.model == 0x2040
    assert info.color == 0x01
    assert info.channel == 0x00
    assert info.mac == "aa:bb:cc:dd:ee:ff"


def test_parse_idle_source():
    # source token 0x00 -> not connected
    frames = [decode_frame(bytes.fromhex("aa1203004700"))]
    info = parse_speaker_info(frames)
    assert info.source_connected is False
    assert info.battery is None  # battery token absent in this partial burst


def test_parse_ignores_non_speaker_info_frames():
    frames = [decode_frame(bytes.fromhex("aa31"))]  # play-sound, not 0x12
    info = parse_speaker_info(frames)
    assert info.battery is None
    assert info.name is None


# --- Opcodes mapped from the JBL Portable APK (v6.9.33), captured live 2026-10-24.

from custom_components.jbl_charge5.protocol import reassemble  # noqa: E402

LIVE_CHUNKS_HEX = [
    "aa1203004450",  # battery 80, not charging
    "aa1203004702",  # source 2 = AUX
    "aa420400080600",  # firmware -> "0.8.6.0"
    "aa660100",  # feedback tones off
    "aa6d1202c1010301000200",  # simple EQ, split by the speaker...
    "0300c103010102ff03fe",  # ...across two notifications
    (
        "aa82260001000000280000065005c21712002909ed"
        "0000000000000000000000000000000000000000"
    ),  # analytics
]


def _live_info():
    return parse_speaker_info(reassemble([bytes.fromhex(h) for h in LIVE_CHUNKS_HEX]))


def test_reassemble_joins_split_notification():
    frames = reassemble([bytes.fromhex(h) for h in LIVE_CHUNKS_HEX])
    eq = next(f for f in frames if f.packet_type == 0x6D)
    assert len(eq.payload) == 0x12


def test_reassemble_keeps_bare_frames():
    frames = reassemble([bytes.fromhex("aa12"), bytes.fromhex("aa1203004450")])
    assert [f.packet_type for f in frames] == [0x12, 0x12]


def test_battery_charging_bit():
    # APK CommandProcessor: value >= 128 -> charging, level = value - 128.
    info = parse_speaker_info([decode_frame(bytes.fromhex("aa12030044d0"))])
    assert info.battery == 80
    assert info.charging is True
    assert _live_info().charging is False


def test_audio_source_aux_counts_as_in_use():
    info = _live_info()
    assert info.source == "aux"
    assert info.source_connected is True


def test_firmware_feedback_eq_analytics():
    info = _live_info()
    assert info.firmware == "0.8.6.0"
    assert info.feedback_tones is False
    assert info.eq_preset == "custom"
    assert (info.eq_bass, info.eq_mid, info.eq_treble) == (1, -1, -2)
    assert info.analytics["play_time"] == 0x0650
    assert info.analytics["play_time_battery"] == 0x05C2
    assert info.analytics["charging_time"] == 0x1712
    assert info.analytics["power_on_count"] == 0x29
    assert info.analytics["power_on_time"] == 0x09ED
    assert info.analytics["critical_temperature"] == 0x28


def test_eq_signature_active():
    frames = reassemble(
        [bytes.fromhex("aa6d120201010301000200"), bytes.fromhex("0300c103010002000300")]
    )
    info = parse_speaker_info(frames)
    assert info.eq_preset == "signature"
    assert (info.eq_bass, info.eq_mid, info.eq_treble) == (0, 0, 0)
