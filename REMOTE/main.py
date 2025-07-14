# L.A.U.R.A. REMOTE Ver.2.1 - main.py
import uasyncio as asyncio
import machine
import utime as time
from lora_controller import get_async_modem, send_coro, recv_coro
from display_controller import update_display
from battery import battery_percentage
from config import DEVICE_UID, HEARTBEAT_TIMEOUT_SEC
from logger_utils import print_info, print_warning, print_error, print_debug

# Global variables
modem = None

# Timeout constants
BATT_CHECK_TIMEOUT_SEC = 60  # How often the battery level is checked
AUTO_SLEEP_TIMEOUT_SEC = 300  # Sleep timeout

# LoRa Commands
LORA_COMMANDS = {
    "START": 0x01,
    "STOP": 0x02,
    "TRIGGER": 0x03,
}

# Initialize timoeut variables
last_interaction_time = time.time()
last_battery_check_time = time.time() - BATT_CHECK_TIMEOUT_SEC  # Trick it to be a past time

# Initialize display message dictionary
display_data = {
    'active_device': 1,
    'last_sender_id': None,
    'header': 'L.A.U.R.A.',  # Main header
    'battery_level': '00',  # Separate battery level
    
    1: ['Signal', 'SNR', 'Status', 'Health', 'Last Comm', 'Button Press Time'],
    2: ['Signal', 'SNR', 'Status', 'Health', 'Last Comm', 'Button Press Time'],
    3: ['Signal', 'SNR', 'Status', 'Health', 'Last Comm', 'Button Press Time'],
}

# Initialize hearbeat data dictionary
heartbeat_data = {
    1: {'last_heartbeat_time': None, 'heartbeat_timed_out': False},
    2: {'last_heartbeat_time': None, 'heartbeat_timed_out': False},
    3: {'last_heartbeat_time': None, 'heartbeat_timed_out': False}
}

# Initialize hearbeat message dictionary
heartbeat_message = {
    "camera_connected": 0,
    "battery_level": 0,
    "sleep_mode": 0,
    "overheating": 0,
    "low_temperature": 0,
    "flatmode": 0,
    "preset_group": 0,
    "video_preset": 0,
    "framerate": 0,
    "resolution": 0,
    "recording": 0
}

# Callback function to handle received messages
def process_received_message(received_data):
    global heartbeat_message, display_data, heartbeat_data
    
    sender_id = received_data["sender_id"]
    rx = received_data["payload"]
    rssi = received_data["rssi"]
    snr = received_data["snr"]
    packet_length = received_data["packet_length"]
    
    print_debug(f"Received a message from Device ID: {sender_id}")
                       
    if rx[0] == 0x10:  # Heartbeat message
        data = rx[1:]
        if len(data) == 11:
            print_debug(f"Heartbeat data received: {data.hex()}")
            
            # Update the last heartbeat time for the corresponding camera
            heartbeat_data[sender_id]['last_heartbeat_time'] = time.time()  # Set last heartbeat time
            heartbeat_data[sender_id]['heartbeat_timed_out'] = False  # Reset timeout state
            
            # Update heartbeat_message dictionary
            heartbeat_message.update({
                "camera_connected": data[0],
                "battery_level": data[1],
                "sleep_mode": data[2],
                "overheating": data[3],
                "low_temperature": data[4],
                "flatmode": data[5],
                "preset_group": data[6],
                "video_preset": data[7],
                "framerate": data[8],
                "resolution": data[9],
                "recording": data[10]
            })

            # Update only specific indexes
            display_data[sender_id][0] = f"{rssi}dB"  # Signal strength
            display_data[sender_id][1] = f"{snr}dB"   # SNR
            display_data[sender_id][2] = "SLEEP" if heartbeat_message['sleep_mode'] == 0 else ("REC" if heartbeat_message['recording'] == 1 else "Stby")  # Status
            display_data[sender_id][3] = "HOT" if heartbeat_message['overheating'] == 1 else ("COLD" if heartbeat_message['low_temperature'] == 1 else "None")  # Health Alert
            display_data[sender_id][4] = ""  # Last communication time
            display_data[sender_id][5] = 0  # Clear the "SENT" state on heartbeat

            # Set the last sender ID
            print_debug(f"Updating display data for Device {sender_id}: {display_data}")
            display_data["last_sender_id"] = sender_id  # Store which device sent the last update

            print_info(
                f"[Heartbeat] "
                f"{'😴' if data[2] == 0 else '✅'} CAMERA {sender_id}: {'Off' if data[0] == 0 else 'On'} | "
                f"📶 RSSI: {rssi}dB | "
                f"📡 SNR: {snr}dB | "
                f"{'🔥' if data[3] == 1 else '✅'} HOT: {'Yes' if data[3] == 1 else 'No'} | "
                f"{'❄️' if data[4] == 1 else '✅'} COLD: {'Yes' if data[4] == 1 else 'No'} | "
                f"{'🔴' if data[10] == 1 else '⚪'} RECORDING: {'Yes' if data[10] == 1 else 'No'}"
            )
        else:
            print_warning("Heartbeat data corrupted therefore ignored")

