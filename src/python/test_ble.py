import asyncio
import sys
import termios
import tty
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
import struct

known_device_address = None  # Hier kann eine gespeicherte Adresse eingefügt werden
MBOT_CAR_CONTROLLER = 40 #Type des Gerätes, welches angesteuert wird


async def scan_makeblock_devices():
    """Scans for Bluetooth LE devices with names starting with 'Makeblock' and returns the first device found."""
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name and d.name.startswith("Makeblock"):
            print("Found Makeblock Device:")
            print(f" Address: {d.address}")
            print(f" Name: {d.name}")
            print(f" Details: {d.details}")  # Platform-specific details
            print(f" Advertisement Data: {d.metadata}")  # Replaced deprecated metadata
            print("-" * 20)
            return d
    return None


def get_char():
    """Gets a single character from standard input."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def build_joystick_command(left_speed: int, right_speed: int) -> bytearray:
    """Builds the command to control the mBot motors."""
    cmd = bytearray()
    cmd.extend(b'\xff\x55')
    cmd.append(8)  # length of data, 8 = 2x short
    cmd.append(0)
    cmd.append(2) # action
    cmd.append(MBOT_CAR_CONTROLLER) # device type
    cmd.extend(struct.pack("<h", left_speed)) #left motor
    cmd.extend(struct.pack("<h", right_speed)) #right motor
    cmd.append(10)  # '\n'
    return cmd

async def send_command(client: BleakClient, command: bytearray):
        """Sends the command to the mBot over BLE"""
        if client and client.is_connected:
            try:
                # Hier musst du die richtige Characteristic auswählen
                # für das Schreiben von Daten.
                # Prüfe die UUIDs der Services und Characteristics mit `connect_and_interact`
                # aus dem vorherigen Beispiel.
                for service in client.services:
                    for characteristic in service.characteristics:
                         if "write" in characteristic.properties and  characteristic.uuid.startswith("0000ffe1"):
                            await client.write_gatt_char(characteristic, command, response=False)
                            return
                print("No write characteristic found")

            except Exception as e:
                print(f"Error sending command: {e}")
        else:
            print("Not connected.")


async def connect_and_control(device: BLEDevice):
    """Connects to the specified device and controls it via keyboard input."""
    if not device:
        print("No Makeblock device found to connect to.")
        return

    print(f"Connecting to {device.name} with address {device.address}...")
    try:
        async with BleakClient(device) as client:
            print(f"Connected: {client.is_connected}")
            print("Use 'w', 'a', 's', 'd' to control the mBot. Press 'q' to quit.")
            while True:
                char = get_char()
                left_speed = 0
                right_speed = 0

                if char == 'w':
                    left_speed = 180
                    right_speed = 180
                elif char == 's':
                    left_speed = -180
                    right_speed = -180
                elif char == 'a':
                     left_speed = -180
                     right_speed = 180
                elif char == 'd':
                    left_speed = 180
                    right_speed = -180
                elif char == 'q':
                    break # Beende die Steuerung

                if char == 'w' and get_char() == 'a':
                  left_speed = 80
                  right_speed = 180
                elif char == 'w' and get_char() == 'd':
                  left_speed = 180
                  right_speed = 80
                elif char == 's' and get_char() == 'a':
                  left_speed = -80
                  right_speed = -180
                elif char == 's' and get_char() == 'd':
                  left_speed = -180
                  right_speed = -80


                command = build_joystick_command(left_speed,right_speed)
                await send_command(client, command)
            # Stop motors after leaving control loop
            stop_command = build_joystick_command(0,0)
            await send_command(client, stop_command)
            print("Disconnecting...")

    except Exception as e:
        print(f"Error during connection or interaction: {e}")


async def main():
    global known_device_address

    try:
        if known_device_address:
            try:
                device = await BleakScanner.find_device(known_device_address)
                if device:
                    print(f"Attempting direct connection to known device at address: {known_device_address}")
                    await connect_and_control(device)
                    return
                else:
                  print(f"Device at {known_device_address} not found. Initiating scan...")
                  known_device_address = None
            except Exception as e:
              print(f"Error during direct connection attempt: {e}. Initiating scan...")
              known_device_address = None

        makeblock_device = await scan_makeblock_devices()
        if makeblock_device:
             known_device_address = makeblock_device.address
             await connect_and_control(makeblock_device)

    except KeyboardInterrupt:
        print("\nScanning and interaction stopped by user.")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())