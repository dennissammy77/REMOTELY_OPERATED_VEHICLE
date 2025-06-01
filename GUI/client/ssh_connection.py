import paramiko
from PyQt5.QtCore import QObject, QThread, pyqtSignal
import time

class sshConnection(QObject):
    """Thread configs"""
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, logger, isSshConnected):
        super().__init__()
        self.logger = logger
        self.isSshConnected = isSshConnected
        self.ssh_client = None
        self.running_processes = []  # To track PIDs of started processes
        '''Connection Details'''
        self.pi_hostname = 'raspberrypi'  # Replace with your Raspberry Pi's IP
        self.username = 'sammy'  # Raspberry Pi username
        self.password = 'password'  # Raspberry Pi password
        self.ip_addr = '192.168.46.17'  # Ip Address connection

    def setup_ssh_connection(self):
        """
            Establishes an SSH connection to the Raspberry Pi using its hostname over Ethernet.
        """
        try:
            # Create SSH Client && Establish the serial connection
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(self.pi_hostname,
                                    username=self.username,
                                    password=self.password)
            self.logger.printTerminal("SSH connection:- [SUCCESS]:Connected to ROV over SSH")
            self.isSshConnected = True
            # if self.ssh_client:
            self.clean_up()
        except Exception as e:
            self.isSshConnected = False
            self.ssh_client = None
            self.logger.printTerminal(f"SSH connection:- [FAILED]: {e}")
            raise Exception("SSH connection:- [FAILED]")

    def disconnect_ssh_connection(self):
        """
        Disconnects the SSH session and kills all running processes.
        """
        if not self.ssh_client:
            self.logger.log("SSH connection [disconnect_ssh_connection]: SSH client is not connected.")
            self.logger.printTerminal("SSH connection [disconnect_ssh_connection]: SSH client is not connected.")
            raise Exception("SSH connection [disconnect_ssh_connection]")

        try:
            # Kill all running processes
            self.clean_up()

            # Close the SSH connection
            self.ssh_client.close()
            self.isSshConnected = False

            self.logger.printTerminal("Disconnected from ROV. All processes terminated.")
        except Exception as e:
            self.logger.printTerminal(f"SSH connection [disconnect_ssh_connection] Failed: {e}")
            self.logger.log(f"SSH connection [disconnect_ssh_connection] Failed: {e}")
            raise Exception("SSH connection [disconnect_ssh_connection]")

    def execute_command(self, command):
        """
        Executes a command over SSH and optionally tracks the process PID.
        :param command: The shell command to execute.
        """
        if not self.ssh_client:
            self.logger.log("SSH connection [execute_command]: SSH client is not connected.")
            self.logger.printTerminal("SSH connection [execute_command]: SSH client is not connected.")
            raise Exception("SSH connection [execute_command]")

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            self.logger.log(f"SSH connection [execute_command]: stdin-exec-command: {stdin}")
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            self.logger.log(f"SSH connection [execute_command]: output-exec-command: {output}")
            self.logger.log(f"SSH connection [execute_command]: error-exec-command: {error}")

            # Retrieve the PID of the started process if available
            pid = stdout.channel.recv_exit_status()
            if pid != 0:
                self.running_processes.append(pid)

            self.logger.log(f"Executed: {command}")
            self.logger.log(f"PID: {pid}")
            if output:
                self.logger.log(f"Output: {output}")
            if error:
                self.error.emit(error.strip())
                self.logger.log(f"Error: {error}")

            self.finished.emit()
            return output
        except Exception as e:
            self.logger.log(f"SSH connection [execute_command]: Failed to execute command: {e}")
            self.logger.printTerminal(f"SSH connection [execute_command]: Failed to execute command: {e}")
            raise Exception("SSH connection [execute_command]")

    def clean_up(self):
        try:
            #self.execute_command('sudo fuser -k /dev/video0') # clean up video processes
            self.execute_command('sudo pkill -f python3')
            self.logger.log(f"SSH connection [clean up]:success")
            self.logger.printTerminal(f"SSH connection [clean up]:success")
        except Exception as e:
            self.logger.log(f"SSH connection [clean up]: Error cleaning up: {e}")
            self.logger.printTerminal(f"SSH connection [clean up]: Error cleaning up: {e}")
            raise Exception("SSH connection [clean up]")

class SSHWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, ssh_conn, command, logger):
        super().__init__()
        self.ssh_conn = ssh_conn
        self.command = command
        self.logger = logger

    def run(self):
        """Execute SSH command."""
        try:
            self.ssh_conn.execute_command(self.command)  # Run the SSH command
            self.progress.emit(f"Executing: {self.command}")
            self.finished.emit()  # Notify that the task is finished
        except Exception as e:
            self.error.emit(f"Error running command: {str(e)}")