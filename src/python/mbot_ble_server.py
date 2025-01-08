from cyberpi import *
import ubluetooth
import time
import gc
import event
import cyberpi
import mbuild
import random

# Bluetooth configuration
NAME = "mBotNeo"
UART_SERVICE_UUID = ubluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
UART_TX_CHAR_UUID = ubluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")  # Data to central
UART_RX_CHAR_UUID = ubluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")  # Commands from central

# Sensor update interval (in milliseconds)
SENSOR_UPDATE_INTERVAL = 500

# Motor state constants
MOTOR_STOPPED = 0
MOTOR_FORWARD = 1
MOTOR_BACKWARD = 2

class BluetoothPeripheral:
    def __init__(self):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)
        ((self.handle_tx, self.handle_rx,), (self.handle_uart,),) = self._register_services()
        self._payload = bytearray()
        self._connections = set()
        self._advertise()
        self.motor_left_state = MOTOR_STOPPED
        self.motor_right_state = MOTOR_STOPPED

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("New connection", conn_handle)
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            print("Disconnected", conn_handle)
            self._connections.discard(conn_handle)
            # Start advertising again to allow new connections
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle == self.handle_rx:
                command = self.ble.gatts_read(self.handle_rx)
                self._process_command(command.decode('utf-8').strip())

    def _register_services(self):
        service = (UART_SERVICE_UUID, [(UART_TX_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY, (20,),),
                                      (UART_RX_CHAR_UUID, ubluetooth.FLAG_WRITE, (20,),)])
        ((handle_tx, handle_rx,), (handle_uart,),) = self.ble.gatts_register_services((service,))
        return handle_tx, handle_rx, handle_uart

    def _advertise(self):
        adv_payload = self._advertising_payload(name=NAME, services=[UART_SERVICE_UUID])
        self.ble.gap_advertise(100, adv_payload)
        print("Advertising...")

    def _advertising_payload(self, limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
        payload = bytearray()

        def _append(adv_type, value):
            nonlocal payload
            payload += struct.pack("BB", len(value) + 1, adv_type)
            payload += value

        _append(0x01, bytes((0x05 if limited_disc else 0x04)) +
                (bytes((0x00, 0x00)) if br_edr else bytes((0x06, 0x00))))

        if name:
            _append(0x09, name.encode())

        if services:
            for uuid in services:
                b = bytes(uuid)
                if len(b) == 2:
                    _append(0x03, b)
                elif len(b) == 16:
                    _append(0x06, b)

        if appearance:
            _append(0x19, struct.pack("<h", appearance))

        return payload

    def send_data(self, data):
        for conn_handle in self._connections:
            self.ble.gatts_notify(conn_handle, self.handle_tx, data)

    def _process_command(self, command):
        print("Received command:", command)
        parts = command.split(':')
        if len(parts) == 2:
            command_type = parts[0].upper()
            value = parts[1].strip()

            if command_type == "M1":  # Motor 1 speed
                try:
                    speed = int(value)
                    motor1.speed(speed)
                    self.motor_left_state = MOTOR_FORWARD if speed > 0 else (MOTOR_BACKWARD if speed < 0 else MOTOR_STOPPED)
                except ValueError:
                    print("Invalid motor 1 speed:", value)
            elif command_type == "M2":  # Motor 2 speed
                try:
                    speed = int(value)
                    motor2.speed(speed)
                    self.motor_right_state = MOTOR_FORWARD if speed > 0 else (MOTOR_BACKWARD if speed < 0 else MOTOR_STOPPED)
                except ValueError:
                    print("Invalid motor 2 speed:", value)
            elif command_type == "LED": # Control onboard LED (example: LED:R-255-G-0-B-0)
                led_parts = value.split('-')
                if len(led_parts) == 6 and led_parts[0].upper() == 'R' and led_parts[2].upper() == 'G' and led_parts[4].upper() == 'B':
                    try:
                        r = int(led_parts[1])
                        g = int(led_parts[3])
                        b = int(led_parts[5])
                        led.on(r, g, b)
                    except ValueError:
                        print("Invalid LED values:", value)
                else:
                    print("Invalid LED command format:", value)
            elif command_type == "BUZZER": # Control buzzer (example: BUZZER:1000-0.5) - frequency, duration
                buzzer_parts = value.split('-')
                if len(buzzer_parts) == 2:
                    try:
                        freq = int(buzzer_parts[0])
                        duration = float(buzzer_parts[1])
                        speaker.play_tone(freq, duration)
                    except ValueError:
                        print("Invalid buzzer values:", value)
                else:
                    print("Invalid buzzer command format:", value)
            else:
                print("Unknown command:", command_type)
        else:
            print("Invalid command format:", command)

    def get_sensor_data(self):
        distance = ultrasonic2.get_value()
        motor_status = f"M1:{self.motor_left_state},M2:{self.motor_right_state}"
        return f"DIST:{distance},MOTORS:{motor_status}"

def turn_off_quad_rgb():
    """Turns off all LEDs on the quad RGB sensor."""
    # Set the RGB values for each LED to black (0, 0, 0)
    mbuild.quad_rgb_sensor.close_led(1)
    print("Quad RGB sensor LEDs turned off.")

def check_memory():
    allocated_memory = gc.mem_alloc() / 1024
    free_memory = gc.mem_free() / 1024
    total_memory = allocated_memory + free_memory
    cyberpi.console.println("Alloc: %d kb" % allocated_memory)
    cyberpi.console.println("Free: %d kb" % free_memory)
    cyberpi.console.println("Total: %d kb" % total_memory)

# Initialize mBot Bluetooth peripheral object
mBotBle = BluetoothPeripheral()
last_sensor_update = time.ticks_ms()

@event.start
def on_start():
    turn_off_quad_rgb()
    cyberpi.led.show('black black black black black')
    check_memory()
    cyberpi.console.print("Press > to start.")

# Button b is >
@event.is_press('b')
def is_btn_press_b():
    global mBotBle, last_sensor_update
    cyberpi.led.on(0, 0, 100, id=3)
    while True:
        if time.ticks_diff(time.ticks_ms(), last_sensor_update) >= SENSOR_UPDATE_INTERVAL:
            sensor_data = mBotBle.get_sensor_data()
            mBotBle.send_data(sensor_data.encode('utf-8'))
            last_sensor_update = time.ticks_ms()
        time.sleep_ms(50)


# Button a is >
@event.is_press('a')
def is_btn_press_a():
    
    cyberpi.led.on(0, 0, 100, id=1)
    cyberpi.led.on(0, 0, 100, id=5)


