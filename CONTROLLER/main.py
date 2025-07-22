# L.A.U.R.A. CONTROLLER Ver.3 - main.py
import machine
import config
from logger_utils import print_info, print_warning, print_error, print_debug
import asyncio
import utime as time
from ble_module import GoProBLE
from commands import Commands, Settings
from ble_handler import register_callback
from oled_display import update_display, shutdown_display
from lora_controller import get_async_modem, send_coro, recv_coro
import urandom

# GPIO setup
button_pin = machine.Pin(config.BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

ble = GoProBLE()

# Global variables for status tracking
modem = None
last_interaction = time.time()  # Track last button press or command

camera_status = {
    "recording": False,
    "system_hot": False,
    "low_temp": False,
    "camera_on": True,
    "internal_battery_percentage": 0,
}

# LoRa Commands
LORA_COMMANDS = {
    "START": 0x01,
    "STOP": 0x02,
    "TRIGGER": 0x03,
    # add more later
}

async def monitor_inactivity():
    """
    Stops queries and powers off the camera after a period of user inactivity.
    
    Checks the last interaction timestamp and sends a sleep command to the camera
    if the inactivity threshold is exceeded.
    """
    while True:
        if not camera_status["camera_on"] or config.ALWAYS_ON:
            await asyncio.sleep(1)  # Sleep if the camera is off or alway-on is enabled
            continue  # Skip loop iteration

        await asyncio.sleep(10)  # Check every 10 seconds
        elapsed_time = time.time() - last_interaction
        print_debug(f"Checking inactivity: Elapsed time = {elapsed_time:.2f} seconds")

        if camera_status["camera_on"] and elapsed_time > config.INACTIVITY_TIMEOUT:  # Use the constant for inactivity timeout
            print_debug(f"No interaction for {config.INACTIVITY_TIMEOUT} seconds. Stopping queries and powering off GoPro...")
            camera_status["camera_on"] = False
            await ble.send_command(Commands.Basic.Sleep)  # Power off the GoPro

async def delayed_display_off(delay=config.DISPLAY_TIMEOUT):
    """
    Turns off the OLED display after a delay.
    Args:
        delay (int): Time in seconds to wait before powering off the display.
                     Defaults to config.DISPLAY_TIMEOUT.
    """
    print_debug(f"Display will shut down in {delay} seconds.")
    await asyncio.sleep(delay)
    shutdown_display()
    print_debug("OLED display powered off.")

async def handle_button_press():
    """
    Monitors the button and performs actions based on the camera state.

    - If the camera is ON, a button press toggles recording (start/stop).
    - If the camera is OFF, a button press wakes it up and reinitializes tracking.

    Continuously polls the button pin and manages debounce timing.

    Globals Modified:
        camera_status["recording"] (bool): Updated based on command sent.
        camera_status["camera_on"] (bool): Set to True if the camera is woken up.
        last_interaction (float): Updated with the current time on press.
    """
    global last_interaction
    
    while True:
        if not button_pin.value():  
            last_interaction = time.time()  # Update interaction time

            if camera_status["camera_on"]:
                # If camera is on, toggle recording
                if camera_status["recording"]:
                    await ble.send_command(Commands.Shutter.Stop)
                    print_info("Button pressed: Sent Stop command")
                else:
                    await ble.send_command(Commands.Shutter.Start)
                    print_info("Button pressed: Sent Start command")
            else:
                # If camera is off, wake it up and restart periodic queries
                print_info("Button pressed: Waking up GoPro...")
                await asyncio.sleep(2)  # Wait for camera to wake up
                camera_status["camera_on"] = True

            await asyncio.sleep(0.2)  
        await asyncio.sleep(0.05)

def lora_handler_wrapper(received_data):
    """
    Wraps the received LoRa data in an asyncio task for processing.

    This allows the `process_received_message` coroutine to run asynchronously
    without blocking the main event loop.

    Args:
        received_data (dict): Parsed LoRa message containing at least a 'payload' key.
    """
    asyncio.create_task(process_received_message(received_data))

async def periodic_heartbeat_sender():
    """
    Periodically sends a heartbeat message to the remote device via LoRa.

    The heartbeat contains camera status indicators such as power state,
    temperature flags, and recording status. If the camera is off, default
    safe values are sent instead.

    Adds a small random delay before each transmission to help avoid
    collisions with other LoRa devices.

    Globals Used:
        camera_status["camera_on"] (bool): Indicates if the camera is currently powered on.
        camera_status["system_hot"] (bool): True if the camera is overheating.
        camera_status["low_temp"] (bool): True if the camera is in low temperature condition.
        camera_status["recording"] (bool): Indicates if the camera is currently recording.
        camera_status["internal_battery_percentage"] (int): Indicates the charge percentage of the GoPro battery

    Notes:
        - Uses `config.STATUS_QUERY_INTERVAL` as the interval between messages.
        - Payload format is fixed and aligned with expected remote parsing.
    """
    while True:
        msg_type = 0x10
        
        # If camera is off, override statuses to safe defaults
        hot = int(camera_status["system_hot"]) if camera_status["camera_on"] else 0
        cold = int(camera_status["low_temp"]) if camera_status["camera_on"] else 0
        recording = int(camera_status["recording"]) if camera_status["camera_on"] else 0

        payload = bytearray([
            msg_type,											# Heartbeat message type
            int(camera_status["camera_on"]),					# camera_connected
            int(camera_status["internal_battery_percentage"]),	# GoPro battery_level
            int(camera_status["camera_on"]),					# sleep_mode
            hot,												# overheating
            cold,												# low_temperature
            0,													# flatmode
            0,													# preset_group
            0,													# video_preset
            0,													# framerate
            0,  												# resolution
            recording											# recording
        ])

        recording_icon = "🔴" if camera_status["recording"] else "⚪"
        hot_icon = "🔥" if camera_status["system_hot"] else "✅"
        cold_icon = "❄️" if camera_status["low_temp"] else "✅"
        power_icon = "✅" if camera_status["camera_on"] else "💤"
        battery_pct = camera_status["internal_battery_percentage"]
        battery_icon = "🟥" if battery_pct <= 20 else "🟨" if battery_pct <= 50 else "🟩"

        print_info(
            f"[Heartbeat] {power_icon} CAMERA: {'On' if camera_status['camera_on'] else 'Off'} | "
            f"{hot_icon} HOT: {'Yes' if camera_status['system_hot'] else 'No'} | "
            f"{cold_icon} COLD: {'Yes' if camera_status['low_temp'] else 'No'} | "
            f"{recording_icon} RECORDING: {'Yes' if camera_status['recording'] else 'No'} | "
            f"🔋 BATTERY: {battery_icon} {battery_pct}%"
        )
        
        # Add randorm delay to avoir LoRa Collistions
        await asyncio.sleep_ms(urandom.getrandbits(4))  # Random 0–15 ms
        
        # Send heartbeat to the remote vie LoRa
        await send_coro(modem, config.DEVICE_UID, config.REMOTE_UID, payload)
        
        # Wait for the next send as defined in config.py
        await asyncio.sleep(config.STATUS_QUERY_INTERVAL)  # send every 5s or whatever you want

async def setup_camera():
    """
    Configures the GoPro with default recording parameters on startup.

    Sends a series of BLE commands to apply camera settings such as:
    - Disabling WiFi
    - Enabling GPS
    - Disabling auto power-down
    - Selecting video mode preset
    - Applying resolution, framerate, and FOV from config

    A delay (`config.COMMAND_DELAY`) is applied between each command to ensure
    the camera has time to process and apply the settings correctly.

    The OLED display is updated after each step for user feedback.
    """
    print_debug("Disabling WiFi...")
    await ble.send_command(Commands.WiFi.OFF)
    update_display("Disabling", "WiFi")
    await asyncio.sleep(config.COMMAND_DELAY)
    
    print_debug("Enabling GPS...")
    await ble.send_settings_request(Settings.GPS.ON)
    update_display("Enabling", "GPS")
    await asyncio.sleep(config.COMMAND_DELAY)
    
    print_debug("Disabling Auto Power Down...")
    update_display("Disabling", "PowerSave")
    await ble.send_settings_request(Settings.AutoPowerDown.Never)
    await asyncio.sleep(config.COMMAND_DELAY)
    
    print_debug("Setting Video Mode...")
    update_display("Setting", "Mode")
    await ble.send_command(Commands.PresetGroup.Video)
    await asyncio.sleep(config.COMMAND_DELAY)
    
    print_debug("Setting Resolution...")
    update_display("Setting", "Resolution")
    await ble.send_settings_request(config.RESOLUTION)
    await asyncio.sleep(config.COMMAND_DELAY)
    
    print_debug("Setting Framerate...")
    update_display("Setting", "FPS")
    await ble.send_settings_request(config.FRAMERATE)
    await asyncio.sleep(config.COMMAND_DELAY)
    
    print_debug("Setting FOV...")
    update_display("Setting", "FOV")
    await ble.send_settings_request(config.FOV)
    await asyncio.sleep(config.COMMAND_DELAY)
    
    update_display(f"ID: {config.DEVICE_UID}", "READY")
    
async def periodic_query_request():
    """
    Periodically sends a BLE query request to update camera status.

    This coroutine checks if the camera is on and, if so, sends a status
    query at regular intervals defined by `config.STATUS_QUERY_INTERVAL`.
    If the camera is off, it waits and checks again every second.

    Notes:
        - The query is used to retrieve current camera state (e.g., recording, temperature).
        - Query bytes are currently hardcoded and may be updated as needed.
    """
    while True:
        if camera_status["camera_on"]:
            # await ble.send_query_request(b'\x05\x13\x0a\x55\x06')
            await ble.send_query_request(b'\x09\x13\x0a\x55\x06\x02\x01\x46\x27')
            await asyncio.sleep(config.STATUS_QUERY_INTERVAL)
        else:
            print_debug("Camera is off, waiting...")
            await asyncio.sleep(1)  # Poll every second until camera is on
            
async def process_received_message(received_data):
    """
    Handles incoming LoRa command messages and controls the GoPro accordingly.

    Parses the received payload to extract a single-byte command, then
    performs the appropriate camera action (start, stop, or trigger recording).

    Behavior:
        - If the camera is off and a TRIGGER command is received,
          attempts to reconnect before proceeding.
        - If the camera is on, executes the command immediately.
        - Updates `last_interaction` timestamp on valid command receipt.

    Args:
        received_data (dict): Dictionary containing a 'payload' key with a list or bytes-like object.

    Globals Used:
        camera_status["camera_on"] (bool): Checked and modified based on command logic.
        last_interaction (float): Updated to track user interaction time.

    Logs:
        - Payload content and command details
        - Errors for unexpected payload lengths or unknown commands
        - Info on camera reconnection and command dispatch
    """
    global last_interaction
    
    rx = received_data.get("payload")
    if rx is None:
        print_warning("Error: 'payload' missing.")
        return

    rx_bytes = bytes(rx)
    print_debug(f"Received command: {rx_bytes}")

    if len(rx_bytes) != 1:
        print_error(f"Unexpected payload length: {len(rx_bytes)}. Expected 1 byte.")
        return

    command_code = rx_bytes[0]  # Extract the integer command code

    # If camera off, reconnect
    if not camera_status["camera_on"]:
        if command_code == LORA_COMMANDS["TRIGGER"]:
            last_interaction = time.time()  # Update interaction time
            print_info("Received TRIGGER command but GoPro is off: reconnecting...")
            success = await ble.reconnect()
            if success:
                camera_status["camera_on"] = True
                print_debug("GoPro is ON again.")
            else:
                print_error("Reconnect to GoPro failed. Skipping command.")
            return  # Still skip executing the command itself

    # Camera is on, handle commands normally
    if command_code == LORA_COMMANDS["START"]:
        last_interaction = time.time()
        print_info("Sending START recording command to GoPro...")
        await ble.send_command(Commands.Shutter.Start)
    elif command_code == LORA_COMMANDS["STOP"]:
        last_interaction = time.time()
        print_info("Sending STOP recording command to GoPro...")
        await ble.send_command(Commands.Shutter.Stop)
    elif command_code == LORA_COMMANDS["TRIGGER"]:
        last_interaction = time.time()
        if camera_status["recording"]:
            print_info("GoPro is recording: sending STOP recording command...")
            await ble.send_command(Commands.Shutter.Stop)
        else:
            print_info("GoPro is NOT recording: sending START recording command...")
            await ble.send_command(Commands.Shutter.Start)
    else:
        print_error(f"Unknown command: {rx_bytes}")
        
async def ble_notification_data_handler(event_type, data):
    """
    Handles BLE notification events by updating global status variables.

    Processes different types of BLE events (e.g., "query_response",
    "command_response") and updates the corresponding global variables
    to reflect the current camera state.

    Args:
        event_type (str): Type of BLE event received (e.g., "query_response", "command_response").
        data (dict): Parsed data dictionary associated with the event.

    Globals Modified:
        camera_status["recording"] (bool): Updated based on query responses.
        camera_status["system_hot"] (bool): Updated based on query responses.
        camera_status["low_temp"] (bool): Updated based on query responses.
        camera_status["internal_battery_percentage"] (int): Updated based on query responses.
    """
    print_info(f"Received event {event_type} with data: {data}")

    # Update global variables based on event_type and data, e.g.:
    if event_type == "query_response":
        camera_status["recording"] = data.get("recording_status", camera_status["recording"])
        camera_status["system_hot"] = data.get("system_hot", camera_status["system_hot"])
        camera_status["low_temp"] = data.get("low_temp", camera_status["low_temp"])
        camera_status["internal_battery_percentage"] = data.get("internal_battery_percentage", camera_status["internal_battery_percentage"])
    elif event_type == "command_response":
        pass
 
async def main():
    global modem
    
    # Register handler to process parsed BLE events from ble_handler
    register_callback(ble_notification_data_handler)
        
    # Connect to GoPro
    print_info("Connecting to the GoPro...")
    if not await ble.connect_and_subscribe(retry_indefinitely=True):
        print("Failed to connect and subscribe to GoPro.")
        return
    
    # Set the camera with default recording parameters
    print_info("Setting GoPro parameters...")
    await setup_camera()
    
    # Schedule OLED display shutdown after 2 minutes
    asyncio.create_task(delayed_display_off())
    
    # Initialize LoRa modem
    print_info("Initializing modem...")
    modem = get_async_modem()

    # Handle button presses
    print_info("Starting button monitor...")
    asyncio.create_task(handle_button_press())
    
    # Start periodic query requests
    print_info("Starting periodic query requests...")
    asyncio.create_task(periodic_query_request())
    
    # Start periodic heartbeat send
    print_info("Starting periodic heartbeat send...")
    asyncio.create_task(periodic_heartbeat_sender())
    
    # Start inactivity monitor
    print_info("Starting inactivity monitor...")
    asyncio.create_task(monitor_inactivity())
    
    # Start LoRa receiver
    print("Starting LoRa message receiver...")
    asyncio.create_task(recv_coro(modem, config.DEVICE_UID, lora_handler_wrapper))
    
    while True:
        await asyncio.sleep(1)

asyncio.run(main())