import asyncio
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

async def scan_makeblock_devices():
    """Scans for Bluetooth LE devices with names starting with 'Makeblock' and prints their information."""
    devices = await BleakScanner.discover()
    found_devices = False
    for d in devices:
        if d.name and d.name.startswith("Makeblock"):
            found_devices = True
            print("Found Makeblock Device:")
            print(f"  Address: {d.address}")
            print(f"  Name: {d.name}")
            print(f"  Details: {d.details}")  # Platform-specific details
            print(f"  Advertisement Data: {d.metadata}") # Replaced deprecated metadata
            print("-" * 20)
    return next((d for d in devices if d.name and d.name.startswith("Makeblock")), None)

async def connect_and_interact(device: BLEDevice):
    """Connects to the specified device and explores its services and characteristics."""
    if not device:
        print("No Makeblock device found to connect to.")
        return

    print(f"Connecting to {device.name} with address {device.address}...")
    try:
        async with BleakClient(device) as client:
            print(f"Connected: {client.is_connected}")

            # Get services and characteristics
            services = client.services
            print("Services:")
            for service in services:
                print(f"  {service.uuid}: {service.description}")
                for characteristic in service.characteristics:
                    print(f"    {characteristic.uuid}: {characteristic.description}, Properties: {characteristic.properties}")

                    # Example of reading a readable characteristic
                    if "read" in characteristic.properties:
                        try:
                            value = await client.read_gatt_char(characteristic)
                            print(f"      Value: {value}")
                        except Exception as e:
                            print(f"      Error reading: {e}")

                    # Example of subscribing to notifications (if supported)
                    if "notify" in characteristic.properties:
                        def callback(_, data):
                            print(f"      Notification received from {characteristic.uuid}: {data}")
                        try:
                            await client.start_notify(characteristic, callback)
                            print(f"      Subscribed to notifications for {characteristic.uuid}")
                            # Keep the connection alive for a bit to receive notifications
                            await asyncio.sleep(5)
                            await client.stop_notify(characteristic)
                            print(f"      Stopped notifications for {characteristic.uuid}")
                        except Exception as e:
                            print(f"      Error subscribing to notifications: {e}")

            print("Disconnecting...")

    except Exception as e:
        print(f"Error during connection or interaction: {e}")

async def main():
    try:
        makeblock_device = await scan_makeblock_devices()
        if makeblock_device:
            await connect_and_interact(makeblock_device)
    except KeyboardInterrupt:
        print("\nScanning and interaction stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
