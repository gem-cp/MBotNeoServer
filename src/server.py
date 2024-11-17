import socket
import threading
from mbuild import power_expand_board  # Assuming you're using mbuild

# MBot Neo setup (same as before)
power_expand = power_expand_board.power_expand_board()

def process_command(command, client_socket):
    """Handles commands from the client."""
    parts = command.split()
    if not parts:
        return "No command received"

    action = parts[0].lower()
    # ... (command processing logic from your USB example) ...
    response = "..." # Build your response based on the action
    client_socket.send(response.encode('utf-8'))

def handle_client(client_socket, address):
    """Handles a single client connection."""
    print(f"Accepted connection from {address}")
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                break
            command = data.decode('utf-8').strip()
            process_command(command, client_socket)
        except ConnectionResetError:
            print(f"Connection with {address} reset")
            break
    client_socket.close()

def start_server():
    """Starts the server and listens for connections."""
    host = ''  # Listen on all available interfaces
    port = 5555  # Choose a port

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)  # Queue up to 5 connections

    print(f"Server listening on port {port}")

    while True:
        client_socket, address = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
        client_thread.start()

if __name__ == "__main__":
    start_server()