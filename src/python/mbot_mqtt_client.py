# Import required modules
import gc
import event
import cyberpi
import time
import mbuild
import random
import network

# Global flag to stop tasks
ultrasonic_publishing_enabled = False
mqtt_connected = False  # Track MQTT connection status

@event.start
def on_start():
    ssid = "ssid"
    password = "password"
    turn_off_quad_rgb()
    cyberpi.led.show('black black black black black')
    if not connect_to_wifi(ssid, password):
        cyberpi.led.on(250, 0, 0, id=3)
        cyberpi.console.println("Wi-Fi connection failed. Aborting.")
    else:
        cyberpi.led.on(0, 0, 100, id=3)
        check_memory()
        cyberpi.console.print("Press > to start.")
        

# Button b is >
@event.is_press('b')
def is_btn_press_b():
    global ultrasonic_publishing_enabled, mqtt_connected

    mqtt_client_id = "mBot_Neo"
    mqtt_server = "192.168.2.63"
    mqtt_port = 1883
    mqtt_topics = ["mBot/Chat", "mBot/Display", "mBot/Motor"]

    cyberpi.mqtt.set_broker(mqtt_client_id, mqtt_server, mqtt_port)
    is_connected = cyberpi.mqtt.connect()
    if is_connected:
        mqtt_connected = True
        cyberpi.console.println("Connected to MQTT broker.")
        for topic in mqtt_topics:
            cyberpi.mqtt.subscribe_message(topic)
        cyberpi.console.println("Subscribed to topics")
        cyberpi.mqtt.set_callback(mqtt_message_received)
        cyberpi.led.on(0, 0, 250, id=3)
        if not ultrasonic_publishing_enabled:
            ultrasonic_publishing_enabled = True
            start_ultrasonic_publisher()
    else:
        cyberpi.console.println("Failed to connect to MQTT broker %s:%d" % (mqtt_server, mqtt_port))
        cyberpi.led.on(250, 0, 0, id=3)

def check_memory():
    allocated_memory = gc.mem_alloc() / 1024
    free_memory = gc.mem_free() / 1024
    total_memory = allocated_memory + free_memory
    cyberpi.console.println("Alloc: %d kb" % allocated_memory)
    cyberpi.console.println("Free: %d kb" % free_memory)
    cyberpi.console.println("Total: %d kb" % total_memory)
    
def generate_random_suffix(length=6):
    """Generate a random alphanumeric string."""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(chars[random.randint(0, len(chars) - 1)] for _ in range(length))

def connect_to_wifi(ssid, password):
    """
    Connect to the Wi-Fi network (blocking).
    """
    if not cyberpi.wifi.is_connect():
        cyberpi.wifi.connect(ssid, password)
        cyberpi.led.on(0, 0, 50, id=3)
        cyberpi.console.println("Connecting to Wi-Fi...")

    time_waited = 0.0
    while not cyberpi.wifi.is_connect():
        time.sleep(0.1)
        time_waited += 0.1
        if time_waited > 15.0:
            cyberpi.console.println("Wi-Fi connection failed")
            cyberpi.led.on(200, 0, 0, id=1)
            return False
    cyberpi.led.on(0, 0, 100, id=3)
    cyberpi.console.println("Wi-Fi connected.")
    return True

def start_ultrasonic_publisher():
    """
    Starts the ultrasonic publisher loop.
    """
    global ultrasonic_publishing_enabled, mqtt_connected
    while ultrasonic_publishing_enabled:
        # Rely on the mqtt_connected flag instead of cyberpi.mqtt.is_connect()
        if mqtt_connected:
            distance = mbuild.ultrasonic2.get(1)  # Replace '1' with the correct port number
            cyberpi.mqtt.publish_message("mBot/Ultrasonic", str(distance))
            cyberpi.console.println("us:%d" % distance)
        else:
            cyberpi.console.println("MQTT connection lost.")
        time.sleep(1.0)

def mqtt_message_received(topic, payload):
    """
    Handle MQTT messages to control mBot movement with command:value payloads.
    """
    cyberpi.console.print("Topic:" + str(topic) + ", Payload:" + str(payload))
    if topic == "mBot/Motor":
        try:
            command, value = payload.split(":")
            value = int(value)
            if command == "forward":
                mbot2.forward(value)
            elif command == "backward":
                mbot2.backward(value)
            elif command == "turn":
                mbot2.turn(value)
            elif command == "stop":
                mbot2.set_motor(0, 0)
            else:
                cyberpi.console.print("Unknown command.")
        except ValueError:
            cyberpi.console.print("Invalid payload format. Expected 'command:value'.")
    else:
        cyberpi.console.print("Unknown topic.")

@event.is_press('a')
def is_btn_press_a():
    """
    Stop ultrasonic publishing and disconnect from MQTT and Wi-Fi.
    """
    global ultrasonic_publishing_enabled, mqtt_connected
    ultrasonic_publishing_enabled = False
    if mqtt_connected:
        cyberpi.mqtt.off()
        cyberpi.console.print("Disconnected from MQTT.")
        mqtt_connected = False
    cyberpi.led.show('black black black black black')
    cyberpi.led.on(0, 0, 50, id=3)


def turn_off_quad_rgb():
    """Turns off all LEDs on the quad RGB sensor."""
    # Set the RGB values for each LED to black (0, 0, 0)
    mbuild.quad_rgb_sensor.close_led(1)
    print("Quad RGB sensor LEDs turned off.")