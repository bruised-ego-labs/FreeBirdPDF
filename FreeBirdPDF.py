# FreeBirdPDF.py
import sys
from PyQt6.QtWidgets import QApplication

# Import main components
from freebird.ui.main_window import PDFViewer

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FreeBird PDF")
    viewer = PDFViewer()
    viewer.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()