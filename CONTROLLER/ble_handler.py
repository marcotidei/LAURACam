# Shared result messages for commands and settings
RESULT_MESSAGES = {
    0x00: "Success",
    0x01: "Error",
    0x02: "Invalid Parameter",
}

# Command-specific mappings
COMMAND_MAPPINGS = {
    0x01: "Shutter",
    0x05: "Sleep",
    0x3E: "Preset Group",
}

# Settings-specific mappings
SETTINGS_MAPPINGS = {
    0x02: "Resolution",
    0x03: "Framerate",
    0x40: "Preset",
    0x3B: "Auto Powerdown",
    0x53: "GPS",
    0x79: "Video Lens",
}

async def handle_command_response(char_uuid, data):
    """Handles responses from the COMMAND_RSP_UUID characteristic."""
    if len(data) < 3:
        print(f"Incomplete command response: {data.hex()}")
        return
    
    response_length, command_id, result_code = data[:3]

    if response_length != len(data) - 1:
        print("Invalid command response length.")
        return

    command_name = COMMAND_MAPPINGS.get(command_id, f"Unknown Command ({command_id})")
    result_message = RESULT_MESSAGES.get(result_code, f"Unknown Result ({result_code})")

    print(f"Command response: {result_message}")
    return {"command_id": command_id, "command_name": command_name, "result": result_message}

async def handle_settings_response(char_uuid, data):
    """Handles responses from the SETTINGS_RSP_UUID characteristic."""
    if len(data) < 3:
        print(f"Incomplete settings response: {data.hex()}")
        return
    
    response_length, setting_id, result_code = data[:3]

    if response_length != len(data) - 1:
        print("Invalid settings response length.")
        return

    setting_name = SETTINGS_MAPPINGS.get(setting_id, f"Unknown Setting ({setting_id})")
    result_message = RESULT_MESSAGES.get(result_code, f"Unknown Result ({result_code})")

    print(f"Setting response: {result_message}")
    return {"setting_id": setting_id, "setting_name": setting_name, "result": result_message}

async def handle_query_response(char_uuid, data):
    """Handles responses from the QUERY_RSP_UUID characteristic."""
    statuses = {}  # Dictionary to store detected statuses

    if len(data) < 6:
        print(f"Incomplete query response: {data.hex()}")
        return statuses  # Return an empty dictionary if data is incomplete

    # print(f"Query Response Received: {data.hex()}")

    index = 3  
    while index < len(data):
        notification_id = data[index]  
        value_length = data[index + 1]  
        value_bytes = data[index + 2:index + 2 + value_length]  

        if len(value_bytes) != value_length:
            print(f"Invalid value length: {data.hex()}")
            break  

        value = bool(int.from_bytes(value_bytes, "big"))  # Convert to boolean
        index += 2 + value_length  

        if notification_id == 0x0A:  # Recording status
            statuses["recording_status"] = value

        elif notification_id == 0x06:  # Overheating status
            statuses["system_hot"] = value

        elif notification_id == 0x55:  # Low temperature warning
            statuses["low_temp"] = value

    return statuses  # Return only detected statuses
