import json
import socket
import threading

class SensorsHandler():
    def __init__(self, ssh_conn, logger,labels):
        super().__init__()
        self.ssh_conn = ssh_conn
        self.logger = logger

        self.ip_addr = '192.168.55.17'  # Ip Address connection
        self.ip_port = 8487  # Ip Address connection
        self.sensor_client_socket = None

        # Assign labels
        self.temperatureLabel = labels.get('temperatureLabel')
        self.pitchLabel = labels.get('pitchLabel')
        self.rollLabel = labels.get('rollLabel')
        self.yawLabel = labels.get('yawLabel')
        self.accelerationLabel = labels.get('accelerationLabel')

    def initialize(self):
        try:
            # Execute the sensor script remotely
            self.ssh_conn.execute_command('python3 /home/sammy/ROV/sensors.py')

            self.sensor_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sensor_client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sensor_client_socket.connect((self.ip_addr, self.ip_port))
            print(f"Sensors Initialized")

            threading.Thread(target=self.handle_sensors).start()
            print(f"Sensors Initialized again")
        except Exception as e:
            print(f"Initialize Sensors Error: {str(e)}")
            return None

    def handle_sensors(self):
        try:
            full_data = ""
            while True:
                # Receive the data
                sensor_data_json = self.sensor_client_socket.recv(1024).decode()  # Decode the received data
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
                print(f"temp: {temperature}")
                print(f"roll: {roll}")

                full_data = ""
                # Update the sensor values
                self.temperatureLabel.setText(str(format(temperature,".2f")))
                self.pitchLabel.setText(str(format(pitch, ".2f")))
                self.rollLabel.setText(str(format(roll, ".2f")))
                self.yawLabel.setText(str(format(yaw, ".2f")))
                self.accelerationLabel.setText(str(format(accel_x, ".2f")))

        except Exception as e:
            print(f"Handle Sensors error {e}")
            self.logger.printTerminal(f"Error handling sensors: {e}")
            # self.sensor_client_socket.close()
        # finally:
            self.logger.printTerminal(f"Sensors Disconnected")
            # self.sensor_client_socket.close()

    def disconnect(self):
        try:
            # Execute the sensor script remotely
            self.ssh_conn.execute_command('pgrep -f sensors.py')
            print(f"Sensors discontinued")
            return None
        except Exception as e:
            print(f"discontinued Sensors Error: {str(e)}")