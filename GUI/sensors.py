from mpu6050 import mpu6050
import time
import socket
import threading
import json
import math

# Create a new Mpu6050 object
mpu6050 = mpu6050(0x68)

# Define a function to read the sensor data
def read_sensor_data():
    # Read the accelerometer values
    accelerometer_data = mpu6050.get_accel_data()

    # Read the gyroscope values
    gyroscope_data = mpu6050.get_gyro_data()

    # Read temp
    temperature = mpu6050.get_temp()

    return accelerometer_data, gyroscope_data, temperature

def get_y_rotation(x, y, z):
    radians = math.atan2(x, math.sqrt(y * y + z * z))
    return -math.degrees(radians)

def get_x_rotation(x, y, z):
    radians = math.atan2(y, math.sqrt(x * x + z * z))
    return math.degrees(radians)

def handle_client(client_socket):
    try:
        while True:
            # Read the sensor data

            accelerometer_data, gyroscope_data, temperature = read_sensor_data()

            # Calculate pitch and roll
            pitch = get_x_rotation(accelerometer_data['x'], accelerometer_data['y'], accelerometer_data['z'])
            roll = get_y_rotation(accelerometer_data['x'], accelerometer_data['y'], accelerometer_data['z'])
            # Yaw calculation (integrate gyro_z over time)

            print(f"Pitch: {pitch:.2f}, Roll: {roll:.2f}, Yaw: ")

            sensor_values = {
                'pitch':    pitch,
                'roll':     roll,
                'yaw':      gyroscope_data['y'],
                'accel-x': accelerometer_data['x'],
                'temp': temperature
            }

            # Convert the dictionary to a JSON string and then encode it as bytes
            sensor_values_json = json.dumps(sensor_values).encode('utf-8')
            print(sensor_values_json)

            client_socket.sendall(sensor_values_json)
            time.sleep(1)  # Send data every second (adjust as needed)
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()

def sensors_setup():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('192.168.1.2', 8487))
    server_socket.listen(5)
    print("Sensors server connected")

    while True:
        client, addr = server_socket.accept()
        print(f"Connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client,))
        client_handler.start()

# Command line execution
if __name__ == '__main__':
    sensors_setup()

