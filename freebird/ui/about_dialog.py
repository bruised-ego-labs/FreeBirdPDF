# freebird/ui/about_dialog.py

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtGui import (
    QPixmap, QFont
)
from PyQt6.QtCore import Qt

from freebird.constants import BACKGROUND_IMAGE_PATH, VERSION

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About FreeBird PDF")
        self.setFixedSize(550, 600)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        layout = QVBoxLayout(self)
        
        # Try to load logo if available
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                pixmap = QPixmap(BACKGROUND_IMAGE_PATH)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio, 
                                                 Qt.TransformationMode.SmoothTransformation)
                    logo_label.setPixmap(scaled_pixmap)
                    layout.addWidget(logo_label)
        except Exception as e:
            print(f"Could not load logo: {e}")
        
        # Version title
        title_label = QLabel(f"Project FreeBird v{VERSION}")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("(Codename: Acrobat's Nightmare)")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_font.setItalic(True)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle_label)
        
        # About text
        about_text = """
        <p><b>The PDF Editor They Don't Want You To Have</b></p>
        
        <p>A <i>Bruised Ego Labs</i> Production<br>
        Released under the Great Bird of Freedom License*</p>
        
        <p>This technological marvel was painstakingly assembled using Python, PyQt6, 
        and the surprisingly potent PyMuPDF library. We at Bruised Ego Labs dared to ask: 
        "What if viewing, assembling, rearranging, and occasionally deleting pages from PDFs 
        didn't require a second mortgage?"</p>
        
        <p>This project is the answer nobody at Adobe wanted to hear. It's proof that sometimes, 
        "good enough" is actually... well, available.</p>
        
        <p><small>* The MIT License, but with more Freedom</small></p>
        
        <p><b>Created with the assistance of:</b><br>
        - Gemini Advanced 2.5 Pro: The initial mastermind<br>
        - ChatGPT 4.0: Creator of Patch the Eagle<br>
        - Claude 3.7 Sonnet: The wise cleanup crew</p>
        """
        
        text_label = QLabel(about_text)
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.TextFormat.RichText)
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(text_label)
        
        # Patch says
        patch_label = QLabel("Patch the Eagle says: \"Freedom isn't free, but your PDF editor definitely should be.\"")
        patch_label.setWordWrap(True)
        patch_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        patch_font = QFont()
        patch_font.setItalic(True)
        patch_label.setFont(patch_font)
        layout.addWidget(patch_label)
        
        # Close button
        close_button = QPushButton("I Feel Free Now")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)