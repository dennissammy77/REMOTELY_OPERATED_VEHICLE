import paramiko


class sshConnection:
    def __init__(self, logger, isSshConnected):
        self.logger = logger
        self.isSshConnected = isSshConnected
        self.ssh_client = None
        self.running_processes = []  # To track PIDs of started processes
        '''Connection Details'''
        self.pi_hostname = 'raspberrypi'  # Replace with your Raspberry Pi's IP
        self.username = 'sammy'  # Raspberry Pi username
        self.password = 'password'  # Raspberry Pi password
        self.ip_addr = '192.168.55.17'  # Ip Address connection

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
            self.logger.printTerminal("Connected to ROV over SSH")
            self.isSshConnected = True
            # self.clean_up(self.logger)
        except Exception as e:
            self.isSshConnected = False
            self.logger.printTerminal(f"SSH connection failed: {e}")

    def disconnect_ssh_connection(self):
        """
        Disconnects the SSH session and kills all running processes.
        """
        if not self.ssh_client:
            print("SSH client is not connected.")
            return

        try:
            # Kill all running processes
            for pid in self.running_processes:
                kill_command = f"sudo kill {pid}"
                self.execute_command(kill_command)

            self.running_processes.clear()

            # Close the SSH connection
            self.ssh_client.close()
            self.isSshConnected = False

            self.logger.printTerminal("Disconnected from ROV. All processes terminated.")
        except Exception as e:
            self.logger.printTerminal(f"Error during disconnection: {e}")

    def execute_command(self, command):
        """
        Executes a command over SSH and optionally tracks the process PID.
        :param command: The shell command to execute.
        """
        if not self.ssh_client:
            print("SSH client is not connected.")
            # return None

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            # Retrieve the PID of the started process if available
            pid = stdout.channel.recv_exit_status()
            if pid != 0:
                self.running_processes.append(pid)

            self.logger.log(f"Executed: {command}")
            self.logger.log(f"PID: {pid}")
            if output:
                self.logger.log(f"Output: {output}")
            if error:
                self.logger.log(f"Error: {error}")
            return output
        except Exception as e:
            self.logger.log(f"Failed to execute command: {e}")
            print(f"Failed to execute command: {e}")
            # return None

    def clean_up(self):
        try:
            self.execute_command('sudo fuser -k /dev/video0') # clean up video processes
            self.execute_command('sudo pkill -f python3')
            self.logger.log(f"cleaning up success:")
        except Exception as e:
            self.logger.log(f"Error cleaning up: {e}")
            print(f"Error cleaning up: {e}")
