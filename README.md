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

### BLE Camera Control

The Controller uses BLE to wake up the GoPro, send commands, and query the current recording state — all wirelessly!

### Low Power Architecture

Optimized for Heltec LoRa (ESP32) boards, supporting sleep mode and wake-up features to minimize power draw.  
The system can also send BLE wake signals to GoPros in power-save mode — ideal when remote cameras are sleeping to conserve battery and reduce the risk of overheating.

At the moment, the controller assumes to be powered by an external source like a power bank. A future update to the Controller will add battery management similar to the one already implemented for the Remote.

### Remote OLED Display

The status of each camera is shown on the Remote’s screen, including signal strength, recording status, alerts, and health indicators.

### Multi-Device Support

Control up to 3 cameras with unique IDs and receive independent feedback from each.

---

## Hardware Compatibility

Tested and optimized for:

- Heltec Wireless Stick V3 (Controller)  
- Heltec LoRa 32 V3 (Remote)  
- GoPro cameras that are compatible with the OpenGoPro API

---

## Suggested 3D-Printable Cases

Here are some recommended enclosures to protect your L.A.U.R.A. Cam hardware:

- **Remote (Heltec LoRa 32 V3 – Slim Form Factor)**  
  [HT Slim Case on Printables.com](https://www.printables.com/model/936437-heltec-lora-32-v3-ht-slim-cases)

- **Controller – Using Heltec LoRa 32 V3 (Pocket Layout)**  
  [HT Pocket Case on Printables.com](https://www.printables.com/model/920722-heltec-lora-32-v3-ht-pocket-case)

- **Controller – Using Heltec Wireless Stick V3**  
  [Wireless Stick Lite V3 Case on Printables.com](https://www.printables.com/model/572273-heltec-wireless-stick-lite-v3-case/files)

### Note on Display Configuration

The **Wireless Stick V3** and the **LoRa 32 V3** have the same hardware features,  
**except for the OLED display**, which is **twice as large** on the LoRa 32 V3.

To ensure correct display behavior, set the pixel count in `config.py` based on your board:

#### Heltec LoRa 32 V3

```python
OLED_WIDTH = 128
OLED_HEIGHT = 64
```

#### Heltec Wireless Stick V3

```python
OLED_WIDTH = 64
OLED_HEIGHT = 32
```

---

## Performance Tips

To improve memory usage and execution speed on MicroPython:

- Compile all `.py` modules into `.mpy` using **mpy-cross**  
- Upload the compiled `.mpy` files to your device

---

## Project Status

**Work in Progress** – Core functionality is stable and actively tested.

### Current Capabilities

-  Reliable long-range recording triggers  
-  BLE camera wake-up  
-  Real-time recording feedback  
-  Multi-camera support  
-  Health feedback based on overheating and low temperature detection

### Planned Improvements

- Improve LoRa communication
- Add battery management for GoPro and Controller battery
- Configuration menu for the Controller
- Adjustable heartbeat interval
- Remote check of camera settings

## 🙏 Acknowledgements

Special thanks to [@KonradIT](https://github.com/KonradIT) and his project on goprowifihack [goprowifihack](https://github.com/KonradIT/goprowifihack) for the foundational work and inspiration behind this project.