# Check for each device the last communication to generate the LOST label on the display
def check_heartbeat_timeouts():
    global heartbeat_data
    
    current_time = time.time()

    for device_id in [1, 2, 3]:
        last_heartbeat_time = heartbeat_data.get(device_id, {}).get('last_heartbeat_time')
        heartbeat_timed_out = heartbeat_data.get(device_id, {}).get('heartbeat_timed_out', False)

        if last_heartbeat_time is None:
            heartbeat_timed_out = True
        else:
            time_since_last = current_time - last_heartbeat_time

            if time_since_last > HEARTBEAT_TIMEOUT_SEC:
                heartbeat_timed_out = True
                print_warning(f"Camera {device_id} heartbeat timeout. Last comm {time_since_last}s ago.")
            else:
                heartbeat_timed_out = False

        heartbeat_data[device_id] = {
            'last_heartbeat_time': last_heartbeat_time,
            'heartbeat_timed_out': heartbeat_timed_out
        }

#  Monitor and refresh display
async def refresh_display():
    global display_data, heartbeat_data, last_battery_check_time

    while True:
        # Check the communication timeouts
        check_heartbeat_timeouts()
        
        # Loop through all devices (1, 2, 3) and update their data for the display
        for device_id in [1, 2, 3]:
            
            # Get current heartbeat data for the device
            heartbeat_timed_out = heartbeat_data.get(device_id, {}).get('heartbeat_timed_out', False)
            last_heartbeat_time = heartbeat_data.get(device_id, {}).get('last_heartbeat_time', None)

            # If heartbeat data is None, it means the device never communicated, display 'Wait'
            if last_heartbeat_time is None:
                display_data[device_id] = [
                    "",							# Signal strength
                    "",							# SNR value
                    "Wait",						# Status - Device has not communicated yet
                    "",							# Health
                    "",							# Last Comm
                    display_data[device_id][5] if device_id in display_data and len(display_data[device_id])>5 else "" # Button Held Seconds
                ]
            
            # If heartbeat is timed out, display "Lost" and show the last communication time
            elif heartbeat_timed_out:
                last_comm_time = time.time() - last_heartbeat_time
                display_data[device_id] = [
                    "",							# Signal strength
                    "",							# SNR value
                    "LOST",						# Status
                    "",							# Health
                    f"{last_comm_time:.0f}s",	# Last Comm - Time since last communication in seconds
                    display_data[device_id][5] if device_id in display_data and len(display_data[device_id])>5 else "" # Button Held Seconds
                ]
            
            # If heartbeat data is available, use the last heartbeat time to update
            else:
                last_comm_time = time.time() - last_heartbeat_time

                # Access device data from the display_data structure
                signal_strength = display_data.get(device_id, [])[0]  # Signal (Index 0)
                snr_value = display_data.get(device_id, [])[1]  # SNR (Index 1)
                status_value = display_data.get(device_id, [])[2]  # SNR (Index 2)
                health_value = display_data.get(device_id, [])[3]  # SNR (Index 3)

                # Update the display data for the device
                display_data[device_id] = [
                    signal_strength,			# Signal strength
                    snr_value,					# SNR value
                    status_value,				# Status
                    health_value,				# Health
                    f"{last_comm_time:.0f}s",	# Last Comm (time since last heartbeat)
                    display_data[device_id][5] if device_id in display_data and len(display_data[device_id])>5 else "" # Button Held Seconds
                ]
        
        # Call the batery check at each display refresh
        check_battery()
        
        try:
            await update_display(display_data)  # Update the display with the latest data
        except Exception as e:
            print_error(f"update_display() failed: {e}")

        await asyncio.sleep(1)  # Adjust as needed
        
