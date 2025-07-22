# L.A.U.R.A. CONTROLLER Ver.3 - ble_handler.py
from logger_utils import print_warning, print_error, print_debug
from commands import GoProUuid

_callbacks = []  # List of registered coroutine callbacks for BLE event notifications

# Stores ResponseAccumulator instances keyed by characteristic UUID,
# used to reassemble fragmented BLE packets per characteristic
response_accumulators = {}

# Mapping of generic BLE response result codes to human-readable strings
RESULT_MESSAGES = {
    0x00: "success",
    0x01: "error",
    0x02: "invalid_parameter",
}

# Maps command IDs to descriptive names for easier debugging and parsing
COMMAND_MAPPINGS = {
    0x01: "set_shutter",
    0x05: "sleep",
    0x17: "set_ap_control",
    0x3E: "preset_group",
    0x5B: "keep_alive",
}

# Maps setting IDs to descriptive names for interpreting BLE settings responses
SETTINGS_MAPPINGS = {
    0x02: "video_resolution",
    0x03: "frame_per_second",
    0x3B: "auto_power_down",
    0x40: "preset",
    0x53: "gps",
    0x79: "video_lens",
}

# Defines known status identifiers returned by GoPro query responses,
# including their human-readable names and expected data types
STATUS_DEFINITIONS = {
    0x01: {"name": "battery_present", "type": "bool"},
    0x02: {"name": "internal_battery_bars", "type": "int"},
    0x06: {"name": "system_hot", "type": "bool"},
    0x0A: {"name": "recording_status", "type": "bool"},
    0x11: {"name": "wireless_enabled", "type": "bool"},
    0x1E: {"name": "access_point_ssid", "type": "string"},
    0x21: {"name": "primary_storage", "type": "int"},
    0x22: {"name": "wifi_scan_state", "type": "int"},
    0x23: {"name": "remaining_video_time", "type": "int"},
    0x27: {"name": "videos", "type": "int"},
    0x46: {"name": "internal_battery_percentage", "type": "int"},
    0x55: {"name": "low_temp", "type": "bool"},
    0x59: {"name": "flatmode", "type": "int"},
    0x5D: {"name": "video_preset", "type": "int"},
    0x5E: {"name": "photo_preset", "type": "int"},
    0x5F: {"name": "timelapse_preset", "type": "int"},
    0x60: {"name": "preset_group", "type": "int"},
    0x61: {"name": "preset", "type": "int"},
    # Add additional status definitions here as needed
}

# Set of (feature_id, action_id) tuples representing protobuf-encoded BLE responses,
# used to identify which BLE packets should be processed as protobuf data
PROTOBUF_IDS = {
    (0x02, 0x02), (0x02, 0x03), (0x02, 0x04), (0x02, 0x05),
    (0x02, 0x0B), (0x02, 0x0C), (0x02, 0x82), (0x02, 0x83),
    (0x02, 0x84), (0x02, 0x85), (0x03, 0x01), (0x03, 0x81),
    (0xF1, 0x64), (0xF1, 0x65), (0xF1, 0x66), (0xF1, 0x67),
    (0xF1, 0x69), (0xF1, 0x6B), (0xF1, 0x79), (0xF1, 0xE4),
    (0xF1, 0xE5), (0xF1, 0xE6), (0xF1, 0xE7), (0xF1, 0xE9),
    (0xF1, 0xEB), (0xF1, 0xF9), (0xF5, 0x6D), (0xF5, 0x6E),
    (0xF5, 0x6F), (0xF5, 0x72), (0xF5, 0x74), (0xF5, 0xED),
    (0xF5, 0xEE), (0xF5, 0xEF), (0xF5, 0xF2), (0xF5, 0xF3),
    (0xF5, 0xF4), (0xF5, 0xF5),
}

def is_protobuf_response(feature_id: int, action_id: int) -> bool:
    """
    Check if the given feature and action IDs correspond to a protobuf-encoded response.

    Args:
        feature_id (int): Feature identifier.
        action_id (int): Action identifier.

    Returns:
        bool: True if the pair matches known protobuf response IDs, False otherwise.
    """
    return (feature_id, action_id) in PROTOBUF_IDS

def register_callback(cb):
    """
    Register a coroutine callback to receive BLE notification events.

    Each callback will be invoked with two arguments: event_type (str) and data (dict).

    Args:
        cb (coroutine function): Callback coroutine to register.
    """
    _callbacks.append(cb)
    
# --- TLV Response Reassembly Logic --- #

