
try:
    import os, sys
    import io
    import json
    import requests
    import socket
    import pickle
    import struct
    import random
    import serial
    import pygame
    import numpy as np
    from PyQt5 import uic
    from PyQt5.QtWidgets import (QMainWindow, QApplication,
                                 QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QTextEdit, QSizePolicy)
    from PyQt5 import QtGui
    from PyQt5.QtGui import QImage, QPixmap, QFont
    from PyQt5.QtCore import QTimer, Qt, QSize, QThread, pyqtSignal
    from datetime import datetime
    import paramiko
    import cv2
    import threading

except:
    sys.exit("\n###################################################################################################"
             "\nSome libraries are missing! Run the 'install_libraries.bat' file to install the required libraries."
             "\n###################################################################################################")

def getResourcePath(relativePath):
    """
        Get absolute path to resource, works for dev and for PyInstaller
    """
    try:
        # PYINSTALLER CREATES A TEMP FOLDER AND STORES PATH IN _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")
    return os.path.join(basePath, relativePath)

class UIWINDOW(QMainWindow):
    """
        Contains functions to initiate the GUI, link the widgets and connect all the signals/slots
        from external libraries together.
    """

    def __init__(self, app):
        """
            Class constructor.
            Loads GUI, call functions to initiate all the libraries and connects the signal/slots together.

            INPUT: app: QApplication object (required to allow theme changing).
        """
        super(UIWINDOW, self).__init__()

        # LOAD UI FILE
        uiFile = getResourcePath("gui.ui")
        uic.loadUi(uiFile, self)

        self.app = app
        self.initUI()

        # INITIATE OBJECTS
        self.initiateObjects()

        # Set up a timer to check the controller state
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateControllerState)
        self.timer.start(50)  # Check every 50 milliseconds

        # INITIAL STARTUP MESSAGE
        self.printTerminal("Welcome to the control interface.")
        self.printTerminal("Connect to the ROV and CONTROLLER to get started.")

        # LAUNCH GUI

    def initUI(self):
        """
            Initializes the user interface.
        """
        self.setWindowTitle("ROV Control Interface")

    def initiateObjects(self):
        """
            Initiates buttons and their slots.
        """
        # Serial connection to the Raspberry PI setup
        self.isConnected = False
        self.ssh_client = None
        self.pi_hostname = 'raspberrypi.local'  # Replace with your Raspberry Pi's IP
        self.username = 'sammy'  # Raspberry Pi username
        self.password = 'password'  # Raspberry Pi password
        self.ip_addr = '192.168.115.17' # Ip Address connection

        '''
            UTIL SETUP
        '''
        self.timer = QTimer()
        '''
            ROV SETUP
        '''
        # connect button
        self.rovConnectButton = self.findChild(QPushButton, 'control_rov_connect')
        self.rovConnectButton.clicked.connect(self.toggleROVConnection)

        '''
            CONTROLLER SETUP
        '''
        # connect button

        self.connectControllerButton = self.findChild(QPushButton, 'control_controller_connect')
        self.connectControllerButton.clicked.connect(self.toggleControllerConnection)
        self.controller = None
        # Set up a timer to check the controller state

        '''
            GUI TERMINAL SETUP
        '''
        self.terminalTextEdit = self.findChild(QTextEdit, 'terminalOutputLabel')
        if not self.terminalTextEdit:
            print("Error: terminalTextEdit not found. Please check the name in the .ui file.")

        '''
            THRUSTER SETUP
        '''
        self.client_socket = None
        self.motor_socket = None
        # Find the thruster labels and buttons
        self.thrusterSpeedLabels = [
            self.findChild(QLabel, f'thruster{i}SpeedLabel') for i in range(1, 7)
        ]
        self.thrusterTestButtons = [
            self.findChild(QPushButton, f'thruster{i}TestButton') for i in range(1, 7)
        ]
        self.thrusterStatusLabels = [
            self.findChild(QLabel, f'thruster{i}StatusLabel') for i in range(1, 7)
        ]

        # Connect buttons to their functions
        for i, button in enumerate(self.thrusterTestButtons):
            button.clicked.connect(lambda _, x=i + 1: self.testThruster(x))

        '''
            CAMERA SETUP
        '''
        # Connect Button
        self.CameraConnectButton = self.findChild(QPushButton, 'camera_connect')
        self.CameraConnectButton.clicked.connect(self.toggleCameraConnection)

        # Video Feed
        self.video_label = self.findChild(QLabel, 'videoFeedLabel')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMaximumSize(806,1094)  # Set max size to control growth


        # Timer to periodically fetch video frames
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(60)  # Update every 30 ms (~30 FPS)

        # Flask video stream URLs
        self.video_url = f"http://{self.ip_addr}:5001/video_feed"  # Replace with your Flask server IP
        self.shutdown_url = f"http://{self.ip_addr}:5001/shutdown"  # Replace with your Flask server IP

        self.video_feed_active=False
        '''
            SENSORS SETUP
        '''
        self.SensorConnectButton = self.findChild(QPushButton, 'sensor_connect')
        self.SensorConnectButton.clicked.connect(self.toggleSensorConnection)
        # SENSORS
        self.sensors_socket = None
        self.sensor_client_socket = None

        self.temperatureLabel = self.findChild(QLabel, 'temperatureLabel')
        self.pitchLabel = self.findChild(QLabel, 'pitchLabel')
        self.rollLabel = self.findChild(QLabel, 'rollLabel')
        self.yawLabel = self.findChild(QLabel, 'yawLabel')
        self.accelerationLabel = self.findChild(QLabel, 'accelerationLabel')

    def getScreenSize(self):
        """
        Gets the width and height of the screen.

        RETURNS:
        - width: Width of screen in pixels.
        - height: Height of screen in pixels.
        """
        sizeObject = QtGui.QGuiApplication.primaryScreen().availableGeometry(-1)
        screenWidth = sizeObject.width()
        screenHeight = sizeObject.height()

        return screenWidth, screenHeight

    def printTerminal(self, text):
        """
        PURPOSE

        Prints text to the serial terminal on the configuration tab.

        INPUT

        - text = the text to display on the serial terminal

        RETURNS

        NONE
        """

        currentText = self.terminalTextEdit.toPlainText()
        newText = f"{datetime.now().strftime('%H:%M:%S')} -> {text}\n"
        self.terminalTextEdit.setPlainText(currentText + newText)
        self.terminalTextEdit.verticalScrollBar().setValue(self.terminalTextEdit.verticalScrollBar().maximum())

    '''
        SYSTEM SETUP
    '''
    def toggleROVConnection(self):
        """
            Toggles between connecting and disconnecting the Raspberry Pi to the GUI over Ethernet.
        """
        if self.isConnected:
            self.disconnectFromROV()
        else:
            self.connectToROV()

    def connectToROV(self):
        """
            Establishes an SSH connection to the Raspberry Pi using its hostname over Ethernet.
        """
        try:
            # Create SSH Client && Establish the serial connection
            self.ssh_client = paramiko.SSHClient()
            if self.ssh_client:
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_client.connect(self.pi_hostname, username=self.username, password=self.password)

                self.isConnected = True
                self.printTerminal("Connected to ROV over SSH")
                # Video Feed

                # self.ssh_client.exec_command('python3 /home/sammy/ROV/video_feed.py')

                # THRUSTERS

                stdin, stdout, stderr = self.ssh_client.exec_command('python3 /home/sammy/ROV/thruster.py')
                combined_output = stdout.read().decode('utf-8')
                print(combined_output)

                threading.Thread(target=self.updateControllerState).start()

                self.motor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.motor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.motor_socket.connect((self.ip_addr, 8486))  # Pi's IP address and port

                # SENSORS
                # self.ssh_client.exec_command('python3 /home/sammy/ROV/sensors.py')
                #
                # stdin, stdout, stderr = self.ssh_client.exec_command('python3 /home/sammy/ROV/thruster.py')
                # combined_output = stdout.read().decode('utf-8')
                # print(combined_output)
                #
                # self.sensors_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # self.sensors_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # self.sensors_socket.connect((self.ip_addr, 8487))  # Pi's IP address and port

                # self.sensors_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # self.sensors_socket.connect((self.ip_addr, 8487))  # Pi's IP address and port

                # Update button style to show disconnection option
                self.rovConnectButton.setText("DISCONNECT")
                self.rovConnectButton.setStyleSheet("""
                    background-color: red;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)
            else:
                self.printTerminal("No ROV system detected.")
                self.rovConnectButton("""
                    background-color: grey;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)
            # Camera
        except Exception as e:
            self.ssh_client.close()
            self.printTerminal(f"Failed to connect to ROV over SSH: {e}")

    def disconnectFromROV(self):
        """
            Closes the SSH connection to the Raspberry Pi over ETHERNET.
        """
        try:
            # Update button style to show connection option
            self.isConnected = False
            self.printTerminal("Disconnected from ROV.")
            self.rovConnectButton.setText("CONNECT")
            self.rovConnectButton.setStyleSheet("""
                background-color: green;
                color: white;
                border-radius: 20px;
                font-weight: bold;
                padding: 10px;
            """)

            '''
            # Attempt to gracefully shut down the server first
            shutdown_url = "http://192.168.16.104:5001/shutdown"  # Update with the correct IP
            try:
                response = requests.get(shutdown_url)
                print(response.text)
            except Exception as e:
                print(f"Error shutting down the server gracefully: {e}")

                # If the graceful shutdown fails, kill the process
                print("Attempting to kill the process directly...")
                stdin, stdout, stderr = self.ssh_client.exec_command('pgrep -f video_feed.py')
                pid = stdout.read().strip()

                if pid:
                    # Kill the process using the PID
                    kill_command = f'kill {pid}'
                    self.ssh_client.exec_command(kill_command)
                    print(f"Video feed process with PID {pid} has been killed.")
                else:
                    print("No process found for video_feed.py")
            finally:
                if self.ssh_client:
                    self.ssh_client.close()
                    self.isConnected = False
                    self.printTerminal("Disconnected from ROV")

                    # Update button style to show connection option
                    self.rovConnectButton.setText("CONNECT")
                    self.rovConnectButton.setStyleSheet("""
                                    background-color: green;
                                    color: white;
                                    border-radius: 20px;
                                    font-weight: bold;
                                    padding: 10px;
                                """)
            '''
        except Exception as e:
            self.printTerminal(f"Failed to disconnect from ROV: {e}")

    '''
        CONTROLLER SETUP
    '''
    def toggleControllerConnection(self):
        """
            Toggles the connection state of the Xbox controller.
        """
        if self.controller:
            # DisConnect the controller
            pygame.joystick.quit()
            pygame.quit()
            self.controller = None
            self.connectControllerButton.setText("CONNECT")
            self.printTerminal("Controller disconnected.")
            self.connectControllerButton.setStyleSheet("""
                background-color: green;
                color: white;
                border-radius: 20px;
                font-weight: bold;
                padding: 10px;
            """)
        else:
            # Connect the controller
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.controller = pygame.joystick.Joystick(0)
                self.controller.init()
                '''
                    # Start the thruster program
                    stdin, stdout, stderr = self.ssh_client.exec_command('python3 /home/sammy/ROV/thruster.py')
                    # Replace with the correct path to your file
    
                    # Print any errors from the server start
                    print(stdout.read().decode())
                    print(stderr.read().decode())
    
                    threading.Thread(target=self.updateControllerState).start()
    
                    self.motor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.motor_socket.connect(('192.168.16.104', 8486))  # Pi's IP address and port
                '''

                self.connectControllerButton.setText("DISCONNECT")
                self.connectControllerButton.setStyleSheet("""
                    background-color: red;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)
                self.printTerminal("Controller connected.")
            else:
                self.printTerminal("No controller detected.")
                self.connectControllerButton.setStyleSheet("""
                    background-color: grey;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)

    def updateControllerState(self):
        """
        PURPOSE
            Read input from XBOX controller with left stick for speed control and buttons for direction control.
        """
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
                        self.printTerminal(f"{current_motor} motor: {direction} at {speed}%")
                        self.send_motor_command(command)

                    # Check for emergency stop
                    elif button_id in stop_map:
                        command = stop_map[button_id]
                        self.printTerminal("EMERGENCY STOP")
                        self.send_motor_command(command)

                controller_state["buttons"][f"Button_{button_id}"] = self.controller.get_button(button_id)
        '''
            # Store axis states for monitoring
            for axis_id in range(self.controller.get_numaxes()):
                controller_state["axes"][f"Axis_{axis_id}"] = round(self.controller.get_axis(axis_id), 2)

            # Mapping for button actions
            direction_map = {
                0: 'Up',  # A Button
                1: 'Down',  # B Button
                2: 'Left',  # X Button
                3: 'Right',  # Y Button
                4: 'Forward',  # LB
                5: 'Backward',  # RB
            }

            # Reading all button states
            for button_id in range(self.controller.get_numbuttons()):
                if self.controller.get_button(button_id):
                    current_direction = direction_map.get(button_id)
                    self.printTerminal(f"Moving {current_direction}")

                    if current_direction is not None:
                        self.send_motor_command(current_direction)
                        self.printTerminal("command sent")

                controller_state["buttons"][f"Button_{button_id}"] = self.controller.get_button(button_id)

            # Reading all axis states (e.g., sticks and triggers)
            for j in range(self.controller.get_numaxes()):
                controller_state["axes"][f"Axis_{j}"] = round(self.controller.get_axis(j), 2)

            #print(controller_state)
        '''
    '''
        SENSORS SETUP
    '''
    def handle_sensors(self):
        try:
            full_data = ""
            while True:
                # Receive the data
                sensor_data_json = self.sensors_socket.recv(1024).decode()  # Decode the received data
                # Append received data to full_data
                full_data += sensor_data_json

                # Deserialize JSON string to dictionary
                sensor_values = json.loads(full_data)

                # Deserialize JSON string to dictionary
                temperature = sensor_values['temp']
                pitch = sensor_values['pitch']
                roll = sensor_values['roll']
                yaw = sensor_values['yaw']
                accel_x = sensor_values['accel-x']

                full_data = ""
                # Update the temperature value
                self.temperatureLabel.setText(str(format(temperature,".2f")))
                self.pitchLabel.setText(str(format(pitch, ".2f")))
                self.rollLabel.setText(str(format(roll, ".2f")))
                self.yawLabel.setText(str(format(yaw, ".2f")))
                self.accelerationLabel.setText(str(format(accel_x, ".2f")))

        except Exception as e:
            self.printTerminal(f"Error handling sensors: {e}")
            self.sensors_socket.close()
        finally:
            self.printTerminal(f"Sensors Disconnected")
            self.sensors_socket.close()

    ''' CAMERA SOCKET HANDLERS
    def start_feed(self):
        """Start the camera feed in a separate thread."""
        """Connect to the Raspberry Pi and start receiving frames."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(('192.168.16.104', 8485))  # Pi's IP address and port
            self.timer.start(30)  # Start the timer to fetch frames
            threading.Thread(target=self.update_video_feed()).start()
            # self.update_video_feed()
        except Exception as e:
            print(f"Error connecting to Raspberry Pi: {e}")

    def stop_feed(self):
        """Handle widget close event."""
        if self.client_socket:
            self.client_socket.close()
    def update_video_feed(self):
        """Receive video frames from Raspberry Pi and update the QLabel."""

        data = b""
        payload_size = struct.calcsize("Q")

        try:
            while len(data) < payload_size:
                packet = self.client_socket.recv(4 * 1024)  # Receive packet
                if not packet:
                    print("No more data from the server.")
                    return
                data += packet

            # Unpack the frame size from the received data
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            if not packed_msg_size:
                return
            msg_size = struct.unpack("Q", packed_msg_size)[0]
            print("Receiving frames:", msg_size)

            # Ensure the message size is realistic
            if msg_size > 10 * 1024 * 1024:  # 10 MB limit
                print("Frame size exceeds the limit!")
                return

            while len(data) < msg_size:
                data += self.client_socket.recv(4 * 1024)

            frame_data = data[:msg_size]

            # Deserialize frame data
            frame = pickle.loads(frame_data)
            print(frame)

            # Convert the frame to RGB and QImage
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            print(bytes_per_line)
            qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

            # Update the QLabel with the new frame
            pixmap = QPixmap.fromImage(qimg)
            scaled_pixmap = pixmap.scaled(self.videoFeedLabel.size())
            self.videoFeedLabel.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error receiving frame: {e}")
            self.client_socket.close()
    '''

    '''
        THRUSTER SETUP
    '''
    def send_motor_command(self, command):
        """Send motor control commands to the Raspberry Pi."""
        if self.motor_socket:
            try:
                self.motor_socket.sendall(command.encode())
            except socket.error as e:
                print(f"Error sending motor command: {e}")

    def stop_all_motors(self):
        """Emergency stop function for all motors"""
        self.send_motor_command("STOP_ALL")

    def updateThrusterSpeeds(self):
        # Simulate thruster speed readings (replace with actual readings)
        for i in range(6):
            speed = random.uniform(0.0, 100.0)  # Replace with actual speed reading
            self.thrusterSpeedLabels[i].setText(f"{speed:.2f} RPM")
    def testThruster(self, thrusterId):
        # Simulate a thruster test (replace with actual test logic)
        print(f"Testing Thruster {thrusterId}")
        self.printTerminal(f"Testing Thruster {thrusterId}")

    def flashOnboardLED(self):
        """
        Executes a Python script on the Raspberry Pi to flash the onboard LED 3 times.
        """
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command("python3 /home/sammy/ROV/flash_led.py")
            stdout.channel.recv_exit_status()  # Wait for the command to complete
            output = stdout.read().decode()
            error = stderr.read().decode()

            if output:
                self.printTerminal(f"LED Flash Output: {output}")
            if error:
                self.printTerminal(f"LED Flash Error: {error}")

        except Exception as e:
            self.logTerminal(f"Failed to flash LED: {str(e)}")

    '''
        CAMERA SETUP
    '''
    def toggleCameraConnection(self):
        """
            Toggles between connecting and disconnecting the camera to the GUI
        """
        if self.isConnected and self.video_feed_active is False:
            self.connectToVideoServer()
        elif self.video_feed_active and self.isConnected:
            self.disconnectFromVideoServer()
        else:
            self.printTerminal("Connect to the ROV first")

    def connectToVideoServer(self):
        try:
            # Start the video feed server
            stdin, stdout, stderr = self.ssh_client.exec_command('python3 /home/sammy/ROV/video_feed.py')
            # Replace with the correct path to your file

            # Print any errors from the server start
            print(stdout.read().decode())
            print(stderr.read().decode())

            threading.Thread(target=self.update_frame).start()

            self.printTerminal("Feed connected to video server")
            self.video_feed_active = True

            # Update style to show disconnection option
            self.CameraConnectButton.setText("DISCONNECT")
            self.CameraConnectButton.setStyleSheet("""
                background-color: red;
                color: white;
                border-radius: 20px;
                font-weight: bold;
                padding: 10px;
            """)
        except Exception as e:
            self.printTerminal(f"Error while connecting to video server:{e}.")
            self.CameraConnectButton("""
                background-color: grey;
                color: white;
                border-radius: 20px;
                font-weight: bold;
                padding: 10px;
            """)

    def disconnectFromVideoServer(self):
        try:
            response = requests.get(self.shutdown_url)
            self.printTerminal(response.text)
        except Exception as e:
            self.printTerminal(f"Error shutting down the video server gracefully: {e}")

            # If the graceful shutdown fails, kill the process
            self.printTerminal("Attempting to kill the process directly...")
            stdin, stdout, stderr = self.ssh_client.exec_command('pgrep -f video_feed.py')
            pid = stdout.read().strip()

            if pid:
                # Kill the process using the PID
                kill_command = f'kill {pid}'
                self.ssh_client.exec_command(kill_command)
                self.printTerminal(f"Video feed process with PID {pid} has been killed.")
            else:
                self.printTerminal("No process found for video_feed.py")
        finally:
            self.printTerminal("Disconnected from video server.")
            self.CameraConnectButton("""
                background-color: green;
                color: white;
                border-radius: 20px;
                font-weight: bold;
                padding: 10px;
            """)

    def update_frame(self):
        # Fetch the video frame from the Flask server
        try:
            img_resp = requests.get(self.video_url, stream=True)
            bytes_data = b""
            for chunk in img_resp.iter_content(chunk_size=1024):
                bytes_data += chunk
                a = bytes_data.find(b'\xff\xd8')  # JPEG start
                b = bytes_data.find(b'\xff\xd9')  # JPEG end
                if a != -1 and b != -1:
                    jpg = bytes_data[a:b + 2]
                    bytes_data = bytes_data[b + 2:]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    self.display_image(frame)
        except Exception as e:
            print(f"Error fetching video stream: {e}")

    def display_image(self, frame):
        # Convert the frame to a format QPixmap can handle
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Update the QLabel with the new frame
        pixmap = QPixmap.fromImage(qt_image)
        # Resize the QPixmap to fit the QLabel while maintaining the aspect ratio
        pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio)

        # Display the QPixmap on the QLabel
        self.video_label.setPixmap(pixmap)

    def toggleSensorConnection(self):
        """
            Toggles between connecting and disconnecting the sensors to the GUI
        """
        if self.isConnected:
            self.connectToSensor()
        else:
            self.printTerminal("Connect to the ROV first")
        '''
                if self.isConnected and self.sensors_socket is not None:
            self.connectToSensor()
        elif self.sensors_socket is not None and self.isConnected:
            self.disconnectFromSensor()
        else:
            self.printTerminal("Connect to the ROV first")
        '''


    def connectToSensor(self):
        try:
            # Start the sensors program
            self.ssh_client.exec_command('python3 /home/sammy/ROV/sensors.py')

            stdin, stdout, stderr = self.ssh_client.exec_command('python3 /home/sammy/ROV/sensors.py')
            combined_output = stdout.read().decode('utf-8')
            print(combined_output)

            self.sensors_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sensors_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sensors_socket.connect((self.ip_addr, 8487))  # Pi's IP address and port

            threading.Thread(target=self.handle_sensors).start()

            self.printTerminal("Sensors connected")

            # Update style to show disconnection option
            self.SensorConnectButton.setText("DISCONNECT")
            self.SensorConnectButton.setStyleSheet("""
                background-color: red;
                color: white;
                border-radius: 20px;
                font-weight: bold;
                padding: 10px;
            """)
        except Exception as e:
            self.printTerminal(f"Error while connecting to sensors.:{e}")
            self.SensorConnectButton("""
                background-color: grey;
                color: white;
                border-radius: 20px;
                font-weight: bold;
                padding: 10px;
            """)

    def disconnectFromSensor(self):
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command('pgrep -f sensors.py')
            pid = stdout.read().strip()

            if pid:
                # Kill the process using the PID
                kill_command = f'kill {pid}'
                self.ssh_client.exec_command(kill_command)
                self.printTerminal("Sensors program ended.")
                self.SensorConnectButton.setText("CONNECT")
                self.SensorConnectButton("""
                    background-color: green;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)
            else:
                print("No process found for sensors.py")
        except Exception as e:
            self.printTerminal(f"Error stopping sensors program: {e}")
        finally:
            self.printTerminal("Sensors disconnected.")

def initiateGUI():
    """
    Launches the program.
    """
    # Create the instance of QApplication
    app = QApplication(sys.argv)

    # SET FONT STYLE
    app.setFont(QFont("Bahnschrift Regular", 10))
    app.setStyle("Fusion")
    #app.setWindowIcon(QIcon('graphics/icon.ico'))

    program = UIWINDOW(app)
    program.show()

    # Start event loop
    sys.exit(app.exec())

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    initiateGUI()