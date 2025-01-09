from PyQt5.QtCore import QThread, pyqtSignal
import time
import requests

class VideoFeedThread(QThread):

    error_signal = pyqtSignal(str)  # Signal to emit errors
    stdout_signal = pyqtSignal(str)  # Signal to emit stdout messages
    stderr_signal = pyqtSignal(str)  # Signal to emit stderr messages

    def __init__(self, ssh_conn, logger):
        super().__init__()
        self.ssh_conn = ssh_conn
        self.video_feed_initialized = False
        self.video_feed_active = True
        self.logger = logger

        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.ip_addr = '192.168.55.17'  # Ip Address connection
        # Flask video stream URLs
        self.video_url = f"http://{self.ip_addr}:5001/video_feed"
        self.shutdown_url = f"http://{self.ip_addr}:5001/shutdown"
        self.start_stream = f"http://{self.ip_addr}:5001/start_stream"
        self.stop_stream = f"http://{self.ip_addr}:5001/stop_stream"
        # sudo fuser -v /dev/video0
        # sudo fuser -k /dev/video0

    def initialize(self):
        try:
            # Execute the video feed script
            self.stdin, self.stdout, self.stderr = self.ssh_conn.execute_command(
                'python3 /home/sammy/ROV/video_feed.py'
            )
            self.video_feed_initialized = True

            # Monitor stdout and stderr while the thread is running
            while self.video_feed_active:
                # Check if there's any stdout data available
                if self.stdout.channel.recv_ready():
                    stdout_data = self.stdout.channel.recv(1024).decode('utf-8')
                    if stdout_data:
                        print(f"stdout_data: {stdout_data}")
                        #self.stdout_signal.emit(stdout_data)

                # Check if there's any stderr data available
                if self.stderr.channel.recv_ready():
                    stderr_data = self.stderr.channel.recv(1024).decode('utf-8')
                    if stderr_data:
                        print(f"stderr_data: {stderr_data}")
                        #self.stderr_signal.emit(stderr_data)

                # Small delay to prevent high CPU usage
                time.sleep(0.1)

        except Exception as e:
            #self.error_signal.emit(f"Video feed error: {str(e)}")
            #self.logger.log(f"Video feed error: {str(e)}")
            print(f"Video feed error: {str(e)}")
            self.video_feed_active = False

    def stop(self):
        try:
            response = requests.get(self.stop_stream)
            self.logger.printTerminal(response.text)
        except Exception as e:
            print(f"Video feed paused error: {e}")

    def play(self):
        try:
            response = requests.get(self.start_stream)
            self.logger.printTerminal(response.text)
        except Exception as e:
            print(f"Video feed played error: {e}")
