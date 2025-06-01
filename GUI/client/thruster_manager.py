import threading
import time
import pygame
import requests
import socket
from PyQt5.QtCore import QThread
from client.ssh_connection import SSHWorker

class THRUSTER_HANDLER():
    def __init__(self, ssh_conn, logger, ip_addr):
        super().__init__()
        self.ssh_conn = ssh_conn
        self.logger = logger

        self.ip_addr = ip_addr  # Ip Address connection
        self.ip_port = 8486  # Ip Address connection
        self.motor_socket = None
        self.controller = None

        self.thread = None
        self.worker = None

    def initialize(self):
        try:
            # Execute the script
            # self.ssh_conn.execute_command('python3 /home/sammy/ROV/thruster.py')
            # Start the SSH command in a separate thread
            self.worker = SSHWorker(self.ssh_conn, 'python3 /home/sammy/ROV/thruster.py', self.logger)
            self.thread = QThread()
            self.worker.moveToThread(self.thread)

            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.error.connect(self.logger.log)
            self.worker.progress.connect(self.logger.log)

            self.thread.started.connect(self.worker.run)
            self.thread.start()

            # Add a small delay to ensure the server is up
            time.sleep(2)

            # self.motor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # print(self.motor_socket)
            # self.motor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # print(self.ip_addr)
            # print(self.ip_port)
            # self.motor_socket.connect((self.ip_addr, self.ip_port))


            #threading.Thread(target=self.updateControllerState).start()
            self.motor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"Attempting to connect to {self.ip_addr}:{self.ip_port}")

            self.motor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                # Add a timeout to prevent hanging
                self.motor_socket.settimeout(5)
                self.motor_socket.connect((self.ip_addr, self.ip_port))
                print("Socket connection successful")
                self.logger.log(f"Controller connection [initialize]: Success")
                pygame.init()
                pygame.joystick.init()
                self.controller = pygame.joystick.Joystick(0)
                self.controller.init()
            except socket.timeout:
                print("Connection timed out")
                raise
            except ConnectionRefusedError as conn_refuse:
                print(f"Detailed connection refused error: {conn_refuse}")
                # Additional debugging
                # self._check_server_status()
                raise
            # self.logger.log(f"Controller connection [initialize]: Success")
            # pygame.init()
            # pygame.joystick.init()
            # self.controller = pygame.joystick.Joystick(0)
            # self.controller.init()
        except ConnectionRefusedError as e:
            print(f"Connection refused: {e}")
        except Exception as e:
            self.logger.log(f"Controller connection [initialize]: {str(e)}")
            self.logger.printTerminal(f"Controller connection [initialize]: {str(e)}")
            raise Exception("Controller connection [initialize]")

    def disconnect_controller(self):
        """Kill the thruster.py script running on the Raspberry Pi."""
        try:
            # Find and kill the process running thruster.py
            find_command = "ps aux | grep '[t]hruster.py' | awk '{print $2}'"
            pid = self.ssh_conn.execute_command(find_command)
            #print(stdout)
            #pid = stdout.read().decode().strip()  # Get the process ID

            if pid:
                kill_command = f"kill -9 {pid}"
                self.ssh_conn.execute_command(kill_command)
                self.logger.log(f"Controller connection [disconnect_controller] (PID {pid}) has been terminated.")

            pygame.joystick.quit()
            pygame.quit()
            self.controller = None
        except Exception as e:
            self.logger.log(f"Controller connection [disconnect_controller]: {str(e)}")
            self.logger.printTerminal(f"Controller connection [disconnect_controller]: {str(e)}")
            raise Exception("Controller connection [disconnect_controller]")

    def updateControllerState(self):
        """
        PURPOSE
            Read input from XBOX controller with left stick for speed control and buttons for direction control.
        """
        try:
            if self.controller:
                #pygame.event.pump()

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
            self.logger.log(f"Controller connection [updateControllerState]: {e}")
            self.logger.printTerminal(f"Controller connection [updateControllerState]: {e}")
            raise Exception("Controller connection [updateControllerState]")


    def send_motor_command(self, command):
        """Send motor control commands to the Raspberry Pi."""
        if self.motor_socket:
            #self.logger.log(f"motor socket: {self.motor_socket}")
            try:
                self.motor_socket.sendall(command.encode())
            except socket.error as e:
                self.logger.printTerminal(f"Controller connection [send_motor_command]: {e}")
                self.logger.log(f"Controller connection [send_motor_command]: {e}")
                raise Exception("Controller connection [send_motor_command]")

    def stop_all_motors(self):
        """Emergency stop function for all motors"""
        self.send_motor_command("STOP_ALL")


"""
Debugging: 
1. check if the server script is running:
ps aux | grep thruster.py
2. Verify the listening port:
sudo netstat -tuln | grep <your_port>
3. stop the process, use the kill command with the process ID
sudo kill -9 <pid>
4. To find and kill all instances of a specific script, you can use:
pkill -f thruster.py
5. Brute Forcing
# List all Python processes running the script
pgrep -f "python3.*thruster.py"

# Kill all Python processes running the script
pkill -f "python3.*thruster.py"

# If that doesn't work, use more forceful method
sudo pkill -9 -f "python3.*thruster.py"

"""