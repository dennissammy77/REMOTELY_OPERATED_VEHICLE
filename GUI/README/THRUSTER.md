# Thrusters 
The thrusters constitute the propulsion mechanism for thr ROV. It involves a set of mechanical, software and control
systems to achieve propulsion. This documentation will outline the Setups, configurations, integrations and Tests for
this critical module.

## A. Key Components
1. ESC
2. Brushless motor
3. Propeller
4. Motor Managemet Algorithm
5. Controller

## B. Methods & Files
There are two key instances for the operation and functionality of the motors. The file that will be uploaded and run at the 
raspberrypi 4 locally  and methods that are integrated at the GUI. Categorically put, 
1. The method that will handle receiving and sending commands from the controller.
2. The method to receive and drive the motors.