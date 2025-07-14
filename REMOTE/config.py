# L.A.U.R.A. REMOTE Ver.2.1 - config.py

# === LOGGING ===
DEBUG_ENABLED = False  # Set to True to enable debug prints

# === DEVICE UIDs ===
DEVICE_UID = 0

# === GPIO Pins ===
BUTTON_PIN = 0
LED_PIN = 35

# === OLED Display Configuration ===
VEXT_CTRL_PIN = 36
RST_OLED_PIN = 21
I2C_SCL_PIN = 18
I2C_SDA_PIN = 17

OLED_WIDTH = 128
OLED_HEIGHT = 64

# === Comm Timeouts ===
HEARTBEAT_TIMEOUT_SEC = 16  # Defines when consider the DEVICE lost

# === LoRa Configuration ===
LORA_CONFIG = {
    'freq_khz': 915000,        # 915 MHz for US
    'sf': 10,                  # Maximum spreading factor for range
    'bw': 125,                 # Narrow bandwidth for range (125 kHz)
    'coding_rate': 5,          # Coding rate 4/5 for better error correction
    'output_power': +14,       # Transmission power fixed at 14 dBm
    'implicit_header': False,  # Explicit header mode (default)
    'crc_on': True,            # Enable CRC for error detection
    'syncword': 0x12,          # Sync word for private networks
    'preamble_len': 12,        # Longer preamble for better signal detection
    'rx_boost': True,          # Enable RX boost for better receive sensitivity
}