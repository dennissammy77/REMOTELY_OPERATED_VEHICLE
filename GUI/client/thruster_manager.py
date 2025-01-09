import threading
import time
import pygame
import requests
import socket

class THRUSTER_HANDLER():
    def __init__(self, ssh_conn, logger):
        super().__init__()
        self.ssh_conn = ssh_conn
        self.logger = logger

        self.ip_addr = '192.168.55.17'  # Ip Address connection
        self.ip_port = 8486  # Ip Address connection
        self.motor_socket = None
        self.controller = None

    def initialize(self):
        try:
            # Execute the video feed script
            # stdin, stdout, stderr = (
            self.ssh_conn.execute_command('python3 /home/sammy/ROV/thruster.py')
            # combined_output = stdout.read().decode('utf-8')
            # print(combined_output)

            self.motor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.motor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.motor_socket.connect((self.ip_addr, self.ip_port))
            print(f"Thruster Initialized")

            threading.Thread(target=self.updateControllerState).start()
            print(f"Thruster Initialized again")
            pygame.init()
            pygame.joystick.init()
            self.controller = pygame.joystick.Joystick(0)
            self.controller.init()

        except Exception as e:
            print(f"Thruster Error: {str(e)}")

    def updateControllerState(self):
        """
        PURPOSE
            Read input from XBOX controller with left stick for speed control and buttons for direction control.
        """
        try:
            if self.controller:
                pygame.event.pump()

                # Dictionary to store the state of buttons and axes
                controller_state = {
                    "buttons": {},
                    "axes": {}
                }

                # Get the left stick Y-axis value for speed control
                speed_axis = round(self.controller.get_axis(1), 2)  # Left stick Y-axis
                # Convert axis value (-1 to 1) to speed percentage (0 to 100) ; Adding deadzone of 0.1
                if abs(speed_axis) > 0.1:
                    speed = int(speed_axis * 100)  # Using absolute value for speed
                else:
                    speed = 0

                # Mapping for motor direction controls: These signify the placement of the motors on the ROV
                motor_map = {
                    0: f'top:speed:{speed}',  # A Button - Top motor forward
                    1: f'top:speed:{-speed}',  # B Button - Top motor reverse
                    2: f'rear:speed:{speed}',  # X Button - Rear motor forward
                    3: f'rear:speed:{-speed}',  # Y Button - Rear motor reverse
                    4: f'left:speed:{speed}',  # LB - Left motor forward
                    5: f'right:speed:{speed}',  # RB - Right motor forward
                    6: f'left:speed:{-speed}',  # Back - Left motor reverse
                    7: f'right:speed:{-speed}',  # Start - Right motor reverse
                }

                # Emergency stop mapping
                stop_map = {
                    10: 'STOP_ALL'  # Xbox Button - Emergency stop all motors
                }

                # Reading all button states
                for button_id in range(self.controller.get_numbuttons()):
                    if self.controller.get_button(button_id):
                        # Check for motor commands
                        if button_id in motor_map:
                            command = motor_map[button_id]
                            current_motor = command.split(':')[0]  # Extract motor name
                            direction = "forward" if ':speed:' in command and '-' not in command else "reverse"
                            self.logger.printTerminal(f"{current_motor} motor: {direction} at {speed}%")
                            self.send_motor_command(command)

                        # Check for emergency stop
                        elif button_id in stop_map:
                            command = stop_map[button_id]
                            self.logger.printTerminal("EMERGENCY STOP")
                            self.send_motor_command(command)

                    controller_state["buttons"][f"Button_{button_id}"] = self.controller.get_button(button_id)
        except Exception as e:
            print(f"Error in updateControllerState: {e}")

    def send_motor_command(self, command):
        """Send motor control commands to the Raspberry Pi."""
        if self.motor_socket:
            print(f"motor socket: {self.motor_socket}")
            try:
                self.motor_socket.sendall(command.encode())
            except socket.error as e:
                print(f"Error sending motor command: {e}")

    def stop_all_motors(self):
        """Emergency stop function for all motors"""
        self.send_motor_command("STOP_ALL")
