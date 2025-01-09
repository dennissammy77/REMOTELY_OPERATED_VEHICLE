import datetime
from PyQt5.QtWidgets import QTextEdit

class Logger:
    def __init__(self, parent=None):
        """
        Initialize the Logger.
        :param parent: The parent widget containing the QTextEdit.
        """
        if parent:
            self.terminalTextEdit = parent.findChild(QTextEdit, 'terminalOutputLabel')
            if not self.terminalTextEdit:
                print("Error: terminalTextEdit not found. Please check the name in the .ui file.")
        else:
            self.terminalTextEdit = None
            print("Error: Parent widget not provided. Cannot locate terminalTextEdit.")

    def log(self, message):
        """Log a message to the terminal and optionally to a file."""
        formatted_message = f"[LOG]: {message}"
        print(formatted_message)

    def printTerminal(self, text):
        """
        Prints text to the serial terminal on the configuration tab.
        :param text: The text to display on the serial terminal.
        """
        if self.terminalTextEdit:
            currentText = self.terminalTextEdit.toPlainText()
            newText = f"[{datetime.datetime.now().strftime('%H:%M:%S')}]: {text}\n"
            self.terminalTextEdit.setPlainText(currentText + newText)
            self.terminalTextEdit.verticalScrollBar().setValue(self.terminalTextEdit.verticalScrollBar().maximum())
        else:
            print("Error: terminalTextEdit is not initialized.")
