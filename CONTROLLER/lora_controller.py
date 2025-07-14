# L.A.U.R.A. Ver.2 - lora_controller.py
import uasyncio as asyncio
from machine import Pin, SPI
import struct
import config
from logger_utils import print_info, print_warning, print_error, print_debug

def get_async_modem():
    from lora import AsyncSX1262

    # Initialize the SPI interface
    spi = SPI(1, baudrate=2000000, polarity=0, phase=0, sck=Pin(9), mosi=Pin(10), miso=Pin(11))
    cs = Pin(8, Pin.OUT)

    # Initialize and return the Async LoRa modem
    return AsyncSX1262(
        spi, cs,
        busy=Pin(13),
        dio1=Pin(14),
        reset=Pin(12),
        dio3_tcxo_millivolts=1800,
        lora_cfg=config.LORA_CONFIG  # Use the imported LoRa configuration
    )

async def recv_coro(modem, local_id, handle_message):
    """ LoRa receive function """
    while True:
        rx = await modem.recv(800)  # Timeout reduced to 480 ms

        if rx:

            if len(rx) < 5:
                print_error("[LoRa] Error: Received packet is too short, skipping...")

                continue
            
            try:
                sender_id, receiver_id, payload_length = struct.unpack('>HHB', rx[:5])
            except struct.error:
                print_error("[LoRa] Error: Failed to unpack the header, skipping...")
                continue

            if receiver_id != local_id:
                print_debug(f"[LoRa] Message not addressed to this device (Local ID: {local_id}). Skipping...")
                continue

            if len(rx) < 5 + payload_length:
                print_error(f"[LoRa] Error: Incomplete payload. Expected {5 + payload_length} bytes, received {len(rx)} bytes.")
                continue

            payload = rx[5:5 + payload_length]

            received_data = {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "payload": payload,
                "rssi": rx.rssi,
                "snr": rx.snr,
                "packet_length": len(rx),
            }

            print_debug(f"[LoRa ID:{sender_id}] Received message {payload!r}, RSSI: {rx.rssi}, SNR: {rx.snr}, Length: {len(rx)}")

            try:
                handle_message(received_data)
            except Exception as e:
                print_error(f"[LoRa] Error in handle_message callback: {e}")

async def send_coro(modem, local_id, receiver_id, payload):
    """ LoRa send function """
    payload_length = len(payload)
    header = struct.pack('>HHB', local_id, receiver_id, payload_length)

    full_message = bytearray(len(header) + len(payload))
    full_message[:len(header)] = header
    full_message[len(header):] = payload

    print_debug(f"[LoRa ID:{receiver_id}] Sending message: {payload}")

    await modem.send(full_message)

def handle_message(received_data):
    """ Handles received messages """
    sender_id = received_data["sender_id"]
    payload = received_data["payload"]
    
    if not isinstance(payload, (bytes, bytearray)):
        print_error(f"[LoRa] Error: Payload is not in the expected format: {type(payload)}")
        return

async def main():
    local_id = config.DEVICE_UID
    receiver_id = config.REMOTE_UID
    print_debug(f"[LoRa] Starting LoRa test script with Local ID: {local_id}")

    modem = get_async_modem()

    async def periodic_sender():
        while True:
            payload = f"Local ID: {local_id}".encode()
            await send_coro(modem, local_id, receiver_id, payload)
            await asyncio.sleep(5)

    await asyncio.gather(
        recv_coro(modem, local_id, handle_message),
        periodic_sender(),
    )

if __name__ == "__main__":
    asyncio.run(main())

