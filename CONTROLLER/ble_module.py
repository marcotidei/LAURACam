# L.A.U.R.A. CONTROLLER Ver.3 - ble_module.py
import asyncio
import machine
from logger_utils import print_warning, print_error, print_debug
import bluetooth
from aioble.security import pair
import aioble
from commands import GoProUuid
from ble_handler import handle_ble_notification
from collections import deque  # Frangmentation

class GoProBLE:
    def __init__(self):
        self.device = None
        self.device_name = None
        self.connection = None
        self.service = None
        self.char_command = None
        self.char_settings = None
        self.char_query = None
        #self.notification_handler = None
        self.is_connected = False

    async def scan_for_gopro(self, scan_duration=3000):
        """
        Scan for nearby GoPro devices via BLE.

        Performs an active BLE scan for a given duration, looking for devices that
        advertise a name containing "GoPro" and include the GoPro service UUID (0xFEA6).
        If found, stores the device and device name for later connection.

        Args:
            scan_duration (int): BLE scan duration in milliseconds (default 3000).

        Returns:
            bool: True if a matching GoPro device is found, False otherwise.

        Notes:
            - Uses a 30 ms scan interval and window.
            - Requires BLE hardware and aioble scan context.
            - This method handles exceptions internally and logs errors.
        """
        print_debug("[BLE] Starting scan for devices...")

        async with aioble.scan(duration_ms=scan_duration, interval_us=30000, window_us=30000, active=True) as scanner:
            async for result in scanner:
                name = result.name() or "Unnamed device"  # Get the device name
                services = list(result.services()) if result.services() else []  # Get services
                
                # Print discovered device details
                print_debug(f"[BLE] Discovered: {name}, Services: {services}")

                # Check if it's a GoPro with the required service
                if "GoPro" in name and bluetooth.UUID(0xFEA6) in services:
                # if bluetooth.UUID(0xFEA6) in services:
                    self.device_name = name
                    self.device = result.device
                    print_debug(f"[BLE] GoPro found: {self.device_name}, Services: {services}")

                    return True  # Indicate success

        print_warning("[BLE] Scan complete. No matching GoPro found.")
        return False  # Indicate failure

    async def connect(self, connect_timeout=5000):
        """
        Attempts to establish a BLE connection with the previously discovered GoPro device.

        This method connects to the BLE device found during scanning and performs secure pairing.
        It sets up the internal connection state and updates `is_connected` to reflect the result.

        Args:
            connect_timeout (int): Connection timeout in milliseconds. Defaults to 5000 ms.

        Returns:
            bool: True if the connection and pairing were successful; False otherwise.

        Preconditions:
            - `self.device` must be set (i.e., `scan_for_gopro()` was called and succeeded).

        Logs:
            - Connection and pairing status.
            - Error details in case of failure.
        """
        if not self.device:
            print_warning("[BLE] No GoPro device found. Scan first.")

            return False

        try:
            print_debug(f"[BLE] Connecting to {self.device_name}...")

            self.connection = await self.device.connect(timeout_ms=connect_timeout)
            print_debug(f"[BLE] Connected to {self.device_name}")

            print_debug("[BLE] Pairing with GoPro...")
            await pair(self.connection)
            self.is_connected = True
            print_debug(f"[BLE] Paired with {self.device_name}")
            return True
        
        except Exception as e:
            self.is_connected = False
            print_error(f"[BLE] Failed to connect to {self.device_name}: {e}")
            return False

    async def disconnect(self):
        """
        Gracefully disconnects from the currently connected GoPro BLE device.

        This method terminates the active BLE connection, resets internal state, and
        clears all references to the connected device and its characteristics.

        Returns:
            bool: True if the disconnection was successful; False if not connected or if an error occurred.

        Side Effects:
            - Sets `is_connected` to False.
            - Resets `device`, `device_name`, `connection`, and characteristic references to None.

        Logs:
            - Disconnection attempts and errors.
        """
        if self.connection:
            try:
                print_debug("[BLE] Disconnecting from GoPro...")
                await self.connection.disconnect()
                self.is_connected = False
                print_debug("[BLE] Disconnected from GoPro.")
                self.device = None  # Reset device and other connection-related data
                self.device_name = None
                self.connection = None
                self.service = None
                self.char_command = None
                self.char_settings = None
                self.char_query = None
                return True
            
            except Exception as e:
                print_error(f"[BLE] Error during disconnection: {e}")
                return False
            
        return False  # Not connected

    async def reconnect(self):
        """
        Attempts to reconnect to the GoPro device by performing a full disconnect
        followed by repeated connection and subscription attempts.

        Implements a retry mechanism with exponential backoff, trying up to a fixed
        number of attempts (default 5). If all attempts fail, the device is rebooted
        to recover from the failure state.

        Returns:
            bool: True if reconnection and subscription succeed within retry attempts.
                  False if the function returns (which it normally won't, due to reboot).

        Behavior:
            - Performs a clean disconnect before retrying.
            - Uses exponential backoff delay between retries (starting at 2 seconds).
            - Logs connection attempts and errors.
            - Calls `machine.reset()` to reboot the device if reconnection repeatedly fails.
        
        Note:
            The final return False will never be reached because `machine.reset()` resets the device.
        """
        print_warning("[BLE] Attempting to reconnect...")
        await self.disconnect()  # Ensure a clean disconnect
        retry_attempts = 5
        delay = 2  # Initial delay (seconds)

        for attempt in range(retry_attempts):
            print_debug(f"[BLE] Reconnection attempt {attempt + 1}/{retry_attempts}...")
            if await self.connect_and_subscribe():
                print_debug("[BLE] Reconnected successfully!")
                return True
            print_warning(f"[BLE] Reconnection failed. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff

        print_error("[BLE] Reconnection failed after multiple attempts. Rebooting device...")
        machine.reset()  # Perform a soft reboot
        return False  # This line won't be reached since the device resets

    async def discover_service(self):
        """
        Discovers the GoPro BLE service and its key characteristics.

        This method locates the primary GoPro service (UUID 0xFEA6) on the connected device,
        and attempts to resolve the three main characteristics used for:
            - command transmission,
            - settings control,
            - device queries.

        Returns:
            bool: True if the service and all key characteristics are found; False otherwise.

        Preconditions:
            - Must be connected to the GoPro (`self.connection` must be active).

        Side Effects:
            - Populates `self.service`, `self.char_command`, `self.char_settings`, and `self.char_query`.
            - Logs warnings for any missing characteristic.

        Logs:
            - Service and characteristic discovery status and errors.
        """
        if not self.connection:
            print_debug("[BLE] Not connected. Connect first.")
            return False
        try:
            print_debug("[BLE] Discovering GoPro service...")
            self.service = await self.connection.service(bluetooth.UUID(0xFEA6))
            if self.service:
                print_debug("[BLE] GoPro service found.")

                # Discover the specific characteristics for commands, settings, and queries
                self.char_command = await self.service.characteristic(bluetooth.UUID(GoProUuid.COMMAND_REQ_UUID))
                self.char_settings = await self.service.characteristic(bluetooth.UUID(GoProUuid.SETTINGS_REQ_UUID))
                self.char_query = await self.service.characteristic(bluetooth.UUID(GoProUuid.QUERY_REQ_UUID))

                if not self.char_command:
                    print_error("[BLE] Command characteristic not found.")
                if not self.char_settings:
                    print_error("[BLE] Settings characteristic not found.")
                if not self.char_query:
                    print_error("[BLE] Query characteristic not found.")

                return True
            print_error("[BLE] GoPro service not found.")
            return False
        except Exception as e:
            print_error(f"[BLE] Error discovering service: {e}")
            return False

    async def subscribe_to_characteristics(self, characteristic_uuids, notify_queue_size=None):
        """
        Subscribes to BLE characteristics and starts processing their notifications.

        Args:
            characteristic_uuids (list): A list of characteristic UUIDs (as strings or integers)
                                         to subscribe to. These should match the service's known characteristics.
            notify_queue_size (int, optional): If provided, sets a fixed-size queue for incoming
                                               notifications on each characteristic.

        Returns:
            bool: True if all subscriptions were successfully started, False otherwise.

        Notes:
            - This method requires `self.service` to be set beforehand by a successful service discovery.
            - For each subscribed characteristic, a background task is created to handle notifications
              via `self._process_notification(char)`.
            - If a characteristic is not found or subscription fails, an error is logged but the loop continues.
        """
        if not self.service:
            print_debug("[BLE] Service not discovered. Discover service first.")
            return False
        try:
            print_debug("[BLE] Subscribing to characteristics...")
            for char_uuid in characteristic_uuids:
                char = await self.service.characteristic(bluetooth.UUID(char_uuid))
                if char:
                    print_debug(f"[BLE] Subscribed to {char_uuid}.")
                    if notify_queue_size is not None:
                        char._notify_queue = deque((), notify_queue_size)
                    await char.subscribe(notify=True)
                    asyncio.create_task(self._process_notification(char))
                else:
                    print_error(f"[BLE] Characteristic {char_uuid} not found.")
            return True
        except Exception as e:
            print_error(f"[BLE] Error subscribing to characteristics: {e}")
            return False

    async def register_status_notifications(self, status_codes):
        """
        Sends a registration request to receive BLE notifications for specific GoPro status codes.

        This method writes a structured payload to the GoPro's Query Request Characteristic to
        enable updates for the selected statuses. It is used to monitor events such as
        overheating or encoding state.

        Args:
            status_codes (list of int): A list of status codes (as bytes) to subscribe to.
                Known values include:
                    - 0x0A: Encoding status
                    - 0x55: Low temperature warning
                    - 0x06: Overheating warning

        Returns:
            bool: True if registration request was successfully sent, False otherwise.

        Notes:
            - If no `status_codes` are provided, registration is skipped with a warning.
            - A fixed request type (0x53, REG_STATUS_VAL_UPDATE) is used to indicate registration intent.
            - The service and characteristic must have been discovered prior to calling this method.
        """
        try:
            query_request_uuid = bluetooth.UUID(GoProUuid.QUERY_REQ_UUID)
            status_char = await self.service.characteristic(query_request_uuid)

            if not status_char:
                print_error("[BLE] Query Request Characteristic not found.")
                return False

            if not status_codes:
                print_warning("[BLE] No status codes provided for registration. Skipping registration.")
                return False

            length = len(status_codes)
            request_type = 0x53  # REG_STATUS_VAL_UPDATE, fixed in function
            payload = bytes([length, request_type] + status_codes)

            print_debug(f"[BLE] Registering for status notifications with payload: {payload.hex()}")
            await status_char.write(payload, response=True)
            print_debug("[BLE] Successfully registered for status updates.")
            return True

        except Exception as e:
            print_error(f"[BLE] Error registering for status notifications: {e}")
            return False

    async def _process_notification(self, char):
        """
        Continuously listens for BLE notifications from the specified characteristic,
        assembles fragmented packets if present, and passes them to the handler.

        Args:
            char: The BLE characteristic object to listen to for notifications.

        Behavior:
            - Awaits incoming notifications from the given characteristic.
            - Collects the first packet and any subsequent packets in the queue.
            - Logs each packet with its index and length.
            - Sends each packet to the appropriate BLE handler for processing.
            - Handles and logs exceptions without breaking the notification loop.

        Notes:
            This method is intended to run indefinitely as part of an asyncio task.
        """
        while True:
            data = None  # <--- This ensures 'data' always exists
            try:
                data = await char.notified()

                # Read initial packet
                packets = [data]

                # Pull remaining packets from queue
                while len(char._notify_queue) > 0:
                    packets.append(char._notify_queue.popleft())

                # Log each packet for now
                for i, pkt in enumerate(packets):
                    print_debug(f"[BLE] Notification #{i+1} from {char.uuid}: {pkt.hex()} (length: {len(pkt)})")
                    await handle_ble_notification(char.uuid, pkt)

            except Exception as e:
                print_error(f"[BLE] Error processing notification from {char.uuid}. Data: {data.hex() if data else 'None'}. Error: {str(e)}")
                continue  # Ensure the loop keeps running
    
    async def send_command(self, command):
        """
        Sends a BLE command to the GoPro via the command characteristic.

        Args:
            command (bytes): The command payload to send.

        Returns:
            bool: True if the command was sent successfully, False otherwise.

        Notes:
            - Requires the command characteristic to be discovered and available.
            - Logs errors if the characteristic is missing or if sending fails.
        """
        if not self.char_command:
            print_error("[BLE] Command characteristic not available. Connect and discover service first.")
            return False
        try:
            print_debug(f"[BLE] Sending command: {command.hex()}")
            await self.char_command.write(command)
            return True
        except Exception as e:
            print_error(f"[BLE] Error sending command: {e}")
            return False

    async def send_settings_request(self, payload):
        """
        Sends a settings request payload to the GoPro via the settings characteristic.

        Args:
            payload (bytes): The settings data to be sent.

        Returns:
            bool: True if the settings request was sent successfully, False otherwise.

        Notes:
            - Requires the settings characteristic to be discovered and available.
            - Logs debug information before sending and errors on failure.
        """
        if not self.char_settings:
            print_debug("[BLE] Settings characteristic not available. Discover service first.")
            return False
        try:
            print_debug(f"[BLE] Sending settings request: {payload.hex()}")
            await self.char_settings.write(payload)
            return True
        except Exception as e:
            print_error(f"[BLE] Error sending settings request: {e}")
            return False

    async def send_query_request(self, payload, retry=True):
        """
        Sends a query request payload to the GoPro via the query characteristic.

        Args:
            payload (bytes): The query data to send to the GoPro.
            retry (bool): Whether to attempt reconnection and retry sending if
                          the query characteristic is unavailable or the send fails.
                          Defaults to True.

        Returns:
            bool: True if the query request was successfully sent, False otherwise.

        Behavior:
            - If the query characteristic is not available, attempts to reconnect once
              if `retry` is True, then retries sending the request.
            - On exceptions during sending, attempts reconnection and retry similarly.
            - If reconnection fails or retry is disabled, returns False.

        Logs:
            - Warnings when the characteristic is unavailable.
            - Debug info when sending.
            - Errors on failure and reconnection attempts.
        """
        if not self.char_query:
            print_warning("[BLE] Query characteristic not available. Attempting reconnection...")
            if retry and await self.reconnect():
                return await self.send_query_request(payload, retry=False)
            return False
        
        try:
            print_debug(f"[BLE] Sending query request: {payload.hex()}")
            await self.char_query.write(payload)
            return True
        except Exception as e:
            print_error(f"[BLE] Error sending query request: {e}. Attempting reconnection...")
            if retry and await self.reconnect():
                return await self.send_query_request(payload, retry=False)
            return False
        
    async def connect_and_subscribe(self, retry_indefinitely=False):
        """
        Performs a full connection sequence to the GoPro device including scanning,
        connecting, service discovery, and subscribing to necessary BLE characteristics.

        This method handles retries and updates the OLED display with connection status
        messages throughout the process. It loops until a successful connection and subscription
        sequence is completed or until it fails once if `retry_indefinitely` is False.

        Args:
            retry_indefinitely (bool): If True, the function will keep retrying the entire
                                       connection process indefinitely until success.
                                       If False, it will attempt once and return False on failure.
                                       Defaults to False.

        Returns:
            bool: True if connection, service discovery, and subscriptions were successful;
                  False if any step failed and retries are not enabled.

        Behavior:
            - Scans for a GoPro device.
            - Connects to the found device.
            - Discovers the GoPro BLE service.
            - Subscribes to the Command, Settings, and Query response characteristics.
            - Registers for specific status notifications (encoding, low temp, overheating).
            - Updates the OLED display with status messages at each step.
            - If any step fails, optionally retries after a short delay or exits based on `retry_indefinitely`.

        Side Effects:
            - May perform multiple retries with delays.
            - Updates the OLED display asynchronously to reflect connection progress.
        """ 
        from oled_display import update_display  # Import function here for lazy loading

        while True:
            update_display("Scanning...", "for GoPro")
            if not await self.scan_for_gopro():
                update_display("No GoPro", "found")
                if not retry_indefinitely:
                    return False
                await asyncio.sleep(2)
                continue

            update_display("Connecting", self.device_name or "")
            if not await self.connect():
                update_display("Conn.", "failed")
                if not retry_indefinitely:
                    return False
                await asyncio.sleep(2)
                continue

            update_display("Discovering", "services...")
            if not await self.discover_service():
                update_display("Service", "failed")
                await self.disconnect()
                if not retry_indefinitely:
                    return False
                await asyncio.sleep(2)
                continue

            update_display("Subscr.", "notif...")
            if not await self.subscribe_to_characteristics([GoProUuid.COMMAND_RSP_UUID]):
                update_display("Subscr.", "failed")
                await self.disconnect()
                if not retry_indefinitely:
                    return False
                await asyncio.sleep(2)
                continue

            if not await self.subscribe_to_characteristics([GoProUuid.SETTINGS_RSP_UUID]):
                update_display("Subscr.", "failed")
                await self.disconnect()
                if not retry_indefinitely:
                    return False
                await asyncio.sleep(2)
                continue

            if not await self.subscribe_to_characteristics([GoProUuid.QUERY_RSP_UUID], notify_queue_size=6):
                update_display("Subscr.", "failed")
                await self.disconnect()
                if not retry_indefinitely:
                    return False
                await asyncio.sleep(2)
                continue
            
            # Register for specific statuses
            await self.register_status_notifications([0x0A, 0x55, 0x06])

            return True  # Success