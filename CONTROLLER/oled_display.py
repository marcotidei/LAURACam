# L.A.U.R.A. CONTROLLER Ver.2 - oled_display.py
import config
from machine import Pin, SoftI2C
import ssd1306
import utime as time

display_power = False
VEXT_CTRL = None
RST_OLED = None
i2c = None
display = None

def init_display_hardware():
    global VEXT_CTRL, RST_OLED, i2c, display, display_power

    if display_power:
        return

    if not config.USE_DISPLAY:
        return  # Don't initialize if disabled in config

    VEXT_CTRL = Pin(config.VEXT_CTRL_PIN, Pin.OUT)
    VEXT_CTRL.value(0)  # Power ON
    time.sleep(2)

    RST_OLED = Pin(config.RST_OLED_PIN, Pin.OUT)
    RST_OLED.off()
    RST_OLED.on()

    i2c = SoftI2C(scl=Pin(config.I2C_SCL_PIN), sda=Pin(config.I2C_SDA_PIN))
    display = ssd1306.SSD1306_I2C(config.OLED_WIDTH, config.OLED_HEIGHT, i2c)

    display_power = True

def update_display(row1, row2):
    if not display_power:
        return
    display.fill(0)
    display.text(row1, 0, 6)
    display.text(row2, 0, 20)
    display.show()

def shutdown_display():
    global display_power, VEXT_CTRL, RST_OLED, i2c, display
    if display_power and VEXT_CTRL is not None:
        if display is not None:
            display.fill(0)
            display.show()
        VEXT_CTRL.value(1)  # Power OFF
        display_power = False
        RST_OLED = None
        i2c = None
        display = None

def power_on_display():
    init_display_hardware()
    
if config.USE_DISPLAY:
    init_display_hardware()

