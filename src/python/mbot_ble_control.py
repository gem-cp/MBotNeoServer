import asyncio
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
import keyboard  # Install using: pip install keyboard

# Replace with the actual UUIDs used in your mBot Neo CyberPi code
SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"  # Replace with your service UUID
TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Replace with your transmit characteristic UUID
RX_CHAR_UUID = "6E400002-B5A3-F393-E3A9-E50E24DCCA9E"  # Replace with your receive characteristic UUID

MBOT_SPEED = 40  # Define a default speed for movement
MAX_SCAN_RETRIES = 3
SCAN_RETRY_DELAY = 2  # seconds

async def send_command(client, command):
    """Sends a command to the mBot Neo."""
    try:
        await client.write_gatt_char(RX_CHAR_UUID, command.encode())
        print(f"Sent command: {command}")
    except Exception as e:
        print(f"Error sending command: {e}")

async def receive_data(characteristic, data):
    """Callback for receiving data from the mBot Neo."""
    print(f"Received data from {characteristic.uuid}: {data.decode()}")

async def control_mbot(client):
    """Controls the mBot Neo based on keyboard input."""
    print("Press arrow keys to control the mBot (up, down, left, right). Press 'q' to quit.")

    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            if event.name == 'up':
                await send_command(client, f"MOVE:forward,{MBOT_SPEED}")
            elif event.name == 'down':
                await send_command(client, f"MOVE:backward,{MBOT_SPEED}")
            elif event.name == 'left':
                await send_command(client, f"MOVE:left,{MBOT_SPEED}")
            elif event.name == 'right':
                await send_command(client, f"MOVE:right,{MBOT_SPEED}")
            elif event.name == 'q':
                break
        elif event.event_type == keyboard.KEY_UP:
            if event.name in ['up', 'down', 'left', 'right']:
                await send_command(client, "MOVE:stop")  # Send stop command when key is released

async def main():
    scan_retries = 0
    while True:  # Outer loop for reconnection attempts
        print("Scanning for mBot Neo...")
        try:
            devices = await BleakScanner.discover()
            mbot_neo_device = None
            for d in devices:
                # Accessing service UUIDs from metadata (for Bleak <= 0.22)
                service_uuids = [str(uuid_obj) for uuid_obj in d.metadata.get("uuids", [])]

                # Check if the device name exists before calling lower()
                if d.name and "mbotneo" in d.name.lower() or SERVICE_UUID.lower() in service_uuids:
                    mbot_neo_device = d
                    print(f"Found mBot Neo: {mbot_neo_device.name} ({mbot_neo_device.address})")
                    break

            if mbot_neo_device:
                print(f"Connecting to {mbot_neo_device.address}...")
                try:
                    async with BleakClient(mbot_neo_device) as client:
                        print("Connected!")
                        await client.start_notify(TX_CHAR_UUID, receive_data)
                        await control_mbot(client)  # Your control logic
                        await client.stop_notify(TX_CHAR_UUID)
                        print("Disconnected.")
                        break  # Exit the outer loop if control_mbot finishes normally

                except Exception as e:
                    print(f"Error during connection or communication: {e}")
                    print("Attempting to reconnect in 1 second...")
                    await asyncio.sleep(1)
                    continue # Continue the outer loop to try scanning and connecting again

            else:
                print("mBot Neo not found.")
                scan_retries += 1
                if scan_retries < MAX_SCAN_RETRIES:
                    print(f"Retrying scan in {SCAN_RETRY_DELAY} seconds (Attempt {scan_retries}/{MAX_SCAN_RETRIES})...")
                    await asyncio.sleep(SCAN_RETRY_DELAY)
                else:
                    print(f"Max scan retries reached ({MAX_SCAN_RETRIES}). Exiting.")
                    break # Exit if max retries reached

        except BleakError as e:
            if "Bluetooth device is turned off" in str(e):
                print(f"BleakError: Bluetooth device is turned off. Please turn it on.")
                scan_retries += 1
                if scan_retries < MAX_SCAN_RETRIES:
                    print(f"Retrying scan in {SCAN_RETRY_DELAY} seconds (Attempt {scan_retries}/{MAX_SCAN_RETRIES})...")
                    await asyncio.sleep(SCAN_RETRY_DELAY)
                else:
                    print(f"Max scan retries reached ({MAX_SCAN_RETRIES}). Please check Bluetooth and try again.")
                    break # Exit if max retries reached
            else:
                print(f"An unexpected BleakError occurred: {e}")
                break # Exit for other Bleak errors
        except Exception as e:
            print(f"An unexpected error occurred during scanning: {e}")
            break # Exit for other unexpected errors

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting.")