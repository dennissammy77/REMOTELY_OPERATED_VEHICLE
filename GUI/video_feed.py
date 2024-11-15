from flask import Flask, Response, request
from picamera2 import Picamera2
import cv2
import json, os, signal

app = Flask(__name__)

camera = Picamera2()
camera.configure(camera.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
camera.start()


def generate_frames():
    while True:
        frame = camera.capture_array()
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/shutdown', methods=['GET'])
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return "Server is shutting down..."


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
