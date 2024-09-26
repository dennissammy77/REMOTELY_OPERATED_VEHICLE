from gpiozero import PWMOutputDevice, PWMLED
import time
import socket

# Pin definitions
MOTOR_PIN = 26  # GPIO 26 corresponds to physical pin 37
LED_PIN = 16    # Example GPIO pin for the LED

# Initialize PWM devices with 50Hz frequency
motor = PWMOutputDevice(MOTOR_PIN, frequency=50)
led = PWMLED(LED_PIN)

def set_motor_speed(duty_cycle):
    """Sets the motor speed with the given duty cycle (0.0 to 100.0) and simulates with an LED."""
    normalized_value = duty_cycle / 100  # Convert percentage to a value between 0 and 1
    motor.value = normalized_value
    led.value = normalized_value  # Set LED brightness to match duty cycle
    print(f"Set motor speed to {duty_cycle}% (LED brightness adjusted to match)")

def handle_client(client_socket):
    try:
        while True:
            command = client_socket.recv(1024).decode()
            if command == "start":
                print("Motor starting")
                set_motor_speed(10)  # Adjust speed
            elif command == "stop":
                print("Motor stopping")
                set_motor_speed(0)
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8486))
    server_socket.listen(5)
    print("Motor control server listening")

    while True:
        client, addr = server_socket.accept()
        print(f"Connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client,))
        client_handler.start()
        
if __name__ == "__main__":
    start_server()
"""        
try:
    # Initialization sequence for ESC
    print("Initializing ESC...")

    # Step 1: Send high signal to arm the ESC (full throttle)
    set_motor_speed(10)  # 10% duty cycle (full throttle)
    time.sleep(2)  # wait for 2 seconds
    print("Step 1 complete: Full throttle signal sent")

    # Step 2: Send low signal to arm the ESC (minimum throttle)
    set_motor_speed(5)  # 5% duty cycle (minimum throttle)
    time.sleep(2)  # wait for 2 seconds
    print("Step 2 complete: Minimum throttle signal sent")

    print("ESC armed and ready to control the motor.")

    # Now you can set the motor speed
    set_motor_speed(9)  # Adjust this value to control speed
    time.sleep(4)  # Run for 4 seconds
    print("Motor running at 9% speed for 4 seconds")

except KeyboardInterrupt:
    pass
finally:
    motor.value = 0  # Stop PWM for motor
    led.value = 0    # Turn off LED
    print("GPIO cleaned up.")
"""

