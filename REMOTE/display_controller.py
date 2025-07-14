# L.A.U.R.A. REMOTE Ver.2.1 - display_controller.py
import utime as time
import uasyncio as asyncio
from machine import Pin, SoftI2C
import ssd1306
from config import VEXT_CTRL_PIN, RST_OLED_PIN, I2C_SCL_PIN, I2C_SDA_PIN, OLED_WIDTH, OLED_HEIGHT 
from logger_utils import print_info, print_warning, print_error, print_debug

# Adjustable blink settings
BLINK_COUNT = 2
BLINK_INTERVAL_MS = 200

# Define lines position
LINE_HEIGHT = 12
LINE_SPACING = 12

# Heart Matrix (8x8)
heart_matrix = [
    [0, 1, 1, 0, 0, 1, 1, 0],
    [1, 1, 1, 0, 0, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0]
]

# OLED Power Setup
VEXT_CTRL = Pin(VEXT_CTRL_PIN, Pin.OUT)
VEXT_CTRL.value(0)  # Enable power to the display

# Reset OLED Display
RST_OLED = Pin(RST_OLED_PIN, Pin.OUT)
RST_OLED.off()
time.sleep(0.1)
RST_OLED.on()
time.sleep(0.1)

# Initialize I2C and OLED display with retries
i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
display = None
for attempt in range(5):
    try:
        display = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
        print_debug("OLED display initialized successfully.")
        break  # Exit loop if initialization succeeds
    except OSError:
        print_warning(f"Display not responding, retrying... ({attempt + 1}/{5})")
        time.sleep(0.5)

if display is None:
    raise RuntimeError("Failed to initialize OLED display after multiple attempts.")

# Function to blink the heart next to the last sender's device ID
async def blink_heart(last_sender_id):
    if last_sender_id is None:
        return  # Skip blinking if no sender ID

    # Calculate Y-position based on the last sender (device ID)
    heart_y_offset = 14 + (last_sender_id - 1) * LINE_SPACING  # Adjusted for proper spacing

    # Horizontal position is fixed for all devices
    heart_x_offset = 15  # Just to the right of the second column
    heart_width = 8
    heart_height = 8

    # Blink the heart at the calculated position
    for _ in range(BLINK_COUNT):
        # Draw the heart shape
        for y in range(heart_height):
            for x in range(heart_width):
                if heart_matrix[y][x] == 1:
                    display.pixel(heart_x_offset + x, heart_y_offset + y, 1)
        display.show()
        await asyncio.sleep(BLINK_INTERVAL_MS / 1000)

        # Clear the heart shape
        for y in range(heart_height):
            for x in range(heart_width):
                display.pixel(heart_x_offset + x, heart_y_offset + y, 0)
        display.show()
        await asyncio.sleep(BLINK_INTERVAL_MS / 1000)


# Main function in charge of updating the display content dynamically based on the provided display_data
async def update_display(display_data):
    shared_info = display_data.get("header", "") + "  " + display_data.get("battery_level", "") + "%"

    line_1_data = display_data.get(1, ["", "", "", "", "", ""])
    line_2_data = display_data.get(2, ["", "", "", "", "", ""])
    line_3_data = display_data.get(3, ["", "", "", "", "", ""])

    line_data = [line_1_data, line_2_data, line_3_data]

    display.fill(0)  # Clear display

    # Drawing the device lines
    for i, data in enumerate(line_data):
        y_offset = 14 + i * LINE_SPACING

        device_id = str(i + 1)  # Column 1: Device ID
        signal = data[0]  # Signal
        status = data[2]  # Status
        health = data[3]  # Health status (HOT/COLD)
        last_connection = data[4]  # Last connection time
        button_time = data[5] if isinstance(data[5], int) else 0  # get the button time, or 0 if not a digit.

        # Determine Column 2 content (Signal, LOST, REC)
        if button_time == 9 and status != "Wait":  # override the status, if button time is 0 and status is not wait.
            column_2_content = "SENT"
        elif status == "LOST":
            column_2_content = "LOST"
        elif status == "REC":
            column_2_content = "REC"
        elif status == "SLEEP":
            column_2_content = "SLEEP"
        elif status == "Wait":
            column_2_content = "No signal..."
        else:
            column_2_content = signal  # Default to Signal

        # Determine Column 3 content (Last Connection or Health)
        if health in ["HOT", "COLD"]:
            column_3_content = health  # Show health status if present
        elif status == "Wait":
            column_3_content = ""
        else:
            column_3_content = last_connection  # Otherwise, show last connection

        # Draw the text at calculated positions
        display.text(device_id, 0, y_offset)  # Column 1
        display.text(column_2_content, 30, y_offset)  # Column 2
        display.text(column_3_content, 90, y_offset)  # Column 3

    # Display shared header info
    display.fill_rect(0, 0, OLED_WIDTH, 12, 0)  # Clear header area
    display.text(shared_info, 0, 2)  # Show header info
    display.hline(0, 12, OLED_WIDTH, 1)  # Draw a line under the header

    # Draw the border around the active row (entire width)
    active_device = display_data.get("active_device", 1)  # Get active device (1-based index)
    highlight_y = 12 + (active_device - 1) * LINE_SPACING  # Calculate Y-position for the highlighted row
    display.rect(0, highlight_y, OLED_WIDTH - 1, LINE_HEIGHT, 1)

    # Create a task to run blink_heart in the background
    last_sender_id = display_data.get('last_sender_id', None)
    if last_sender_id is not None:
        asyncio.create_task(blink_heart(last_sender_id))  # This runs blink_heart without blocking

    display_data['last_sender_id'] = None

    # Get the button time of the active device
    active_device_data = line_data[active_device - 1]  # Get data for the active device
    button_time = active_device_data[5] if isinstance(active_device_data[5], int) else 0  # Get button time for active device

    # Draw the progress if requested
    bar_width = min(button_time * (OLED_WIDTH // 2), OLED_WIDTH)  # Ensure the bar doesn't exceed display width
    if bar_width > 0:
        bar_height = 10
        progress_bar_y_offset = OLED_HEIGHT - bar_height  # Ensures full bar fits on screen
        display.fill_rect(0, progress_bar_y_offset, bar_width, bar_height, 1)

    display.show()
