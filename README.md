L.A.U.R.A. Cam

LoRa-powered Action camera Ultra-long distance Remote Actuator

L.A.U.R.A. Cam is a remote control system designed to trigger GoPro camera recording from long distances using LoRa communication. It's not desined to replace the GoPro App entierly (it doesn't allow to see a preview neither change settings for now) but to overcome the distance limitations imposed by the BLE protocol in thoese situations where is not safe or possible to stay close to the GoPro when the anction starts.

System Overview
  The system is built around two devices:

  Controller – Communicates with the GoPro via BLE, receives LoRa trigger/wake-up commands, and sends back status updates

  Remote – The physical remote control used to send triggers, request status updates, and wake up cameras from standby over LoRa

  This design allows users to control cameras far beyond the typical BLE/WiFi range, while still ensuring recording confirmation and camera feedback.

BLE Camera Control
The Controller uses BLE to wake up the GoPro, send commands, and query current recording state.

Low Power Architecture
Optimized for Heltec LoRa (ESP32) boards, supporting sleep mode and wake-up features for minimal power draw.

Remote OLED Display
Status of each camera is shown on the Remote’s screen: signal, recording, alerts, and health indicators.

Multi-device Support
Control multiple cameras with unique IDs and get independent feedback from each.

GoPro Wake-Up
Send BLE wake signals to GoPros in power-save mode — useful when remote cameras are in sleep to conserve battery.

Hardware Compatibility

Tested and optimized for:

✅ Heltec Wireless Stick V3 for the Controller

✅ Heltec LoRa 32 V3 for the Remote

✅ GoPro cameras compattible with OpenGoPro API

⚙️ Performance Tips
To improve memory usage and execution speed on MicroPython:

Compile all .py modules into .mpy using mpy-cross

Upload the .mpy files to your device

This is especially recommended for MicroPython on ESP32 boards with limited RAM.

Project Status

Work in Progress – Core functionality is stable and actively tested

Current capabilities:

✔️ Reliable long-range recording triggers

✔️ BLE camera wake-up

✔️ Real-time recording feedback

✔️ Multi-camera support

✔️ OLED-based UI with blinking device indicators and connection health

Planned improvements:

🔋 Enhanced power management (deep sleep cycles)

📊 Expanded status reporting (battery, temperature, etc.)

🔄 Simplified configuration for presets and camera groups
