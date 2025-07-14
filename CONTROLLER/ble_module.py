# ble_module.py
import asyncio
import machine
import bluetooth
from aioble.security import pair
import aioble
from commands import Commands, GoProUuid
import gc

class GoProBLE:
    def __init__(self):
        self.device = None
        self.device_name = None
        self.connection = None
        self.service = None
        self.char_command = None
        self.char_settings = None
        self.char_query = None
        self.notification_handler = None
        self.is_connected = False

    async def scan_for_gopro(self, scan_duration=3000):
        gc.collect()  # Clean memory before scanning
        print("Starting scan for GoPro devices...")

        async with aioble.scan(duration_ms=scan_duration, interval_us=30000, window_us=30000, active=True) as scanner:
            async for result in scanner:
                name = result.name()
                if not name:
                    continue
                if "GoPro" not in name:
                    continue

                # Check if required service UUID present without building list
                if any(s == bluetooth.UUID(0xFEA6) for s in result.services() or []):
                    self.device_name = name
                    self.device = result.device
                    print(f"GoPro found: {self.device_name}")
                    return True

        print("Scan complete. No matching GoPro found.")
        return False
    
    async def pair_and_save(self, connect_timeout=5000):
        if not self.device:
            print("No GoPro device found. Scan first.")
            return False

        try:
            print(f"Connecting to {self.device_name}...")
            self.connection = await self.device.connect(timeout_ms=connect_timeout)
            print(f"Connected to {self.device_name}")

            print("Pairing with GoPro...")
            await pair(self.connection)
            self.is_connected = True
            print("Paired with GoPro device.")

            mac = ':'.join(f'{b:02X}' for b in self.device.addr)
            print(f"MAC Address: {mac}")
            with open("gopro_mac.txt", "w") as f:
                f.write(mac)

            return True
        
        except Exception as e:
            self.is_connected = False
            print(f"Failed to connect to {self.device_name}: {e}")
            return False
        
    async def connect_by_mac(self, connect_timeout=5000):
        try:
            with open("gopro_mac.txt", "r") as f:
                mac_str = f.read().strip()
                mac_bytes = bytes(int(b, 16) for b in mac_str.split(":"))
        except Exception as e:
            print(f"Could not read MAC address: {e}")
            return False

        try:
            print(f"Attempting direct connection to saved MAC: {mac_str}...")
            self.device = aioble.Device(addr_type=0, addr=mac_bytes)
            self.connection = await self.device.connect(timeout_ms=connect_timeout)
            self.is_connected = True
            print(f"Reconnected to GoPro at {mac_str}.")
            return True
        except Exception as e:
            print(f"Failed to connect to saved MAC {mac_str}: {e}")
            return False

    async def disconnect(self):
        if self.connection:
            try:
                print("Disconnecting from GoPro...")
                await self.connection.disconnect()
                self.is_connected = False
                print("Disconnected from GoPro.")
                self.device = None  # Reset device and other connection-related data
                self.device_name = None
                self.connection = None
                self.service = None
                self.char_command = None
                return True
            except Exception as e:
                print(f"Error during disconnection: {e}")
                return False
        return False  # Not connected

    async def discover_service(self):
        if not self.connection:
            print("Not connected. Connect first.")
            return False
        try:
            print("Discovering GoPro service...")
            self.service = await self.connection.service(bluetooth.UUID(0xFEA6))
            if self.service:
                print("GoPro service found.")

                # Discover the specific characteristics for commands, settings, and queries
                self.char_command = await self.service.characteristic(bluetooth.UUID(GoProUuid.COMMAND_REQ_UUID))
                self.char_settings = await self.service.characteristic(bluetooth.UUID(GoProUuid.SETTINGS_REQ_UUID))
                self.char_query = await self.service.characteristic(bluetooth.UUID(GoProUuid.QUERY_REQ_UUID))

                if not self.char_command:
                    print("Command characteristic not found.")
                if not self.char_settings:
                    print("Settings characteristic not found.")
                if not self.char_query:
                    print("Query characteristic not found.")

                return True
            print("GoPro service not found.")
            return False
        except Exception as e:
            print(f"Error discovering service: {e}")
            return False

    async def subscribe_to_characteristics(self):
        if not self.service:
            print("Service not discovered. Discover service first.")
            return False
        try:
            print("Subscribing to characteristics...")
            characteristic_uuids = [
                GoProUuid.COMMAND_RSP_UUID,
                GoProUuid.SETTINGS_RSP_UUID,
                GoProUuid.QUERY_RSP_UUID,
            ]
            for char_uuid in characteristic_uuids:
                char = await self.service.characteristic(bluetooth.UUID(char_uuid))
                if char:
                    print(f"Subscribed to {char_uuid}.")
                    await char.subscribe(notify=True)
                    asyncio.create_task(self._process_notification(char))
                else:
                    print(f"Characteristic {char_uuid} not found.")

            await self._register_status_notifications()
            return True
        except Exception as e:
            print(f"Error subscribing to characteristics: {e}")
            return False

    async def _register_status_notifications(self):
        try:
            query_request_uuid = bluetooth.UUID(GoProUuid.QUERY_REQ_UUID)
            status_char = await self.service.characteristic(query_request_uuid)

            if status_char:
                print("Registering for status notifications...")
                payload = bytes([0x03, 0x53, 0x0A, 0x55, 0x06])
                # 0x53 is REG_STATUS_VAL_UPDATE
                # 0x0A is ENCODING
                # 0x55 is LOW TEMP
                # 0x06 is OVERHEATING
                
                await status_char.write(payload, response=True)
                print("Successfully registered for status updates.")
            else:
                print("Query Request Characteristic not found.")
        except Exception as e:
            print(f"Error registering for status notifications: {e}")

    async def _process_notification(self, char):
        while True:
            try:
                data = await char.notified()
                print(f"[LAURA <-- GoPro] Notification received from {char.uuid}: {data.hex()} (length: {len(data)})")
                await self._handle_notification_data(char.uuid, data)
            except Exception as e:
                print(f"Error processing notification from {char.uuid}. Data: {data.hex() if data else 'None'}. Error: {str(e)}")
                continue  # Ensure the loop keeps running

    async def _handle_notification_data(self, char_uuid, data):
        try:
            if self.notification_handler:
                # print(f"Handling notification from {char_uuid}. Data: {data.hex()}")  # Debug
                await self.notification_handler(char_uuid, data)
            else:
                print(f"No handler registered for {char_uuid}. Data: {data.hex()}")
        except Exception as e:
            print(f"Error in _handle_notification_data for {char_uuid}. Data: {data.hex() if data else 'None'}. Exception: {repr(e)}")

    def register_notification_handler(self, handler):
        self.notification_handler = handler
    
    async def send_command(self, command):
        if not self.char_command:
            print("[LAURA xxx GoPro] Command characteristic not available. Connect and discover service first.")
            return False
        try:
            print(f"[LAURA --> GoPro] Sending command: {command.hex()}")
            await self.char_command.write(command)
            return True
        except Exception as e:
            print(f"[LAURA xxx GoPro] Error sending command: {e}")
            return False

    async def send_settings_request(self, payload):
        """Send a settings request to the GoPro."""
        if not self.char_settings:
            print("[LAURA xxx GoPro] Settings characteristic not available. Discover service first.")
            return False
        try:
            print(f"[LAURA --> GoPro] Sending settings request: {payload.hex()}")
            await self.char_settings.write(payload)
            return True
        except Exception as e:
            print(f"[LAURA xxx GoPro] Error sending settings request: {e}")
            return False

    async def send_query_request(self, payload, retry=True):
        """Send a query request to the GoPro, retrying if disconnected."""
        if not self.char_query:
            print("[LAURA xxx GoPro] Query characteristic not available. Attempting reconnection...")
            if retry and await self.reconnect():
                return await self.send_query_request(payload, retry=False)
            return False
        
        try:
            print(f"[LAURA --> GoPro] Sending query request: {payload.hex()}")
            await self.char_query.write(payload)
            return True
        except Exception as e:
            print(f"[LAURA xxx GoPro] Error sending query request: {e}. Attempting reconnection...")
            if retry and await self.reconnect():
                return await self.send_query_request(payload, retry=False)
            return False
        
    async def connect_and_subscribe(self, retry_indefinitely=False):
        while True:
            connected = await self.connect_by_mac()
            if not connected:
                print("Saved MAC connection failed. Scanning and pairing...")
                if not await self.scan_for_gopro():
                    print("Scan failed. Retrying..." if retry_indefinitely else "Scan failed.")
                    if not retry_indefinitely:
                        return False
                    await asyncio.sleep(2)
                    continue

                if not await self.pair_and_save():
                    print("Pairing failed. Retrying..." if retry_indefinitely else "Pairing failed.")
                    if not retry_indefinitely:
                        return False
                    await asyncio.sleep(2)
                    continue

            if not await self.discover_service():
                print("Service discovery failed. Retrying..." if retry_indefinitely else "Service discovery failed.")
                await self.disconnect()
                if not retry_indefinitely:
                    return False
                await asyncio.sleep(2)
                continue

            if not await self.subscribe_to_characteristics():
                print("Subscription failed. Retrying..." if retry_indefinitely else "Subscription failed.")
                await self.disconnect()
                if not retry_indefinitely:
                    return False
                await asyncio.sleep(2)
                continue

            return True  # Success
        
    async def reconnect(self):
        """Attempt to reconnect to the GoPro, and reboot if all attempts fail."""
        print("[LAURA xxx GoPro] Attempting to reconnect...")
        await self.disconnect()  # Ensure a clean disconnect
        retry_attempts = 5
        delay = 2  # Initial delay (seconds)

        for attempt in range(retry_attempts):
            print(f"[LAURA --> GoPro] Reconnection attempt {attempt + 1}/{retry_attempts}...")
            if await self.connect_and_subscribe():
                print("[LAURA --> GoPro] Reconnected successfully!")
                return True
            print(f"[LAURA xxx GoPro] Reconnection failed. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff

        print("[LAURA xxx GoPro] Reconnection failed after multiple attempts. Rebooting device...")
        machine.reset()  # Perform a soft reboot
        return False  # This line won't be reached since the device resets

