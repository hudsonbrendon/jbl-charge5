# JBL Portable BLE protocol, as used for the JBL Charge 5 (PID 2040)

Source: static analysis of JBL Portable 6.9.33 (`com.harman.ble.jbllink`, APK
SHA-256 `d007d54863f43d4ba0cb1158cf715718f8755b48aea7dfbf1f0430eb7d5ef14f`),
decompiled with jadx; nothing was executed. Path prefix `S/` = the decompiled
`com/harman/` package. Which of these the speaker really answers is in
[PROTOCOL.md](PROTOCOL.md#live-verification-2026-10-24). `[obs]` = read directly in the code, `[inf]` = my inference.

---

## 0. How the app classifies the Charge 5

`assets/product_list_config.json:567-575` [obs]:

```json
{"deviceName":"JBL Charge 5","pid":"2040","platform":"Vimicro","protocol":"PROTOCOL_BLE",
 "features":["FEEDBACK_SUPPORT","EQ_BALANCE_SUPPORT"]}
```

What follows from that:
- **No `PROTOCOL_4`.** `DeviceUtils.isSupportFeatureProtocol4()` (S/sdk/utils/DeviceUtils.java:334) checks this feature list, so every `PortableControl` method takes the "legacy" `0xAA`-frame branch (S/sdk/protocol4/cmd/PortableControl.java:121-960). The P4 path (`BaseP4Command`/`AssembleCmd`) is **not used** for Charge 5.
- Platform "Vimicro" means `isVimicroOrActionsProduct` is true. That turns on the Vimicro dev-info parser, battery >=95 % shown as 100 %, and the mic-status query.
- The JSON has no `PRESET_EQ`, `7_BANDS_EQ`, `PLAY_TIME_BOOST`, `SQ_SUPPORT`, `AURACAST_SUPPORT`, `AUTO_POWER_OFF_SUPPORT`, `MFB_SUPPORT`, `HFP_SUPPORT`, `DEVICE_USAGE_SUMMARY_SUPPORT`, `BATTERY_NOTIFICATION_SUPPORT`, `LED_*`, `BRIGHTNESS*` or `EQ_OUTDOOR_INDOOR_SUPPORT` entry.
- `assets/AppConfig.json` [obs]: service `65786365-6C70-6F69-6E74-2E636F6D0000`, rx/notify `...0001`, tx/write `...0002`, CCCD `2902`, `commandTimeout` 2000 ms, `maxRewriteCount` 3.

---

## 1. Framing

### 1.1 TX (app to speaker), short form [obs]
`S/sdk/command/BaseCommand.java:154-164`:
```
AA <opcode> <len> <payload[len]>
```
- `identifier` is always `0xAA` (BaseCommand.java:82).
- `len` = `payload.length`, or `0` when the payload is null (`Command.DefaultImpls.getPayloadLen`, S/sdk/Command.java). **The length byte is always sent**, so a no-payload request is 3 bytes, e.g. `AA 11 00`.
- There is no checksum, no sequence number and no trailer.

### 1.2 Long form (16-bit length) [obs]
`BaseCommandForLongBytes.java:36-46`, `ReqAdvancedEQCommand.data()`, `SetAdvancedEQCommand.data()`:
```
AA <opcode> <lenHi> <lenLo> <payload>
```
- TX: used only by `0x98` REQ_ADVANCE_EQ and `0x97` SET_ADVANCE_EQ (not used for Charge 5).
- RX: the receive path (S/sdk/impl/connect/GattControllerImpl.java:456-464) treats a notification as long-form if `len(value) > 127` or `opcode ∈ LONG_BYTES_COMMAND = {0x94, 0x96, 0x99}` (PacketFormat.java:161-167). The payload is then taken from byte 4 to the end.

### 1.3 RX parsing [obs]
`BaseCommand(byte[])` (BaseCommand.java:86-106):
- `opcode = buf[1]`, `len = buf[2]`, `payload = buf[3 : 3+min(len, n-3)]`.
- **One notification = one frame.** The app does not reassemble frames or split coalesced frames (GattControllerImpl.java:427-490). Notifications shorter than 3 bytes are dropped (line 435).

### 1.4 Transport details [obs]
- Writes use the default write type (with response) for PROTOCOL_BLE. `WRITE_NO_RESPONSE` (type 1) is used only for GATT-over-BR/EDR (GattControllerImpl.java:784-786).
- After service discovery the app enables notify on `...0001`. For non-P4 BLE devices it then calls `requestMtu(512)` after 800 ms (GattControllerImpl.java:806-816).
- The app sends commands **one at a time**. `GattControllerImpl.sendingCommandList` waits until the outstanding command's `responseCommands` list is empty or the timeout fires.
- An incoming frame that the pending command does not claim still goes to `CommandProcessor.processCommand(dev, frame, null)` (GattControllerImpl.java:479-484). **That is the unsolicited-notification path.**

### 1.5 Generic ACK and NAK [obs]
- **ACK**: `AA 00 02 <echoed opcode> <status>`, where status `00` = success. Examples: `SetFeedbackToneCommand.onReceive` checks `cmd==0 && p[0]==0x67 && p[1]==0`; SetDeviceName/SetChannel check `p[0]==0x15`; SetMFB `0x32`; SetHFP `0x70`; SetEQMode `0x63`; SetSimpleEq `0x6E`.
- **NAK**: `AA EE <len> <rejected opcode> ...` = RET_UNSUPPORTED_CMD. It is only handled explicitly for 0x7A (ReqSerialNumberCommand: `cmd==-18 && p[0]==122`). [inf] Treat 0xEE as "unsupported" for any opcode.
- **App ACK**: `SET_APP_ACK 0x01` with payload `[<opcode being acked>, 00]` (SetAppAckCommand: `AA 01 02 12 00`). The app sends it after each DEVICE_INFO **only for CSR/QCC products** (NewDashboardActivityViewModel.java:1429-1435), so **not for Charge 5**. The same 0x01 opcode is also used for "clear analytics" (§2.10).

---

## 2. Opcodes

Hex values come from PacketFormat.java (Java signed bytes converted). "Builder" = class in S/sdk/command/.

### 2.1 Device info (0x11 / 0x13 → 0x12), SET_DEV_INFO 0x15
| Request | Bytes | Builder |
|---|---|---|
| REQ_DEV_INFO (all tokens) | `AA 11 00` | GetDevInfoCommand (no payload) |
| REQ_DEV_INFO_TOKEN (one token) | `AA 13 02 <devIdx=00> <token>` | ReqBatteryCommand (token 0x44), ReqChannelCommand (0x46), ReqMicStatusCommand (0x53), ReqBtAddressCrc16Command (0x4A) |
| SET_DEV_INFO name | `AA 15 <3+n> <devIdx> C1 <n> <UTF-8 name, truncated to 16 chars>` | SetDeviceNameCommand; ACK `00 [15 00]` |
| SET_DEV_INFO channel | `AA 15 03 <devIdx> 46 <0=none/stereo,1=L,2=R>` | SetChannelCommand; ACK `00 [15 00]` |
| SET_DEV_INFO stereo lock | `AA 15 03 <devIdx> 49 <b>` | SetChannelLockCommand |

**Response RET_DEV_INFO `AA 12 <len> <devIdx> <TLV tokens...>`** (CommandProcessor.processDeviceInfoRes, CommandProcessor.java:1572-1601):
- `payload[0]` is the device index (0 = this speaker, 1 = secondary/TWS).
- Token value lengths come from `processVimicroDeviceInfoRes` (1759-1980):

| token | len | meaning |
|---|---|---|
| 42 | 2 | PID (hex string, e.g. `20 40`) |
| 43 | 1 | model/colour id ("mid", key into productImageUrls: 00/01 black, 02 red, 03 blue, 04 white, 05 green, 07 grey, 09 teal, 10 pink, 12 TML, 13 camo) |
| 44 | 1 | **battery: bit7 = charging, bits0-6 = %**. `>=128 → level = b-128, charging=true` (CommandProcessor.java:1888-1904, also 1667). For Vimicro, the app shows level >= 95 as 100. |
| 45 | 1 | linked device count (role: 0 → NORMAL) |
| 46 | 1 | active channel 0 none / 1 L / 2 R |
| 47 | 1 | audio source 0 NO_AUDIO, 1 BT_A2DP, 2 AUX_IN, 3 RECEIVER_PLAYING, 4 FM, 5 DAB (S/sdk/utils/AudioSource.java:13-19) |
| 48 | 6 | MAC (big-endian as printed) |
| 49 | 1 | stereo lock |
| 4A | 2 | CRC16 of BT MAC (not in the Vimicro parser) |
| 4C | 1 | Auracast support 0/1 |
| 4D | 4 | secondary FW version |
| 4F / 51 | 1 | LL-stereo connected |
| 50 | 4 | DAB FW version |
| 53 | 1 | mic connected 0/1 |
| C1 | 1+n | name: `<n> <bytes>` |
| C2 | 1+n | serial: `<n> <ASCII>` |

Parser quirk [obs]: `isDevInfoFromVimicro()` (1603-1606) returns true when fewer than 7 known token ids appear in the hex string **or** the payload is ≤ 18 bytes. Otherwise the app uses `processNormalDeviceInfoRes` (1608-1725), which peels fixed-size tokens from the **end** of the payload in the order 48, 47, 46, 45, 44, 43, 42, with the name before them. A HA integration should just parse it as TLV using the lengths above.

Unsolicited [obs + inf]: `processCommand` handles 0x12 with no pending request (CommandProcessor.java:290-295). The dashboard refreshes the battery on any DEVICE_INFO message (NewDashboardActivityViewModel.java:812-825) and only actively requests battery in `onResume` (NewDashboardActivity.java:4588). That suggests the speaker pushes 0x12 when battery, source or charging change.

### 2.2 Firmware version, serial number
- **REQ_VER** `AA 41 00` → **REP_VER `AA 42 <n> <bytes>`** (ReqVerCommand). Decoding [obs]: hex-encode the payload, split into 2-char chunks, `Integer.parseInt(chunk)` as **decimal**, join with ".". In effect each byte is BCD: `03 05 01` → "3.5.1". A nibble ≥ A would throw in the app. CommandProcessor.formatVersion (2027-2059) is a variant that ASCII-decodes chunks that are digits.
- **REQ_SERIAL_NUMBER** `AA 7A 00` → **RET `AA 7B <n> <ASCII>`**. All-zero → "0000000000000000". A `0xEE [7A]` reply means unsupported (ReqSerialNumberCommand.onReceive).
- DFU version `AA 4A 00` → `AA 4B <n> <b0 b1 b2>`, shown as "hh.hh.hh" from the hex (ReqDfuVerCommand). This is an OTA path.

### 2.3 Feedback tone (Charge 5: yes)
- REQ `AA 65 00` → REP_FEEDBACK_STATUS `AA 66 01 <s>`.
- SET `AA 67 01 <s>`, where s = `01` on, `00` off (callers ProductInformationFragment.java:1019/1035, NewDashboardActivity.java:4491/4500) → ACK `AA 00 02 67 00`.
- 0x66 is also handled unsolicited (CommandProcessor.java:396-400).

### 2.4 Simple EQ, "EQ_BALANCE" (Charge 5: yes, this is its EQ)
- REQ_SIMPLE_EQ `AA 6C 01 00` (ReqSimpleEqCommand).
- RET_SIMPLE_EQ `AA 6D <len> <scope> <activeCategoryId> { <categoryId> <nParams> { <type> <value> }*n }*` (parseEQPayload).
  - `scope` = UI half-range. The slider has `2*scope+1` steps, **value is a signed int8 in [-scope, +scope]** (EQFragment.java:271,343).
  - categoryId: `0x01` = default/"JBL Signature" (EQ off), `0xC1` = custom 1, `0xC2` = custom 2.
  - Param type: 1 bass, 2 mid, 3 treble (SimpleEQSettings.java constants).
- SET_SIMPLE_EQ `AA 6E <2+2n> <categoryId> <n> {<type> <value>}*` (SetSimpleEqCommand).
  - The app sends `01 00` (default, no params) or `C1 03 01 bb 02 mm 03 tt` (EQFragmentViewModel.java:102-121).
  - Reply: ACK `00 [6E 00]` or a 0x6D frame.
- Other categoryIds defined but unused by the UI: PartyBoost presets 0 Balance, 1/2 BassBoost, 3 Vocal, 4 Metal, 5 Classical.
- [inf] There is no unsolicited 0x6D handler in processCommand.

### 2.5 EQ mode (0x61/0x63 → 0x62/0x64), outdoor/indoor
- Payload: `AA 61 00` → `AA 62 01 <mode>`. SET `AA 63 01 <mode>` → ACK `[63 00]`.
- 0x64 is an unsolicited "EQ changed" notification (CommandProcessor.java:390-395).
- Gated by `EQ_OUTDOOR_INDOOR_SUPPORT` (BoomBox only). **Not Charge 5.**

### 2.6 Advanced EQ (0x98/0x97 → 0x99), long frames
- `AA 98 00 00` → `AA 99 LL LL ...`.
- Gated by PRESET_EQ (ConnectingActivityViewModel.java:~1559-1573, NewDashboardActivityViewModel.java:1453). **Not Charge 5.**

### 2.7 Bass volume (0x77 → 0x78; 0x76 set)
- `AA 77 00` → `AA 78 01 <int>` (handled in CommandProcessor.java:419-423).
- **No UI code ever instantiates ReqBassVolumeCommand, and no Set builder exists.** Dead code for every device.

### 2.8 HFP (0x68/0x70 → 0x69), MFB (0x33/0x32 → 0x34)
- REQ `AA 68 00` / `AA 33 00`. SET `AA 70 01 <b>` / `AA 32 01 <b>` → ACK.
- 0x69 and 0x34 are also handled unsolicited.
- Only for products with HFP_SUPPORT / MFB_SUPPORT (CSR: Charge 3, Flip 4, Xtreme 2, BoomBox 1, Pulse 3). **Not Charge 5.**

### 2.9 Link mode / PartyBoost (Charge 5: yes)
- SET_LINK_MODE `AA 6A 01 <m>`: m = 0 off, 1 PartyBoost (non-Auracast), 2 Auracast.
- Response RET_LINK_MODE `AA 6B 01 <role>`, with role 0 NORMAL, 1 MASTER, 2 SLAVE, 3 STANDBY (DeviceRole.java:14-20).
- Code path: SetLinkModeCommand → `PortableControl.changeAuraCastMode`, which uses 0x6A for non-P4 devices (PortableControl.java:277-283).
- PartyBoostViewModel.turnOnOffPartyBoost (725-734) names Charge 5 explicitly and sends 1 (PartyBoost) or 0 to turn off.
- After 0x6B with role ≠ NORMAL, the app sends ROLE_CHECK `AA 17 00` → ROLE_INFO `AA 16 01 <role>` (PartyBoostViewModel.java:565; RoleCheckCommand).
- 0x16 is also handled unsolicited (CommandProcessor.java:315-320).
- 0x22 NOTIFY_LINK_DEV_DROP is unsolicited (only acted on for TWS).

### 2.10 Analytics (0x81 → 0x82), clear via 0x01
- REQ_ANALYTICS_DATA `AA 81 00` → RET_ANALYTICS_CMD `AA 82 <len> <u16 BE>*` (ReqAnalyticsCommand parses the hex string from offset 6 in 4-char chunks).
- Charge 5 uses this short (non-BR/EDR) variant. `isSupportAnalyticsBrEdr` = Pulse5, or PID string > "206d" (DeviceUtils.java:172-177), and "2040" < "206d".
- **Field map for Charge 5** (shared with BoomBox 2 and Xtreme 3), from ConnectingActivityViewModel.java:2080-2120 (`processDeviceAnalytics`) and the Firebase keys at 2550-2610:

| idx | field | Firebase key |
|---|---|---|
| 0 | jblConnect (count of app connections) | di_dev_jbl_connect |
| 1 | durationJBLConnect | di_dev_duration_jbl_connect |
| 2 | criticalTemperature (count) | di_dev_critical_temperature |
| 3 | powerBank (power-bank use) | di_dev_power_bank |
| 4 | playtime | di_dev_play_time |
| 5 | playtimeInBattery | di_dev_play_time_in_battery |
| 6 | chargingTime | di_dev_charging_time |
| 7 | powerONCount | di_dev_power_on_count |
| 8 | durationPowerONOFF | di_dev_duration_power_on_off |
| 9 | playtimeInAux | di_dev_play_time_in_aux |
| 10 | pdChargingTime (USB-PD) | di_dev_pd_charging_time |
| 11 | popularVolumeUsage | di_dev_popular_volume_usage |
| 12 | popularVolumeLevel | di_dev_popular_volume_level |

- Units are not converted anywhere in the app [obs]. [inf] Durations are probably minutes, by analogy with 0x9E below.
- **The app clears the counters after every read** with `AA 01 02 82 00` (ClearDeviceAnalyticsCommand; ConnectingActivityViewModel.java:221-226). The values are therefore deltas since the last app read. **HA should not send the clear** if it wants to keep counters for the official app. Also expect small numbers if the phone app is in use.
- When it is sent: only if the PID is in a remotely downloaded AWS analytics list (`DeviceUtils.isSupportAws`, list set at JBLConnectBaseApplication.java:285-302; trigger ConnectingActivityViewModel.java:1496-1505). Whether 2040 is on that list can't be determined offline.
- 0x82 is also logged when unsolicited (CommandProcessor.java:414-417).
- BR/EDR variants (not Charge 5): 0x93 → 0x94 and 0x95 → 0x96 (long frames); clear `AA 01 02 94 00`.

### 2.11 Device usage summary (0x9D → 0x9E)
- `AA 9D 02 0C 0B` → `AA 9E <len> { <id> <len=4> <u32 BE> }*` (ReqBatteryStatusCommand; OneTouchViewModel.processDeviceSummaryUsage 143-183).
  - id 0x0B = total power-on duration.
  - id 0x0C = total playback time.
  - Both are in **minutes**: the UI shows `value/60` hours (DeviceUsageSummaryFragment.java:128-190).
- Gated by DEVICE_USAGE_SUMMARY_SUPPORT (PortableControl.getPlaybackTimeAndPowerOnTimeSummary 696-704). **Not enabled for Charge 5.** [inf] Worth probing: an `0xEE` reply means unsupported.

### 2.12 Player settings 0xA8 / 0xA7 → 0xA6 (play, pause, skip, volume)
- **REQ** `AA A8 03 01 02 03` (ReqPlayerSettingsCommand).
- **SET** `AA A7 03 <id> 01 <value>` (SetPlayerSettingsCommand: payload `{id, 1, value}`).
- **RET** `AA A6 <len> { <id> <len=1> <value> }*` (PartyBoostViewModel.setDevicePlayerSettingStatus 644-682).

| id | meaning | SET value | RET value |
|---|---|---|---|
| 01 | play/pause | app sends **current** isMusicPlaying (1 if playing, 0 if paused). [inf] The toggle semantics are muddled; MusicPlayCard flips the local flag first (MusicPlayCard.java:270-292). Probe both. | 0 = paused, ≠0 = playing |
| 02 | track skip | 00 = previous, 01 = next (PartyBoostViewModel.java:877-904) | ignored by app |
| 03 | volume | 0..**32** (SeekBar `android:max="32"`, res/layout/play_music_details_layout.xml:16) | current volume |

- Used only in the PartyBoost tab's MusicPlayCard: getMusicPlayStatus on BLE connect and when the phone volume changes (PartyBoostFragment.java:4753-4758).
- No PID/feature gate is visible on this path, and Charge 5 is a PartyBoost device [obs]. Whether Charge 5 firmware answers 0xA8 is **unknown statically**. [inf] Send `AA A8 03 01 02 03` and treat `0xA6` as supported, `0xEE` or a timeout as not supported.
- `MessageID.PLAYER_STATUS (1511)` is **never produced** by any code. `S/sdk/control/PlayerControl.java` (getPlayerInfo/setVolume/setPlayerStatus) has **no implementation**.
- VolumeChangeObserver only reads and writes the **phone's** `AudioManager.STREAM_MUSIC`.
- There is no MediaSession or AVRCP usage in the app. AVRCP volume is the A2DP source's job.

### 2.13 Playtime boost (0xB1/0xB2 → 0xB3)
- `AA B1 00` → `AA B3 01 <s>`. SET `AA B2 01 <s>` → `AA B3 01 <s>`.
- Gated by PLAY_TIME_BOOST / PRESET_EQ+7-band (ConnectingActivityViewModel.java:~1571-1577). **Not Charge 5.**

### 2.14 SQ status (0xAF → 0xB0)
- `AA AF 01 <0|1>` → `AA B0 01 <s>`. This is Auracast "sound quality" mode. Gated by SQ_SUPPORT. **Not Charge 5.**

### 2.15 Vendor codes / disabled features (0xAB → 0xAD), control feature 0xAC
- `AA AB 00` → `AA AD <len> { <type> <n> <bytes[n]> }*`, with type 1 = vendor (chipset) codes and type 2 = disabled features.
- `AA AC <n> <actions>` → 0xAD. Actions: 0 = recover all, 1/2/3 = recover playback/EQ/PartyBoost, 0x11/0x12/0x13 = disable the same features (PacketFormat.java:18-50).
- This is counterfeit-chip detection. It only runs when a remote "UnSupportCodeConfigs" entry exists for the PID and FW is newer than a configured version (NewDashboardActivityViewModel.java:2078-2120). [inf] Avoid.

### 2.16 Identify (0x31), disconnect (0x35)
- IDENT_DEV `AA 31 01 <devIdx>`. No expected response (IdentificationCommand), so fire-and-forget.
  - The dashboard "identify" button (NewDashboardActivityViewModel.java:1694-1703) is available to all devices.
- DISCONNECT_DEVICE `AA 35 00` → ACK. Only used by the OTA code.
- 0x02 RET_DEV_BYE_BYE is unsolicited (logged only, CommandProcessor.java:297-300).

### 2.17 Light / brightness / LED
- Opcodes: 0x71/0x73 → 0x72; 0x56/0x55 → 0x57; 0x8B/0x8A → 0x8C; 0x51-0x5A; 0x83-0x92.
- Gated by LED_SUPPORT / BRIGHTNESS_SUPPORT / LED_PACKAGE_SUPPORT (Pulse family). **Not Charge 5.**

### 2.18 Auracast group (0xA1/0xA0 → 0xA2), LE audio (0xA4/0xA3 → 0xA5), radio (0xB4/0xB6 → 0xB5), screen (0xB7/0xB9 → 0xB8)
- Only for AURACAST_SUPPORT / LE_AUDIO / RADIO_SUPPORT / SCREEN_DISPLAY devices. **Not Charge 5.**

### 2.19 Authentication (0xF1 → 0xF2)
- `AA F1 02 <action> <timeout>`: action 1 = Play (start), 2 = Cancel; timeout = 5 (0 on cancel).
- Reply `AA F2 01 <r>`: r 0 = Succeed, 1 = Fail (ReqAuthenticationCommand; AuthenticationResult.java).
- Only sent in HomeViewModel's BLE-only flow for **radio devices (Tuner 3)**:
  - HomeFragment.java:835 `getBleRadioDeviceList()` → `connectBleDevice`
  - HomeViewModel.java:736-748
  - stored as `PREFERENCE_KEY_TUNER_BLE_AUTHENTICATED`
- **Not required for Charge 5.** No other command checks `isAuthVerified` before sending.

### 2.20 Auto power-off / standby
- `DeviceStatusControlImpl.getAutoPowerOffStatus/setAutoPowerOffStatus` are **empty stubs** (DeviceStatusControlImpl.java:52-79).
- `PortableControl.get/setAutoStandbyStatus` only act for PROTOCOL_4 (PortableControl.java:196-200, 332-341, via P4 `DeviceFeature.AutoStandby`).
- **There is no legacy-frame opcode for auto-off. Not available for Charge 5 through this app.**

### 2.21 DFU/OTA (for completeness, not detailed)
- 0x43 REQ_DFU_START, 0x44 SET_DFU_DATA, 0x45 RET/NOTIFY DFU status, 0x47 NOTIFY_DFU_CANCEL, 0x4A/0x4B DFU version, 0x4D/0x4C trigger update. Code in S/sdk/impl/ota/UpgradeFirmwareFileUtils.java.

### 2.22 Unsolicited frames handled by `CommandProcessor.processCommand` (282-527)
- 0x02, 0x12, 0x16, 0x22, 0x34, 0x52, 0x54, 0x57/0x58, 0x5A
- 0x62/0x64, 0x66, 0x69, 0x72, 0x78, 0x82, 0x4B, 0x4C
- 0x87, 0x88, 0x8C, 0xA2, 0xB0, 0xB3, 0xB5, 0xB8, 0xF2
- 0x45 (DFU) is skipped here.

---

## 3. What the app actually does for Charge 5

Connect sequence (ConnectingActivityViewModel.java, non-Pulse2 branch, around 1549-1745) [obs]:
1. (Optional) analytics `AA 81 00`, then clear `AA 01 02 82 00`, only if the PID is in the remote AWS list (1496-1505).
2. `AA 6C 01 00` simple EQ (EQ_BALANCE_SUPPORT, 1553-1560).
3. `AA 65 00` feedback tone (FEEDBACK_SUPPORT, 1698-1702).
4. `AA 13 02 00 53` mic status (Vimicro, 1704-1708). [inf] Charge 5 has no mic, so the reply is likely empty, 0 or 0xEE.
5. `AA 11 00` device info (PortableControl.getDeviceInfo, ~1724).
6. `AA 7A 00` serial (1730), `AA 41 00` firmware if unknown (1733-1736).
7. Dashboard onResume: `AA 13 02 00 44` battery (NewDashboardActivity.java:4588 → PortableControl.getBatteryStatus 121-127), `AA 13 02 00 53` mic.
8. Party tab: `AA 6A 01 01/00` (PartyBoost on/off), `AA 17 00`, and possibly `AA A8 03 01 02 03` plus 0xA7 controls.

| Feature | Opcode(s) | Charge 5? | Evidence |
|---|---|---|---|
| Device info, battery %, charging bit, source, channel, MAC, name | 0x11/0x13 → 0x12 | **Yes** | product_list_config.json:567; CommandProcessor.java:1888-1904; PortableControl.java:121-127 |
| Firmware version | 0x41 → 0x42 | **Yes** | ConnectingActivityViewModel.java:1733-1736; PortableControl.java:169-176 |
| Serial number | 0x7A → 0x7B | **Yes** | ConnectingActivityViewModel.java:1730; PortableControl.java:217-224 |
| Rename | 0x15 (C1) | **Yes** (non-P4 path) | PortableControl.changeName 302-311; HmRenameDialogFragment.java:243 |
| Stereo channel L/R | 0x15 (46) | Yes (stereo pairing) | DeviceStatusControlImpl.setAudioChannel |
| Feedback tone | 0x65/0x67 → 0x66 | **Yes** | FEEDBACK_SUPPORT; ConnectingActivityViewModel.java:1698-1702 |
| Simple EQ bass/mid/treble | 0x6C/0x6E → 0x6D | **Yes** | EQ_BALANCE_SUPPORT; ConnectingActivityViewModel.java:1553; NewDashboardActivity.supportEQ / initEQFragment 4693 |
| PartyBoost link mode | 0x6A → 0x6B, 0x17 → 0x16 | **Yes** | PartyBoostViewModel.java:725-734 (explicit isCharge5Pid) |
| Identify | 0x31 | **Yes** | NewDashboardActivityViewModel.java:1694-1703 |
| Mic status token 0x53 | 0x13 → 0x12 | Sent (Vimicro), [inf] meaningless | ConnectingActivityViewModel.java:1704-1708 |
| Analytics | 0x81 → 0x82 (+ clear 0x01) | Conditional (remote AWS list) | ConnectingActivityViewModel.java:1496-1505, 2080-2120 |
| Player play/pause/skip/volume | 0xA8/0xA7 → 0xA6 | Code path reachable in Party tab; FW support unknown | PartyBoostViewModel.java:845-918 |
| Usage summary (power-on/playback minutes) | 0x9D → 0x9E | No (feature absent) | PortableControl.java:696-704 |
| Playtime boost | 0xB1/0xB2 → 0xB3 | No | feature list |
| SQ (Auracast) | 0xAF → 0xB0 | No | feature list |
| Advanced/preset EQ | 0x98/0x97 → 0x99 | No | feature list |
| EQ mode outdoor/indoor | 0x61/0x63 → 0x62 | No | feature list |
| Bass volume | 0x77 → 0x78 | No (dead code everywhere) | no `new ReqBassVolumeCommand` |
| HFP / MFB | 0x68/0x70, 0x33/0x32 | No | feature list |
| Light / brightness | 0x71-0x73, 0x55-0x57 | No | feature list |
| Auto power-off / standby | (P4 only) | No | DeviceStatusControlImpl.java:52-79; PortableControl.java:196,332 |
| Vendor codes / feature control | 0xAB → 0xAD, 0xAC | Only if remote blacklist config | NewDashboardActivityViewModel.java:2078-2120 |
| Authentication | 0xF1 → 0xF2 | No (Tuner 3 BLE-only) | HomeViewModel.java:736-748 |

---

## 4. Direct answers

- **Media playback and volume over BLE:**
  - The only mechanism is player settings 0xA7/0xA8 → 0xA6: id1 play/pause, id2 prev(0)/next(1), id3 volume 0-32.
  - It lives in the PartyBoost "music card" and is not feature-gated per PID.
  - No other opcode, AVRCP or MediaSession code exists. PLAYER_STATUS (1511) is never emitted, and PlayerControl has no implementation.
  - Charge 5 firmware support is unverified and needs a live probe.
- **Auto power-off / standby:** P4-only. Nothing for Charge 5.
- **Charging state:** bit 7 of token 0x44 in RET_DEV_INFO (1 = charging). The remaining 7 bits are the percentage; the app shows ≥95 as 100 for Vimicro.
- **Battery health:** nothing in the app.
- **Usage stats:**
  - 0x9E gives power-on and playback **minutes** (u32), but is not enabled for Charge 5.
  - 0x82 analytics has 13 u16 counters for Charge 5 (table above), and the app clears them after reading.
- **Firmware version:** 0x42 payload bytes, each byte BCD/decimal, joined with ".".
- **Authentication:** not needed for Charge 5. 0xF1 is only used for the Tuner 3 BLE-only pairing flow.
