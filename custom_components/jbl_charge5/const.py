"""Constants for the JBL Charge 5 integration."""

DOMAIN = "jbl_charge5"

# Poll interval (seconds). The speaker answers a Speaker-Info request quickly;
# polling every 90s keeps battery fresh without hammering the BLE link.
SCAN_INTERVAL_SECONDS = 90

# Custom GATT service/characteristics (verified on real hardware).
SERVICE_UUID = "65786365-6c70-6f69-6e74-2e636f6d0000"
WRITE_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0002"
NOTIFY_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0001"
