import RPi.GPIO as GPIO
import time

# GPIO pin for ESC signal
ESC_PIN = 12

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(ESC_PIN, GPIO.OUT)

# Initialize PWM (50Hz for standard ESCs)
pwm = GPIO.PWM(ESC_PIN, 50)
pwm.start(0)  # Start with 0% duty cycle

# Functions for ESC control
def stop():
    print("Stopping motor...")
    pwm.ChangeDutyCycle(7.5)  # Neutral (1.5ms pulse width)
    time.sleep(1)

def forward():
    print("Running motor forward...")
    pwm.ChangeDutyCycle(10)  # Forward (2ms pulse width)
    time.sleep(2)

def reverse():
    print("Running motor reverse...")
    pwm.ChangeDutyCycle(5)  # Reverse (1ms pulse width)
    time.sleep(2)

try:
    # Testing ESC control
    stop()     # Ensure the motor stops first
    forward()  # Move forward
    stop()     # Stop the motor
    reverse()  # Move in reverse
    stop()     # Stop again

finally:
    pwm.stop()
    GPIO.cleanup()
