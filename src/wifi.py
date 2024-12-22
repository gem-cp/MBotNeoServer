"""
Script to connect mBot Neo to a Wi-Fi network using credentials from a config.yaml file 
and display the IP address on the CyberPi screen.

Requirements:
- mBot Neo with CyberPi module.
- Installed CyberPi library.
- A config.yaml file with Wi-Fi credentials.

Author: [Your Name]
Date: [Today's Date]
"""

import cyberpi
import time
import yaml

def load_config(file_path):
    """
    Loads Wi-Fi credentials from a config.yaml file.

    Args:
        file_path (str): Path to the config.yaml file.

    Returns:
        dict: A dictionary containing the Wi-Fi SSID and password.
    """
    try:
        with open(file_path, "r") as file:
            config = yaml.safe_load(file)
            return config.get("wifi", {})
    except FileNotFoundError:
        cyberpi.display.show_label("Config file not found!", 24, "center", index=0)
        time.sleep(2)
        cyberpi.display.clear()
        raise
    except yaml.YAMLError as e:
        cyberpi.display.show_label("Error reading config!", 24, "center", index=0)
        time.sleep(2)
        cyberpi.display.clear()
        raise e


def connect_to_wifi(ssid, password):
    """
    Connects the mBot Neo to a Wi-Fi network.

    Args:
        ssid (str): The Wi-Fi network name (SSID).
        password (str): The Wi-Fi network password.
    """
    cyberpi.wifi.connect(ssid, password)
    while not cyberpi.wifi.is_connect():
        cyberpi.display.show_label("Connecting...", 24, "center", index=0)
        time.sleep(1)

    cyberpi.display.clear()
    cyberpi.display.show_label("Connected!", 24, "center", index=0)
    time.sleep(2)
    cyberpi.display.clear()


def display_ip_address():
    """
    Displays the current IP address of the mBot Neo on the CyberPi screen.
    """
    ip_address = cyberpi.wifi.get_ip()
    if ip_address:
        cyberpi.display.show_label(f"IP: {ip_address}", 24, "center", index=0)
    else:
        cyberpi.display.show_label("No IP Address", 24, "center", index=0)


def main():
    """
    Main function to connect to Wi-Fi and display the IP address.
    """
    config = load_config("config.yaml")
    ssid = config.get("ssid")
    password = config.get("password")

    if not ssid or not password:
        cyberpi.display.show_label("Missing credentials!", 24, "center", index=0)
        time.sleep(2)
        cyberpi.display.clear()
        return

    cyberpi.display.show_label("Starting...", 24, "center", index=0)
    time.sleep(1)
    cyberpi.display.clear()

    connect_to_wifi(ssid, password)
    display_ip_address()


if __name__ == "__main__":
    main()