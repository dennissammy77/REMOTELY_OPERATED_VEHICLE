from picamera2 import Picamera2
from time import sleep

cam = Picamera2()
cam.start_preview()
cam.record_video("~/Desktop/new_video.mp4", duration=5)
cam.stop_preview()

