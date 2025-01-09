from flask import Flask, Response, request
from picamera2 import Picamera2
import cv2
import json, os, signal

app = Flask(__name__)

# Global variables for control
camera = None
stream_active = False

def initialize_camera():
    global camera
    if camera is None:
        camera = Picamera2()
        camera.configure(camera.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
        camera.start()

def generate_frames():
    global stream_active
    while stream_active:
        frame = camera.capture_array()
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    global stream_active
    if not stream_active:
        return "Stream is not active"
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_stream', methods=['GET'])
def start_stream():
    global stream_active, camera
    if camera is None:
        initialize_camera()
    stream_active = True
    return "Stream started"

@app.route('/stop_stream', methods=['GET'])
def stop_stream():
    global stream_active
    stream_active = False
    return "Stream stopped"

if __name__ == '__main__':
    initialize_camera()
    stream_active = True  # Start with stream active
    app.run(host='0.0.0.0', port=5001)