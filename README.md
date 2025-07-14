# L.A.U.R.A. Cam

## LoRa-powered Action-camera Ultra-long-distance Remote Actuator

**L.A.U.R.A. Cam** is a remote control system designed to trigger GoPro camera recording from long distances using LoRa communication.  
It is not designed to replace the GoPro App entirely (it does not support live preview or setting changes yet), but to overcome the distance limitations imposed by the BLE protocol—particularly in situations where it is not safe or possible to stay close to the GoPro when the action starts.

---

## System Overview

The system is built around two devices:

- **Controller** – Communicates with the GoPro via BLE, receives LoRa trigger/wake-up commands, and sends back status updates.
- **Remote** – The physical remote control used to send triggers, request status updates, and wake up cameras from standby over LoRa.

This design allows users to control cameras far beyond the typical BLE/Wi-Fi range, while still ensuring recording confirmation and camera feedback.

---

## BLE Camera Control

The Controller uses BLE to wake up the GoPro, send commands, and query the current recording state.

---

## Low Power Architecture

Optimized for Heltec LoRa (ESP32) boards, supporting sleep mode and wake-up features for minimal power draw.

---

## Remote OLED Display

The status of each camera is shown on the Remote’s screen, including signal strength, recording status, alerts, and health indicators.

---

## Multi-Device Support

Control multiple cameras with unique IDs and receive independent feedback from each.

---

## GoPro Wake-Up

Send BLE wake signals to GoPros in power-save mode — ideal when remote cameras are sleeping to conserve battery.

---

## Hardware Compatibility

Tested and optimized for:

- Heltec Wireless Stick V3 (Controller)  
- Heltec LoRa 32 V3 (Remote)  
- GoPro cameras that are compatible with the OpenGoPro API

---

## Performance Tips

To improve memory usage and execution speed on MicroPython:

- Compile all `.py` modules into `.mpy` using **mpy-cross**  
- Upload the compiled `.mpy` files to your device

---

## Project Status

**Work in Progress** – Core functionality is stable and actively tested.

### Current Capabilities

✔️ Reliable long-range recording triggers  
✔️ BLE camera wake-up  
✔️ Real-time recording feedback  
✔️ Multi-camera support  
✔️ Health feedback based on overheating and low temperature detection

### Planned Improvements

- Configuration menu for the Controller  
- Adjustable heartbeat interval  
- Remote access to check camera settings
