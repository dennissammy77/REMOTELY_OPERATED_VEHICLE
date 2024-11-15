# !/usr/bin/env python3
# Modules
import RPi.GPIO as GPIO
from time import sleep
import socket
import threading

GPIO.setwarnings(False)  # disable warnings
GPIO.setmode(GPIO.BCM)  # Use GPIO pin number
GPIO.setup(16, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(18, GPIO.OUT)
GPIO.setup(15, GPIO.OUT)

GPIO.output(16, GPIO.LOW)
GPIO.output(22, GPIO.LOW)
GPIO.output(11, GPIO.LOW)
GPIO.output(13, GPIO.LOW)
GPIO.output(18, GPIO.LOW)
GPIO.output(15, GPIO.LOW)

def move(direction,pin):
    GPIO.output(pin, GPIO.HIGH)
    sleep(1)
    print("Motor init")
    GPIO.output(pin, GPIO.LOW)

def handle_client(client_socket):
    try:
        while True:
            command = client_socket.recv(1024).decode()
            pin_map = {
                'Up': 11,  # A Button
                'Down': 13,  # B Button
                'Left': 15,  # X Button
                'Right': 18,  # Y Button
                'Forward': 16,  # LB
                'Backward': 22,  # RB
            }
            if command in pin_map and pin_map.get(command) is not None:
                print(f"Motor moving: {command}")
                move(command,pin_map.get(command))
            else:
                print("Motor stopping")
                GPIO.output(16, GPIO.LOW)
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()

def thruster_setup():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8486))
    server_socket.listen(5)
    print("Thruster control server listening")

    while True:
        client, addr = server_socket.accept()
        print(f"Connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client,))
        client_handler.start()

# Command line execution
if __name__ == '__main__':
    thruster_setup()
