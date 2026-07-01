# The code scans for Makeblock devices and connects to the first one found.
# It then reads keyboard input to control the mBot Neo. The control logic is based
# on the WASD keys for forward, backward, left, and right movements, respectively.
# Pressing 'q' quits the program. The motor speeds are set to 180 units for full
# speed in either direction. The build_joystick_command function constructs the
# command packet to control the mBot Neo's motors. The process_key_input function
# maps the WASD keys to motor speeds. The main function loads the device address
# from a configuration file, scans for Makeblock devices, and connects to the mBot
# Neo for control. If the device address is found in the configuration file, it
# attempts to connect directly to that device. If the device is not found, it
# saves the address of the discovered device to the configuration file for future
# use. The asyncio.run(main()) call starts the main coroutine, which handles the
# connection and control logic. The program can be interrupted by the user with a
# keyboard interrupt (Ctrl+C).
# The code uses the Bleak library to interact with Bluetooth Low Energy (BLE)

import asyncio
import sys
import termios
import tty
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
import struct
import yaml
import os
import logging

# Logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = "mbot_config.yaml"
MBOT_CAR_CONTROLLER = 0x02  # Device ID for mBot Neo motor control (tentative, verify from docs if needed)
MOTOR_MOVE_COMMAND = 0x05 # Command for controlling multiple motors

# Command prefixes and suffixes
PREFIX = b'\xff\x55'
SUFFIX = b'\x0d\x0a'

command_index = 0  # Global index counter

async def scan_makeblock_devices():
    """Scans for Bluetooth LE devices with names starting with 'Makeblock'."""
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name and d.name.startswith("Makeblock"):
            logging.info(f"Found Makeblock Device: {d.name}, Address: {d.address}")
            return d
    logging.warning("No Makeblock devices found.")
    return None

def get_char():
    """Gets a single character from standard input."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def build_joystick_command(left_speed: int, right_speed: int) -> bytearray:
    """Builds the command to control the mBot motors according to the protocol."""
    global command_index
    index = command_index % 256  # Keep index within 0-255
    command_index += 1
    action = MOTOR_MOVE_COMMAND  # Use specific command for motor control

    payload = bytearray()
    payload.append(0x01) # Motor ID 1
    payload.extend(struct.pack("<h", right_speed)) # Motor 1 speed
    payload.append(0x02) # Motor ID 2
    payload.extend(struct.pack("<h", left_speed))  # Motor 2 speed

    length = 1 + len(payload)  # Length of command + data

    command = bytearray(PREFIX)
    command.append(length)
    command.append(index)
    command.append(action)
    command.extend(payload)
    command.extend(SUFFIX)
    logging.debug(f"Built command: {command.hex()}")
    return command

async def send_command(client: BleakClient, command: bytearray):
    """Sends the command to the mBot over BLE."""
    try:
        if client.is_connected:
            write_uuid = "0000ffe3-0000-1000-8000-00805f9b34fb"
            await client.write_gatt_char(write_uuid, command, response=False)
            logging.debug(f"Sent command: {command.hex()}")
        else:
            logging.error("Client is not connected.")
    except Exception as e:
        logging.error(f"Failed to send command: {e}")

async def connect_and_control(device: BLEDevice):
    """Connects to the device and allows keyboard-based control."""
    if not device:
        logging.error("No Makeblock device found.")
        return False

    try:
        async with BleakClient(device) as client:
            logging.info(f"Connected to {device.name} ({device.address}).")
            logging.info("Use 'w', 'a', 's', 'd' to control the mBot. Press 'q' to quit.")

            while True:
                char = get_char()
                left_speed, right_speed = process_key_input(char)
                if char == 'q':
                    break

                command = build_joystick_command(left_speed, right_speed)
                await send_command(client, command)
                await asyncio.sleep(0.1) # ചെറിയ കാലതാമസം ചേർക്കുന്നു

            # Stop motors before disconnecting
            await send_command(client, build_joystick_command(0, 0))
            logging.info("Disconnected.")
            return True

    except Exception as e:
        logging.error(f"Connection error: {e}")
        return False

def process_key_input(char):
    """Processes keyboard input and returns motor speeds."""
    speed = 200  # Adjust speed as needed
    if char == 'w':
        return speed, speed
    elif char == 's':
        return -speed, -speed
    elif char == 'a':
        return -speed, speed
    elif char == 'd':
        return speed, -speed
    return 0, 0

async def main():
    device_address = None

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
            device_address = config.get('device_address')
            logging.info(f"Loaded device address from config: {device_address}")

    try:
        device = None
        if device_address:
            device = await BleakScanner.find_device_by_address(device_address, timeout=5.0)
            if not device:
                logging.warning(f"Device with address {device_address} not found. Initiating scan...")

        if not device:
            device = await scan_makeblock_devices()

        if device:
            with open(CONFIG_FILE, 'w') as f:
                yaml.dump({'device_address': str(device.address)}, f, default_flow_style=False)
                logging.info(f"Saved device address to config file: {device.address}")

            await connect_and_control(device)

    except KeyboardInterrupt:
        logging.info("Interrupted by user.")
    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())