from PyQt5.QtCore import QThread, pyqtSignal
import time
import requests
from client.ssh_connection import SSHWorker

class VideoFeedThread(QThread):

    error_signal = pyqtSignal(str)  # Signal to emit errors
    stdout_signal = pyqtSignal(str)  # Signal to emit stdout messages
    stderr_signal = pyqtSignal(str)  # Signal to emit stderr messages

    def __init__(self, ssh_conn, logger, ip_addr):
        super().__init__()
        self.ssh_conn = ssh_conn
        self.video_feed_initialized = False
        self.video_feed_active = True
        self.logger = logger

        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.ip_addr = ip_addr  # Ip Address connection
        # Flask video stream URLs
        self.video_url = f"http://{self.ip_addr}:5001/video_feed"
        self.shutdown_url = f"http://{self.ip_addr}:5001/shutdown"
        self.start_stream = f"http://{self.ip_addr}:5001/start_stream"
        self.stop_stream = f"http://{self.ip_addr}:5001/stop_stream"
        # sudo fuser -v /dev/video0
        # sudo fuser -k /dev/video0

        self.thread = None
        self.worker = None

    def initialize(self):
        try:
            # Execute the video feed script
            # self.stdin, self.stdout, self.stderr = self.ssh_conn.execute_command(
            #     'python3 /home/sammy/ROV/video_feed.py'
            # )
            self.worker = SSHWorker(self.ssh_conn, 'python3 /home/sammy/ROV/video_feed.py', self.logger)
            self.thread = QThread()
            self.worker.moveToThread(self.thread)

            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.error.connect(self.logger.log)
            self.worker.progress.connect(self.logger.log)

            self.thread.started.connect(self.worker.run)
            self.thread.start()

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
