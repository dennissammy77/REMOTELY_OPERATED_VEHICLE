import json
import socket
import threading

from PyQt5.QtCore import QThread
from client.ssh_connection import SSHWorker

class SensorsHandler():
    def __init__(self, ssh_conn, logger,labels,ip_addr):
        super().__init__()
        self.ssh_conn = ssh_conn
        self.logger = logger

        self.ip_addr = ip_addr  # Ip Address connection
        self.ip_port = 8487  # Ip Address connection
        self.sensor_client_socket = None

        self.thread = None
        self.worker = None

        # Assign labels
        self.temperatureLabel = labels.get('temperatureLabel')
        self.pitchLabel = labels.get('pitchLabel')
        self.rollLabel = labels.get('rollLabel')
        self.yawLabel = labels.get('yawLabel')
        self.accelerationLabel = labels.get('accelerationLabel')

    def initialize(self):
        try:
            # Execute the sensor script remotely
            # self.ssh_conn.execute_command('python3 /home/sammy/ROV/sensors.py')

            self.worker = SSHWorker(self.ssh_conn, 'python3 /home/sammy/ROV/sensors.py', self.logger)
            self.thread = QThread()
            self.worker.moveToThread(self.thread)

            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.error.connect(self.logger.log)
            self.worker.progress.connect(self.logger.log)

            self.thread.started.connect(self.worker.run)
            self.thread.start()

            self.sensor_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sensor_client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sensor_client_socket.connect((self.ip_addr, self.ip_port))
            self.logger.log(f"Sensors Initialized")

            threading.Thread(target=self.handle_sensors).start()
            self.logger.printTerminal(f"Sensors Initialized again")
        except Exception as e:
            self.logger.printTerminal(f"Initialize Sensors Error: {str(e)}")
            return None

    def handle_sensors(self):
        try:
            full_data = ""
            while True:
                # Receive the data
                sensor_data_json = self.sensor_client_socket.recv(1024).decode()  # Decode the received data

                # Check if the received data is empty
                if not sensor_data_json:
                    self.logger.log("Received empty data from sensor.")
                    # Skip empty data and keep listening
                    continue
                # Append received data to full_data
                full_data += sensor_data_json

                # Deserialize JSON string to dictionary
                sensor_values = json.loads(full_data)
                self.logger.log(sensor_values)

                # Deserialize JSON string to dictionary
                temperature = sensor_values['temp']
                pitch = sensor_values['pitch']
                roll = sensor_values['roll']
                yaw = sensor_values['yaw']
                accel_x = sensor_values['accel-x']
                print(f"temp: {temperature}")
                print(f"roll: {roll}")

                full_data = ""
                sensor_values = ""
                # Update the sensor values
                self.temperatureLabel.setText(str(format(temperature,".2f")))
                self.pitchLabel.setText(str(format(pitch, ".2f")))
                self.rollLabel.setText(str(format(roll, ".2f")))
                self.yawLabel.setText(str(format(yaw, ".2f")))
                self.accelerationLabel.setText(str(format(accel_x, ".2f")))

        except Exception as e:
            self.logger.log(f"Error handling sensors: {e}")
            self.logger.printTerminal(f"Error handling sensors")
            # self.sensor_client_socket.close()
        # finally:
            self.logger.printTerminal(f"Sensors Disconnected")
            # self.sensor_client_socket.close()
            raise Exception("Sensors [handle sensors]")

    def disconnect(self):
        try:
            # Execute the sensor script remotely
            self.ssh_conn.execute_command('pgrep -f sensors.py')
            self.worker = SSHWorker(self.ssh_conn, 'pgrep -f sensors.py', self.logger)
            self.thread = QThread()
            self.worker.moveToThread(self.thread)

            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.error.connect(self.logger.log)
            self.worker.progress.connect(self.logger.log)

            self.thread.started.connect(self.worker.run)
            self.thread.start()
            self.logger.printTerminal(f"Sensors discontinued")
        except Exception as e:
            self.logger.printTerminal(f"disconnected Sensors Error: {str(e)}")
            self.logger.log("disconnected Sensors Error")
            raise Exception("disconnected")