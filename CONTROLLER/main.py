# CONTROLLER ESP32
import machine
import asyncio
import bluetooth
import utime as time
from ble_module import GoProBLE
from commands import GoProUuid, Commands, Settings
from ble_handler import handle_command_response, handle_query_response, handle_settings_response
import gc

print("Total RAM:", gc.mem_alloc() + gc.mem_free(), "bytes")
print("Free RAM:", gc.mem_free(), "bytes")
gc.collect()  # Run garbage collection at startup

# Constants for configuration
INACTIVITY_TIMEOUT = 300  # Inactivity timeout (in seconds)
ALWAYS_ON = True  # Set to True to disable inactivity check
COMMAND_DELAY = 0.5  # seconds
STATUS_QUERY_INTERVAL = 5  # seconds between status checks

# GPIO setup
BUTTON_PIN = 0
button_pin = machine.Pin(BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

ble = GoProBLE()

# Global variables for status tracking
recording_status = False  
system_hot = False  
low_temp = False
camera_on = True  # Track camera power state
last_interaction = time.time()  # Track last button press or command

async def setup_camera():
    """Executes the initial camera settings one command at time. Delay needed to ensure the camera applies them."""
    print("Disabling WiFi...")
    await ble.send_command(Commands.WiFi.OFF)
    await asyncio.sleep(COMMAND_DELAY)
    print("Disabling Auto Power Down...")
    await ble.send_settings_request(Settings.AutoPowerDown.Never)
    await asyncio.sleep(COMMAND_DELAY)
    print("Setting Video Mode...")
    await ble.send_command(Commands.PresetGroup.Video)
    await asyncio.sleep(COMMAND_DELAY)
    print("Setting Resolution...")
    await ble.send_settings_request(Settings.Resolution.RES_4K)
    await asyncio.sleep(COMMAND_DELAY)
    print("Setting Framerate...")
    await ble.send_settings_request(Settings.Framerate.FPS_60)
    await asyncio.sleep(COMMAND_DELAY)
    print("Setting FOV...")
    await ble.send_settings_request(Settings.VideoLens.Wide)
    await asyncio.sleep(COMMAND_DELAY)
    
    print("GoPro configuration completed.")

async def handle_button_press():
    """Handles button presses: wakes camera if off, or toggles recording if on."""
    global recording_status, camera_on, last_interaction  

    while True:
        if not button_pin.value():  
            print("Button pressed!")
            last_interaction = time.time()  # Update interaction time

            if camera_on:
                # If camera is on, toggle recording
                if recording_status:
                    await ble.send_command(Commands.Shutter.Stop)
                    print("Sent Stop command")
                else:
                    await ble.send_command(Commands.Shutter.Start)
                    print("Sent Start command")
            else:
                # If camera is off, wake it up and restart periodic queries
                print("Waking up GoPro...")
                await asyncio.sleep(2)  # Wait for camera to wake up
                camera_on = True

                # Restart queries and inactivity monitoring
                asyncio.create_task(periodic_query_request())  
                asyncio.create_task(monitor_inactivity())  

            await asyncio.sleep(0.2)  
        await asyncio.sleep(0.05)

async def notification_handler(char_uuid, data):
    """Redirects BLE notifications to the correct handler based on UUID."""
    global recording_status, system_hot, low_temp

    try:
        handler_map = {
            bluetooth.UUID(GoProUuid.COMMAND_RSP_UUID): handle_command_response,
            bluetooth.UUID(GoProUuid.QUERY_RSP_UUID): handle_query_response,
            bluetooth.UUID(GoProUuid.SETTINGS_RSP_UUID): handle_settings_response
        }

        handler = handler_map.get(char_uuid)

        if handler:
            if char_uuid == bluetooth.UUID(GoProUuid.QUERY_RSP_UUID):
                # Process periodic status queries without updating last_interaction
                received_statuses = await handler(char_uuid, data)

                if "recording_status" in received_statuses:
                    recording_status = received_statuses["recording_status"]
                if "system_hot" in received_statuses:
                    system_hot = received_statuses["system_hot"]
                if "low_temp" in received_statuses:
                    low_temp = received_statuses["low_temp"]

                print(f"Updated statuses (from periodic query): recording={recording_status}, system_hot={system_hot}, low_temp={low_temp}")

            else:
                await handler(char_uuid, data)

        else:
            print(f"Unknown UUID: {char_uuid}")

    except Exception as e:
        print(f"Error in notification_handler for {char_uuid}. Data: {data.hex() if data else 'None'}. Exception: {repr(e)}")

async def periodic_query_request():
    """Sends a BLE query request with interval defined in STATUS_QUERY_INTERVAL to update the status, but stops if the camera is off."""
    gc.collect()  # Clean memory before BLE request
    
    while camera_on:
        await ble.send_query_request(b'\x05\x13\x0a\x55\x06')
        await asyncio.sleep(STATUS_QUERY_INTERVAL)  # Wait for 5 seconds before sending again
    print("[DEBUG] Stopping periodic queries because camera is off.")

async def monitor_inactivity():
    """Stops queries and powers off the camera after inactivity."""
    global camera_on, last_interaction

    while True:
        if not camera_on or ALWAYS_ON:
            await asyncio.sleep(1)  # Sleep if the camera is off or alway-on is enabled
            continue  # Skip loop iteration

        await asyncio.sleep(10)  # Check every 10 seconds
        elapsed_time = time.time() - last_interaction
        print(f"[DEBUG] Checking inactivity: Elapsed time = {elapsed_time:.2f} seconds")

        if camera_on and elapsed_time > INACTIVITY_TIMEOUT:  # Use the constant for inactivity timeout
            print(f"[DEBUG] No interaction for {INACTIVITY_TIMEOUT} seconds. Stopping queries and powering off GoPro...")
            camera_on = False
            await ble.send_command(Commands.Basic.Sleep)  # Power off the GoPro

async def main():
    # Enable notification handler
    ble.register_notification_handler(notification_handler)
    
    # Connect to GoPro
    if not await ble.connect_and_subscribe(retry_indefinitely=True):
        print("Failed to connect and subscribe to GoPro.")
        return

    # Clean memory after pairing process
    gc.collect()
    
    # Set the camera with default recording parameters
    await setup_camera()

    asyncio.create_task(handle_button_press())  # Handle button presses
    asyncio.create_task(periodic_query_request())  # Start periodic query requests
    asyncio.create_task(monitor_inactivity())  # Start inactivity monitor
    
    while True:
        await asyncio.sleep(1)

asyncio.run(main())

