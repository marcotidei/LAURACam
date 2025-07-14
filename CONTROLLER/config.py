# L.A.U.R.A. CONTROLLER Ver.2 - config.py
from commands import Settings

# === LOGGING ===
DEBUG_ENABLED = True  # Set to True to enable debug prints

# === DEVICE UIDs ===
DEVICE_UID = 3
REMOTE_UID = 0

# Resolution Options:
# Settings.Resolution.RES_1080p
# Settings.Resolution.RES_2_7K
# Settings.Resolution.RES_2_7K43
# Settings.Resolution.RES_4K
# Settings.Resolution.RES_4K43
# Settings.Resolution.RES_5_3K
RESOLUTION = Settings.Resolution.RES_4K43

# Framerate Options:
# Settings.Framerate.FPS_30
# Settings.Framerate.FPS_60
# Settings.Framerate.FPS_120
# Settings.Framerate.FPS_240
FRAMERATE = Settings.Framerate.FPS_60

# Field of View (FOV) Options:
# Settings.VideoLens.Wide
# Settings.VideoLens.Narrow
# Settings.VideoLens.Superview
# Settings.VideoLens.Linear
# Settings.VideoLens.MaxSuperview
# Settings.VideoLens.LinearLevel
FOV = Settings.VideoLens.Wide

# === Feature Flags ===
USE_DISPLAY = True
ALWAYS_ON = False

# === Timings (seconds) ===
INACTIVITY_TIMEOUT = 300
COMMAND_DELAY = 0.5
STATUS_QUERY_INTERVAL = 5
DISPLAY_TIMEOUT = 30

# === GPIO Pins ===
BUTTON_PIN = 0

# === OLED Display Configuration ===
VEXT_CTRL_PIN = 36
RST_OLED_PIN = 21
I2C_SCL_PIN = 18
I2C_SDA_PIN = 17

OLED_WIDTH = 64
OLED_HEIGHT = 32

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
