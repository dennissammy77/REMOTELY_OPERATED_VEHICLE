import os, sys
import threading

import cv2
import numpy as np
import pygame
import requests
from PyQt5 import uic
from PyQt5.QtWidgets import (QMainWindow, QApplication,
                             QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QTextEdit, QSizePolicy)
from PyQt5 import QtGui
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtCore import QTimer, Qt, QSize, QThread, pyqtSignal
from functools import partial

from client.ssh_connection import sshConnection
from client.video_manager import VideoFeedThread
from client.thruster_manager import THRUSTER_HANDLER
from client.sensors_manager import SensorsHandler
from utils.logger import Logger


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
        # States
        self.isSshConnected = False  # is ROV connected over ssh
        self.video_feed_active = False  # is Video feed active
        self.video_feed_initialized = False
        self.motor_socket = None
        self.ip_addr = '192.168.55.17'  # Ip Address connection
        self.sensors_connection = False

        self.controller = None

        self.video_url = f"http://{self.ip_addr}:5001/video_feed"

        # Instantiators
        self.logger = Logger(self)
        self.ssh_conn = sshConnection(self.logger, self.isSshConnected)
        self.video_conn = VideoFeedThread(self.ssh_conn, self.logger)
        self.thruster_conn = THRUSTER_HANDLER(self.ssh_conn, self.logger)

        self.temperatureLabel = self.findChild(QLabel, 'temperatureLabel')
        self.pitchLabel = self.findChild(QLabel, 'pitchLabel')
        self.rollLabel = self.findChild(QLabel, 'rollLabel')
        self.yawLabel = self.findChild(QLabel, 'yawLabel')
        self.accelerationLabel = self.findChild(QLabel, 'accelerationLabel')

        # Pass labels to SensorsHandler
        labels = {
            'temperatureLabel': self.temperatureLabel,
            'pitchLabel': self.pitchLabel,
            'rollLabel': self.rollLabel,
            'yawLabel': self.yawLabel,
            'accelerationLabel': self.accelerationLabel,
        }
        self.sensor_conn = SensorsHandler(self.ssh_conn, self.logger, labels)

        # INITIAL STARTUP MESSAGE
        self.logger.printTerminal("Welcome to the control interface.")
        self.logger.printTerminal("Connect to the ROV and CONTROLLER to get started.")

        # ssh_conn.setup_ssh_connection()
        self.actionUiListenerSetup()

        self.timer = QTimer()
        self.timer.timeout.connect(self.thruster_conn.updateControllerState)
        self.timer.start(50)  # Check every 50 milliseconds

    def actionUiListenerSetup(self):
        """
        Setup UI components and initialize action listeners.
        """
        # connect button
        self.rovConnectButton = self.findChild(QPushButton, 'control_rov_connect')
        # camera button
        self.CameraConnectButton = self.findChild(QPushButton, 'camera_connect')
        self.video_label = self.findChild(QLabel, 'videoFeedLabel')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMaximumSize(806, 1094)  # Set max size to control growth
        # Controller button
        self.connectControllerButton = self.findChild(QPushButton, 'control_controller_connect')
        # Sensors button
        self.SensorConnectButton = self.findChild(QPushButton, 'sensor_connect')

        self.actionListeners()

    def actionListeners(self):
        # connect action
        self.rovConnectButton.clicked.connect(partial(self.toggleRovToPiConnection, self.ssh_conn))
        # camera action
        self.CameraConnectButton.clicked.connect(partial(self.toggleVideoConnection, self.video_conn))
        # Controller action
        self.connectControllerButton.clicked.connect(self.toggleControllerConnection)
        # Sensors action
        self.SensorConnectButton.clicked.connect(self.toggleSensorConnection)
        # Set up a timer to check the controller state

    def toggleRovToPiConnection(self, ssh_conn):
        try:
            if self.isSshConnected:
                ssh_conn.disconnect_ssh_connection()
                ssh_conn.clean_up()
                self.isSshConnected = False
                self.logger.printTerminal("Disconnected from ROV.")
                self.rovConnectButton.setText("CONNECT")
                self.rovConnectButton.setStyleSheet("""
                    background-color: green;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)
                self.CameraConnectButton.setText("CONNECT")
                self.CameraConnectButton.setStyleSheet("""
                                                background-color: green;
                                                color: white;
                                                border-radius: 20px;
                                                font-weight: bold;
                                                padding: 10px;
                                            """)
                self.connectControllerButton.setText("CONNECT")
                self.connectControllerButton.setStyleSheet("""
                                background-color: green;
                                color: white;
                                border-radius: 20px;
                                font-weight: bold;
                                padding: 10px;
                            """)
                self.SensorConnectButton.setText("CONNECT")
                self.SensorConnectButton.setStyleSheet("""
                                    background-color: green;
                                    color: white;
                                    border-radius: 20px;
                                    font-weight: bold;
                                    padding: 10px;
                                """)
            else:
                ssh_conn.setup_ssh_connection()
                self.logger.printTerminal("Connected to ROV.")
                self.isSshConnected = True
                self.rovConnectButton.setText("DISCONNECT")
                self.rovConnectButton.setStyleSheet("""
                    background-color: red;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)

        except Exception as e:
            self.logger.printTerminal(f"Failed to connect to ROV:{e}")
            print(f"Error in toggleRovToPiConnection: {e}")

    def toggleVideoConnection(self, video_conn):
        """
            Toggles between connecting and disconnecting the camera to the GUI
        """
        try:
            self.logger.printTerminal(self.video_feed_active)
            if self.video_feed_active:
                video_conn.stop()
                self.logger.printTerminal("video disconnection success")
                self.CameraConnectButton.setText("CONNECT")
                self.CameraConnectButton.setStyleSheet("""
                                background-color: green;
                                color: white;
                                border-radius: 20px;
                                font-weight: bold;
                                padding: 10px;
                            """)
                self.video_feed_active = False
            else:
                if self.video_feed_initialized:
                    video_conn.play()
                    self.logger.printTerminal("video connection success")
                    # Update style to show disconnection option
                    self.CameraConnectButton.setText("DISCONNECT")
                    self.CameraConnectButton.setStyleSheet("""
                                                        background-color: red;
                                                        color: white;
                                                        border-radius: 20px;
                                                        font-weight: bold;
                                                        padding: 10px;
                                                    """)
                    self.video_feed_active = True
                    threading.Thread(target=self.update_frame).start()
                else:
                    video_conn.initialize()
                    self.logger.printTerminal("video connection success")
                    # Update style to show disconnection option
                    self.CameraConnectButton.setText("DISCONNECT")
                    self.CameraConnectButton.setStyleSheet("""
                                    background-color: red;
                                    color: white;
                                    border-radius: 20px;
                                    font-weight: bold;
                                    padding: 10px;
                                """)
                    self.video_feed_active = True
                    self.video_feed_initialized = True
                    threading.Thread(target=self.update_frame).start()

        except Exception as e:
            print(e)
            self.logger.printTerminal("Error on video connection")
            self.logger.printTerminal(f"Error while connecting to video server:{e}.")
            self.CameraConnectButton("""
                            background-color: grey;
                            color: white;
                            border-radius: 20px;
                            font-weight: bold;
                            padding: 10px;
                        """)

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
            self.logger.printTerminal("Controller disconnected.")
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
                self.thruster_conn.initialize()
                self.connectControllerButton.setText("DISCONNECT")
                self.connectControllerButton.setStyleSheet("""
                    background-color: red;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)
                self.logger.printTerminal("Controller connected.")
                self.controller = True
            else:
                self.logger.printTerminal("No controller detected.")
                self.connectControllerButton.setStyleSheet("""
                    background-color: grey;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)

    def toggleSensorConnection(self):
        """
            Toggles the connection state of the sensors.
        """
        try:
            if self.sensors_connection:
                self.SensorConnectButton.setText("CONNECT")
                self.SensorConnectButton.setStyleSheet("""
                    background-color: green;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)
                self.sensor_conn.disconnect()
                self.sensors_connection = False
            else:
                self.sensor_conn.initialize()
                self.SensorConnectButton.setText("DISCONNECT")
                self.SensorConnectButton.setStyleSheet("""
                    background-color: red;
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 10px;
                """)
                self.sensors_connection = True
        except Exception as e:

            self.logger.printTerminal(f"toggleSensorConnection: {e}")

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

    # LAUNCH GUI
    def initUI(self):
        """
            Initializes the user interface.
        """
        self.setWindowTitle("ROV Control Interface")


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


if __name__ == '__main__':
    initiateGUI()
