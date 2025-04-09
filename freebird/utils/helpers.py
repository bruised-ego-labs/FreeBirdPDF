# freebird/utils/helpers.py

from PyQt6.QtWidgets import QMessageBox

def show_message(parent, title, message, icon=QMessageBox.Icon.Information):
    """
    Shows a message box with the specified title, message, and icon.
    
    Args:
        parent: The parent widget for the message box
        title: The title for the message box
        message: The message to display
        icon: The icon to use (default: Information)
    """
    msg_box = QMessageBox(parent)
    msg_box.setIcon(icon)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()