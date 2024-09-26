import socket
import cv2
import pickle
import struct
from picamera2 import Picamera2
import io
import time

# Initialize the camera
camera = Picamera2()
camera.configure(camera.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))

# Initialize the socket connection
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('192.168.16.104', 8485))  # Use the Pi's IP address and an open port
server_socket.listen(5)
print("Listening for connections...")

# Accept a client connection
conn, addr = server_socket.accept()
print(f"Connection from: {addr}")

# Start capturing frames
camera.start()

# Initialize Picamera2 and configure the video settings

try:
    while True:
        # Capture a frame
        frame = camera.capture_array()
        # Encode the frame as JPEG
        _, jpeg_frame = cv2.imencode('.jpg', frame)
    
        # Serialize the frame
        data = pickle.dumps(jpeg_frame)
        
        # Pack the frame size as a long integer (Q)
        msg_size = struct.pack("Q", len(data))
    
        try:
            # Send frame size and then the frame data
            conn.sendall(msg_size + data)
        except (BrokenPipeError, ConnectionResetError) as e:
            print(f"Client disconnected or connection lost: {e}")
            break  # Exit the loop if the client disconnects
        
        # Add a small delay to control the frame rate (e.g., 30 FPS)
        time.sleep(1 / 30)
        
except Exception as e:
    print(f"Error during frame sending: {e}")
    conn.close()


'''
finally:
    #conn.close()
    #server_socket.close()
    #camera.stop()
    print()
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()

try:
    while True:
        # Capture frame-by-frame
        frame = picam2.capture_array()

        # Serialize the frame
        data = pickle.dumps(frame)
        # Send message length first
        message_size = struct.pack("Q", len(data))
        # Then send the data
        client_socket.sendall(message_size + data)
'''
'''
# Capture video from the Pi Camera (using OpenCV)
camera = cv2.VideoCapture(0)

# Ensure camera opens successfully
if not camera.isOpened():
    print("Error: Could not open camera.")
    exit()

try:
    while True:
        ret, frame = camera.read()  # Capture a frame
        if not ret:
            break

        # Serialize frame (compress to JPEG format)
        data = pickle.dumps(frame)
        message = struct.pack("Q", len(data)) + data

        # Send frame over the socket
        connection.sendall(message)        
except Exception as e:
    print(f"Error: {e}")
finally:
    #picam2.stop()
    client_socket.close()
    server_socket.close()
'''