class ResponseAccumulator:
    """
    Accumulates fragmented BLE TLV response packets and reassembles them into full messages.

    Tracks sequence numbers to detect missing or out-of-order packets and supports
    multiple header formats defining payload length.

    Attributes:
        buffer (bytearray): Accumulated payload bytes.
        expected_length (int or None): Total expected length of the full message.
        expected_seq (int): Sequence number expected for next continuation packet.
        receiving (bool): Flag indicating if currently receiving a multi-packet message.
    """
    def __init__(self):
        self.buffer = bytearray()
        self.expected_length = None  # Total expected length of the full message payload
        self.expected_seq = 0        # Expected continuation sequence number (increments with each continuation packet)
        self.receiving = False       # Are we in the middle of receiving a multi-packet message?

    def reset(self):
        """Reset the accumulator to initial empty state."""
        self.buffer = bytearray()  # MicroPython-compatible
        self.expected_length = None
        self.expected_seq = 0
        self.receiving = False

    def is_complete(self):
        """
        Determine if the full message has been accumulated.

        Returns:
            bool: True if the buffer length is at least the expected payload length.
        """
        if self.expected_length is None:
            return False

        current_length = len(self.buffer)
        is_full = current_length >= self.expected_length
        return is_full

    def add(self, data):
        """
        Add a new BLE packet to the accumulator, handling headers and continuation.

        Args:
            data (bytes or bytearray): Incoming BLE packet to process.

        Notes:
            - First byte indicates header type or continuation and sequence number.
            - Resets if sequence numbers mismatch or packet is malformed.
        """
        print_debug(f"[BLE] Accumulator received packet: {data.hex()}")
        
        if not data:
            print_warning("[BLE] Empty packet received, ignoring.")
            return

        first_byte = data[0]
        first_byte_bin = f"{first_byte:08b}"
        is_continuation = (first_byte & 0x80) != 0
        seq_num = first_byte & 0x7F  # Lower 7 bits = sequence number
        
        print_debug(f"[BLE] First byte: 0x{first_byte:02X} (binary: {first_byte_bin})")

        if not is_continuation:
            # New message start packet
            header_type = (first_byte >> 5) & 0x03

            if header_type == 0b00:  # General header with 5-bit length
                self.expected_length = first_byte & 0x1F
                payload_start = 1
            elif header_type == 0b01:  # Extended 13-bit length
                if len(data) < 2:
                    print_warning("[BLE] Packet too short for 13-bit length header, discarding.")
                    self.reset()
                    return
                self.expected_length = ((first_byte & 0x1F) << 8) + data[1]
                payload_start = 2
            elif header_type == 0b10:  # Extended 16-bit length
                if len(data) < 3:
                    print_warning("[BLE] Packet too short for 16-bit length header, discarding.")
                    self.reset()
                    return
                self.expected_length = (data[1] << 8) + data[2]
                payload_start = 3
            else:
                print_error(f"[BLE] Unknown header type in first byte: {first_byte:02x}")
                self.reset()
                return

            # Start fresh with new payload
            self.buffer = bytearray(data[payload_start:])
            self.expected_seq = 0  # Expect next continuation packet to have seq=0
            self.receiving = True
            
            print_debug(f"[BLE] Accumulator buffer length: {len(self.buffer)} / expected {self.expected_length}")

        else:
            # Continuation packet - verify sequence number
            if not self.receiving:
                # We got a continuation packet without starting a new message - discard
                print_warning(f"[BLE] Unexpected continuation packet seq={seq_num} without active message. Discarding.")
                self.reset()
                return

            if seq_num != self.expected_seq:
                # Sequence mismatch - packets lost or out of order
                print_error(f"[BLE] Sequence mismatch! Expected seq={self.expected_seq}, got seq={seq_num}. Resetting buffer.")
                self.reset()
                return

            # Append payload (skip first byte)
            self.buffer.extend(data[1:])
            self.expected_seq += 1
            
            print_debug(f"[BLE] Accumulator buffer length: {len(self.buffer)} / expected {self.expected_length}")

def get_accumulator(uuid):
    """
    Retrieve or create a ResponseAccumulator for a given characteristic UUID.

    Args:
        uuid (UUID): BLE characteristic UUID.

    Returns:
        ResponseAccumulator: The accumulator instance for the UUID.
    """
    if uuid not in response_accumulators:
        response_accumulators[uuid] = ResponseAccumulator()
    return response_accumulators[uuid]

