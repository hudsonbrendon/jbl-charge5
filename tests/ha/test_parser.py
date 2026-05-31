from custom_components.jbl_charge5.protocol import decode_frame
from custom_components.jbl_charge5.parser import SpeakerInfo, parse_speaker_info

# Real burst captured from a JBL Charge 5 on 2026-05-31 (battery was 100%).
REAL_FRAMES_HEX = [
    "aa120f00c10c4a424c204368617267652035",  # name "JBL Charge 5"
    "aa120400422040",                          # model 0x2040
    "aa1203004301",                            # color 0x01
    "aa1203004464",                            # battery 0x64 = 100
    "aa1203004600",                            # channel 0x00
    "aa1203004701",                            # source state 0x01 (connected)
    "aa12080048aabbccddeeff",                  # MAC aa:bb:cc:dd:ee:ff
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
