
try:
    import os, sys
    import io
    import requests
    import socket
    import pickle
    import struct
    import random
    import serial
    import pygame
    from PyQt5 import uic
    from PyQt5.QtWidgets import (QMainWindow, QApplication,
                                 QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QTextEdit)
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
    Contains functions to initiate the GUI, link the widgets and connect
    all the signals/slots from external libraries together.
    """

    def __init__(self, app):
        """
        Class constructor.
        Loads GUI, call functions to initiate all the libraries and connects the signal/slots together.

        INPUT:
        - app: QApplication object (required to allow theme changing).
        """
        super(UIWINDOW, self).__init__()

        # LOAD UI FILE
        uiFile = getResourcePath("gui.ui")
        uic.loadUi(uiFile, self)

        self.app = app
        self.initUI()

        # INITIATE OBJECTS
        self.initiateObjects()

        # Initialize Pygame and the controller
        pygame.init()
        pygame.joystick.init()
        self.controller = None
        if pygame.joystick.get_count() > 0:
            self.controller = pygame.joystick.Joystick(0)
            self.controller.init()

        # Track button states
        self.prev_button_states = []
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
        # Serial connection setup
        self.isConnected = False
        self.ssh_client = None
        self.pi_hostname = 'raspberrypi.local'  # Replace with your Raspberry Pi's IP
        self.username = 'sammy'  # Raspberry Pi username
        self.password = 'password'  # Raspberry Pi password

        # ROV connect button
        self.rovConnectButton = self.findChild(QPushButton, 'control_rov_connect')
        self.rovConnectButton.clicked.connect(self.toggleROVConnection)


        self.connectControllerButton = self.findChild(QPushButton, 'control_controller_connect')
        self.connectControllerButton.clicked.connect(self.toggleControllerConnection)

        self.terminalTextEdit = self.findChild(QTextEdit, 'terminalOutputLabel')
        if not self.terminalTextEdit:
            print("Error: terminalTextEdit not found. Please check the name in the .ui file.")

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

        # Video feed QLabel
        self.camera_active = False
        self.stream_url = 'http://192.168.16.104:5001/video_feed'
        self.videoFeedLabel = self.findChild(QLabel, 'videoFeedLabel')

        self.client_socket = None
        self.motor_socket = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_video_feed)

        self.start_feed()
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
        # time = datetime.now().strftime("%H:%M:%S")
        # string = time + " -> " + str(text)
        # self.terminalTextEdit.setPlainText(string)
        # self.terminalTextEdit.verticalScrollBar().setValue(self.terminalTextEdit.verticalScrollBar().maximum())

        currentText = self.terminalTextEdit.toPlainText()
        newText = f"{datetime.now().strftime('%H:%M:%S')} -> {text}\n"
        self.terminalTextEdit.setPlainText(currentText + newText)
        self.terminalTextEdit.verticalScrollBar().setValue(self.terminalTextEdit.verticalScrollBar().maximum())
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
            # Create SSH Client
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(self.pi_hostname, username=self.username, password=self.password)

            # Establish the serial connection
            self.isConnected = True
            self.printTerminal("Connected to ROV")

            # Flash the onboard LED 3 times by executing the script remotely
            self.flashOnboardLED()

            # Update button style to show disconnection option
            self.rovConnectButton.setText("DISCONNECT")
            self.rovConnectButton.setStyleSheet("""
                background-color: red;
                color: white;
                border-radius: 20px;
                font-weight: bold;
                padding: 10px;
            """)

            # Camera
            self.start_feed()
            #self.ssh_client.exec_command("python3 /home/sammy/ROV/video_feed.py")
        except Exception as e:
            self.printTerminal(f"Failed to connect to ROV: {e}")
    def disconnectFromROV(self):
        """
        Closes the SSH connection to the Raspberry Pi.
        """
        try:
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
                # Camera
                self.stop_feed()
        except Exception as e:
            self.printTerminal(f"Failed to disconnect from ROV: {e}")
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
            self.setButtonStyle("background-color: green; color: white; border-radius: 20px; font-weight: bold; padding: 10px;")
            self.printTerminal("Controller disconnected.")
        else:
            # Connect the controller
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.controller = pygame.joystick.Joystick(0)
                self.controller.init()
                '''
                self.motor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.motor_socket.connect(('192.168.16.104', 8486))  # Pi's IP address and port
                '''
                self.connectControllerButton.setText("DISCONNECT")
                self.setButtonStyle("background-color: red; color: white; border-radius: 20px; font-weight: bold; padding: 10px;")
                self.printTerminal("Controller connected.")
            else:
                self.printTerminal("No controller detected.")
                self.setButtonStyle("background-color: grey; color: white; border-radius: 20px; font-weight: bold; padding: 10px;")
    def setButtonStyle(self, style):
        """
        Sets the stylesheet of the connectControllerButton.

        INPUT:
        - style: CSS-like stylesheet for the button
        """
        self.connectControllerButton.setStyleSheet(style)
    def updateControllerState(self):
        """
        PURPOSE
        Contains the functions to connect and read from the XBOX controller.
        """
        if self.controller:
            pygame.event.pump()

            # Dictionary to store the state of buttons and axes
            controller_state = {
                "buttons": {},
                "axes": {}
            }

            # Mapping for button actions
            direction_map = {
                0: 'Up',  # A Button
                1: 'Down',  # B Button
                2: 'Left',  # X Button
                3: 'Right',  # Y Button
                4: 'Forward',  # LB
                5: 'Backward',  # RB
            }

            current_direction = None

            # Reading all button states
            for button_id in range(self.controller.get_numbuttons()):
                if self.controller.get_button(button_id):
                    current_direction = direction_map.get(button_id)
                    self.printTerminal(f"Button {button_id} pressed: Moving {current_direction}")

                    if current_direction == 'Forward':
                        self.printTerminal("Forward pressed")
                        self.send_motor_command("start")

                controller_state["buttons"][f"Button_{button_id}"] = self.controller.get_button(button_id)

            # Reading all axis states (e.g., sticks and triggers)
            for j in range(self.controller.get_numaxes()):
                controller_state["axes"][f"Axis_{j}"] = round(self.controller.get_axis(j), 2)

            #print(controller_state)
            '''
            axes = [self.controller.get_axis(i) for i in range(self.controller.get_numaxes())]
            buttons = [self.controller.get_button(i) for i in range(self.controller.get_numbuttons())]
            # Example: Print axis values and button states to the terminal
            #print(f"Axes: {axes}")
            #self.printTerminal(f"Axes: {axes}")
            self.printTerminal(f"Buttons: {buttons}")
            '''

    def send_motor_command(self, command):
        """Send motor control commands to the Raspberry Pi."""
        if self.motor_socket:
            try:
                self.motor_socket.sendall(command.encode())
            except Exception as e:
                print(f"Error sending motor command: {e}")
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