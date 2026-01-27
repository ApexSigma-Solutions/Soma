#!/usr/bin/env python3
"""
Test server to verify port 8768 is working
"""

import socket
import threading


def handle_client(client_socket):
    """Handle a client connection"""
    try:
        request = client_socket.recv(1024)
        print(f"Received: {request.decode('utf-8')}")

        # Send HTTP response
        response = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nmemOS.MCP Test Server Running on Port 8768"
        client_socket.send(response)
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()


def start_server():
    """Start a simple TCP server on port 8768"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind(("0.0.0.0", 8768))
        server.listen(5)
        print("Test server listening on port 8768...")

        while True:
            client_socket, addr = server.accept()
            print(f"Accepted connection from {addr}")
            client_handler = threading.Thread(
                target=handle_client, args=(client_socket,)
            )
            client_handler.start()

    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server.close()


if __name__ == "__main__":
    print("Starting test server on port 8768...")
    start_server()