def check_battery():
    global last_battery_check_time, display_data

    current_time = time.time()
    if current_time - last_battery_check_time >= BATT_CHECK_TIMEOUT_SEC:
        battery_level = battery_percentage()
        print_debug(f"Current battery level: {battery_level}%")
        display_data['battery_level'] = f"{battery_level}"
        last_battery_check_time = current_time  # Update timestamp

# Monitor the button press to switch active device or send trigger
async def monitor_button(pin, modem, DEVICE_UID):
    global display_data, last_interaction_time
    button = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
    trigger_sent = False  # Flag to track if trigger has been sent
    seconds_held = 0  # Track seconds elapsed
    press_start_time = None  # To track when the button was pressed

    while True:
        if button.value() == 0:  # Button pressed (pin is LOW)
            if press_start_time is None:  # Check if this is the start of the press
                press_start_time = time.ticks_ms()  # Record press start time
                seconds_held = 0  # Reset seconds held at the beginning of a new press

            press_duration = time.ticks_diff(time.ticks_ms(), press_start_time)  # Time held

            # Check the duration
            if press_duration >= (seconds_held + 1) * 1000 and not trigger_sent:  
                seconds_held += 1  # Increase seconds only if trigger has not been sent yet
                print_info(f"Button held for {seconds_held} second(s)")

                # Update the Button Press Time for the active device
                active_device = display_data["active_device"]
                display_data[active_device][5] = seconds_held  # Store seconds_held in 6th position

                # If held for 2+ seconds, send trigger (only if not already sent)
                if seconds_held == 2:
                    print_info("Button pressed for more than 2 seconds, sending trigger command...")
                    payload = bytes([LORA_COMMANDS["TRIGGER"]])
                    asyncio.create_task(send_coro(modem, DEVICE_UID, active_device, payload))
                    display_data[active_device][5] = 9  # Store 9 in 6th position after trigger ti call the SENT label for the selected Device
                    trigger_sent = True  # Mark the trigger as sent to avoid multiple sent until button release
                    print_debug(f"Sent trigger command to Device {active_device}")

            await asyncio.sleep(0.1)  # Prevent busy waiting

        else:  # Button released (pin is HIGH)
            if press_start_time is not None:  # If the button was pressed previously
                # Short press (<3 sec) switches active device
                if seconds_held < 3 and not trigger_sent:
                    print_debug("Button pressed, switching Device")
                    active_device = display_data["active_device"]
                    display_data["active_device"] = (active_device % 3) + 1
                    print_info(f"Switched to Device {display_data['active_device']}")

                # Reset trigger flag and counter after button release
                trigger_sent = False  # Reset the trigger flag to allow future triggers
                press_start_time = None  # Reset press start time for next press
                seconds_held = 0  # Reset the hold time counter
                display_data[display_data["active_device"]][5] = 0  # Reset the button hold counter

                last_interaction_time = time.time()  # Update last interaction time

        await asyncio.sleep(0.1)  # Small debounce delay
    
async def monitor_inactivity():
    global last_interaction_time
    while True:
        current_time = time.time()
        inactivity_duration = current_time - last_interaction_time

        print_debug(f"Power save check: {inactivity_duration}s since last interaction")

        if inactivity_duration > AUTO_SLEEP_TIMEOUT_SEC:
            print_info(f"No interaction for more that {AUTO_SLEEP_TIMEOUT_SEC}s: entering sleep mode")
            machine.deepsleep()

        await asyncio.sleep(5)

# ------------ Main ------------
async def main():
    global modem
    
    print_debug("Initializing display with default values...")
    asyncio.create_task(refresh_display())  

    print_info("Initializing modem...")
    modem = get_async_modem()

    print_info("Starting message reception...")
    asyncio.create_task(recv_coro(modem, DEVICE_UID, process_received_message))
    
    print_info("Starting monitor button press...")
    asyncio.create_task(monitor_button(0, modem, DEVICE_UID))
    
    print_info("Starting monitor for inactivity...")
    asyncio.create_task(monitor_inactivity())

    while True:
        await asyncio.sleep(1)