async def handle_ble_notification(char_uuid, data):
    """
    Handle incoming BLE notifications, performing packet reassembly and dispatch.

    Args:
        char_uuid (UUID): UUID of the characteristic that generated the notification.
        data (bytes): The notification payload.

    Behavior:
        - Uses ResponseAccumulator to reassemble fragmented data.
        - Dispatches complete messages to the appropriate handler based on UUID.
    """
    acc = get_accumulator(char_uuid)
    acc.add(data)

    if not acc.is_complete():
        # Still waiting for more packets
        return

    # Once complete, forward to the appropriate handler and reset accumulator
    reassembled_data = acc.buffer
    acc.reset()

    # strip "UUID('" from start and "')" from end
    uuid_str = str(char_uuid)
    if uuid_str.startswith("UUID('") and uuid_str.endswith("')"):
        uuid_str = uuid_str[6:-2]
    uuid_str = uuid_str.lower()

    # Simple dispatch based on characteristic UUID string (adjust your UUID names accordingly)
    expected_command_rsp = GoProUuid.COMMAND_RSP_UUID.lower()
    expected_settings_rsp = GoProUuid.SETTINGS_RSP_UUID.lower()
    expected_query_rsp = GoProUuid.QUERY_RSP_UUID.lower()

    if uuid_str == expected_command_rsp:
        await handle_command_response(char_uuid, reassembled_data)
    elif uuid_str == expected_settings_rsp:
        await handle_settings_response(char_uuid, reassembled_data)
    elif uuid_str == expected_query_rsp:
        await handle_query_response(char_uuid, reassembled_data)
    else:
        print_warning(f"[BLE] Unknown UUID received: {char_uuid}")

async def handle_command_response(char_uuid, data):
    """
    Parse and log the response for a command sent to the GoPro.

    Args:
        char_uuid (UUID): UUID of the characteristic that sent the response.
        data (bytes): The command response data payload.

    Behavior:
        - Parses command ID and result code.
        - Logs and notifies registered callbacks.
    """
    if len(data) < 2:
        print_error(f"Incomplete command response: {data.hex()}")
        return

    command_id, result_code = data[:2]

    command_name = COMMAND_MAPPINGS.get(command_id, f"Unknown Command ({command_id})")
    result_message = RESULT_MESSAGES.get(result_code, f"Unknown Result ({result_code})")

    print_debug(f"[BLE] Command response: {command_name} → {result_message}")
    parsed_result = {
        "command_id": command_id,
        "command_name": command_name,
        "result": result_message,
    }

    # Notify registered callbacks
    for cb in _callbacks:
        try:
            await cb("command_response", parsed_result)
        except Exception as e:
            print_error(f"Callback error: {e}")

    return parsed_result

async def handle_settings_response(char_uuid, data):
    """
    Parse and log the response for a settings request sent to the GoPro.

    Args:
        char_uuid (UUID): UUID of the characteristic that sent the response.
        data (bytes): The settings response data payload.

    Behavior:
        - Parses setting ID and result code.
        - Logs and notifies registered callbacks.
    """
    if len(data) < 2:
        print_error(f"[BLE] Incomplete settings response: {data.hex()}")
        return

    setting_id, result_code = data[:2]

    setting_name = SETTINGS_MAPPINGS.get(setting_id, f"Unknown Setting ({setting_id})")
    result_message = RESULT_MESSAGES.get(result_code, f"Unknown Result ({result_code})")

    print_debug(f"[BLE] Settings response: {setting_name} → {result_message}")
    parsed_result = {
        "setting_id": setting_id,
        "setting_name": setting_name,
        "result": result_message,
    }

    # Notify registered callbacks
    for cb in _callbacks:
        try:
            await cb("setting_response", parsed_result)
        except Exception as e:
            print_error(f"Callback error: {e}")

    return parsed_result

async def handle_query_response(char_uuid, data):
    """
    Parse and process status query responses from the GoPro.

    Args:
        char_uuid (UUID): UUID of the characteristic that sent the response.
        data (bytes): The query response data payload.

    Behavior:
        - Parses TLV-encoded status entries.
        - Logs unknown status IDs.
        - Notifies registered callbacks.
    """
    print_debug(f"[BLE] Reassembled data received in handle_query_response: {data.hex()}")
    statuses = {}

    if len(data) < 5:
        print_error(f"[BLE] Incomplete query response: {data.hex()}")
        return statuses

    index = 2

    while index + 2 <= len(data):
        try:
            status_id = data[index]
            length = data[index + 1]

            if index + 2 + length > len(data):
                break

            value = data[index + 2 : index + 2 + length]

            # Get definition from combined STATUS_DEFINITIONS map
            definition = STATUS_DEFINITIONS.get(status_id)

            if definition:
                value_type = definition["type"]

                # Parse based on type
                if value_type == "bool":
                    decoded = bool(int.from_bytes(value, "big"))
                elif value_type == "int":
                    decoded = int.from_bytes(value, "big")
                elif value_type == "string":
                    decoded = value.decode("utf-8", errors="ignore")
                else:
                    decoded = value  # fallback raw bytes

                # Store by name
                status_key = definition["name"]
                statuses[status_key] = decoded
            else:
                print_warning(f"[BLE] Unknown status ID {status_id:02X} in query response.")

            index += 2 + length

        except Exception as e:
            print_error(f"[BLE] Error decoding TLV entry: {repr(e)}")
            break

    for cb in _callbacks:
        try:
            await cb("query_response", statuses)
        except Exception as e:
            print_error(f"Callback error: {e}")

    return statuses
