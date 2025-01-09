# !/usr/bin/env python3
# Modules
import RPi.GPIO as GPIO
from time import sleep, time
import socket
import threading
# sudo lsof -i :8486
# sudo kill pid
class ESCController:
    def __init__(self, pin, motor_name, min_pulse=1000, max_pulse=2000, frequency=50):
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self.frequency = frequency
        self.signal_pin = pin
        self.motor_name = motor_name

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # Setup PWM pin for speed control
        GPIO.setup(pin, GPIO.OUT)
        self.pwm = GPIO.PWM(pin, frequency)
        self.pwm.start(0)

        # Calibrate ESC
        self.calibrate()

    def calibrate(self):
        # try:
        #     """Initialize ESC by sending min throttle signal"""
        #     print("Stopping motor...")
        #     self.pwm.ChangeDutyCycle(7.5)  # Neutral (1.5ms pulse width)
        #     sleep(1)
        #     print("Running motor forward...")
        #     self.pwm.ChangeDutyCycle(10)  # Forward (2ms pulse width)
        #     sleep(2)
        #     print("Running motor reverse...")
        #     self.pwm.ChangeDutyCycle(5)  # Reverse (1ms pulse width)
        #     sleep(2)
        # finally:
        #     self.pwm.stop()  # Reverse (1ms pulse width)
        #     GPIO.cleanup()
        #     return

        print(f"Calibrating {self.motor_name} ESC...")
        duty_cycle = self.pulse_to_duty(self.min_pulse)
        self.pwm.ChangeDutyCycle(5)
        # self.pwm.ChangeDutyCycle(duty_cycle)
        # self.pwm.ChangeDutyCycle(0)
        sleep(2)
        print(f"{self.motor_name} ESC calibrated")

    def pulse_to_duty(self, pulse_width):
        """Convert pulse width (microseconds) to duty cycle percentage"""
        period = 1000000 / self.frequency
        return (pulse_width / period) * 100

    def set_speed(self, speed_percent):
        """Set ESC speed as percentage (-100 to 100)"""
        # Ensure speed is between -100 and 100
        speed_percent = max(-100, min(100, speed_percent))
        abs_speed = abs(speed_percent)

        # Calculate pulse width
        pulse_range = self.max_pulse - self.min_pulse
        neutral_pulse = (self.max_pulse + self.min_pulse) / 2

        # Calculate pulse width
        # pulse_range = self.max_pulse - self.min_pulse
        print('pulse_range',pulse_range)
        print('speed_percent', speed_percent)

        if speed_percent >= 0:
            # Forward speed (positive values)
            pulse_width = self.min_pulse + (pulse_range * speed_percent / 100)
            print('pulse_width_FR', pulse_width)
        else:
            # Reverse speed (negative values)
            pulse_width = self.min_pulse - (pulse_range * abs_speed / 100)
            print('pulse_width_RV', pulse_width)

        duty_cycle = self.pulse_to_duty(pulse_width)

        print(f"Setting {self.motor_name} speed to {speed_percent}% ({duty_cycle}% duty cycle)")
        self.pwm.ChangeDutyCycle(duty_cycle)

class MotorController:
    def __init__(self):
        # Define motor configurations with GPIO pins
        motor_configs = {
            'top': {'pin': 12, 'name': 'Top Motor'},
            'rear': {'pin': 22, 'name': 'Rear Motor'},
            'left': {'pin': 11, 'name': 'Left Motor'},
            'right': {'pin': 13, 'name': 'Right Motor'}
        }

        # Initialize all ESC controllers
        self.motors = {}
        for motor_id, config in motor_configs.items():
            self.motors[motor_id] = ESCController(
                pin=config['pin'],
                motor_name=config['name']
            )

    def process_command(self, command):
        """Process commands for all motors"""
        try:
            # Parse command string: "motor_id:speed:value"
            parts = command.split(':')

            # Handle emergency stop
            if command == 'STOP_ALL':
                self.stop_all()
                return

            if len(parts) != 3:
                print(f"Invalid command format: {command}")
                return

            motor_id, action, value = parts

            if motor_id not in self.motors:
                print(f"Unknown motor ID: {motor_id}")
                return

            motor = self.motors[motor_id]

            if action == 'speed':
                try:
                    speed = int(value)
                    motor.set_speed(speed)
                except ValueError:
                    print(f"Invalid speed value: {value}")
            else:
                print(f"Unknown action: {action}")

        except Exception as e:
            print(f"Error processing command: {e}")

    def stop_all(self):
        """Emergency stop all motors"""
        print("Emergency stop - stopping all motors")
        for motor in self.motors.values():
            motor.set_speed(0)

def handle_client(client_socket, controller):
    try:
        print("Client connected, waiting for commands...")
        while True:
            command = client_socket.recv(1024).decode().strip()
            if not command:
                continue

            print(f"Received command: {command}")
            controller.process_command(command)

    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        controller.stop_all()
        client_socket.close()
        print("Client disconnected")

def thruster_setup():
    # Initialize the motor controller
    controller = MotorController()

    # Setup socket server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 8486))
    #server_socket.bind(('192.168.201.17', 8486))
    server_socket.listen(5)
    print("Multi-motor thruster control server listening")

    try:
        while True:
            client, addr = server_socket.accept()
            print(f"Connection from {addr}")
            client_handler = threading.Thread(
                target=handle_client,
                args=(client, controller)
            )
            client_handler.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        controller.stop_all()
        server_socket.close()
        GPIO.cleanup()

# Command line execution
if __name__ == '__main__':
    thruster_setup()
