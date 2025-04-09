# freebird/ui/search_panel.py

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLineEdit, QPushButton, 
    QCheckBox, QLabel
)
from PyQt6.QtCore import Qt

from freebird.ui.pdf_view import PDFViewWidget

class SearchPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Search text input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search text...")
        self.search_input.returnPressed.connect(self.on_search)
        layout.addWidget(self.search_input, 1)  # Stretch factor 1
        
        # Case sensitive checkbox
        self.case_sensitive_check = QCheckBox("Match case")
        layout.addWidget(self.case_sensitive_check)
        
        # Whole words checkbox
        self.whole_words_check = QCheckBox("Whole words")
        layout.addWidget(self.whole_words_check)
        
        # Search buttons
        self.btn_search = QPushButton("Find")
        self.btn_search.clicked.connect(self.on_search)
        layout.addWidget(self.btn_search)
        
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.clicked.connect(self.on_previous)
        layout.addWidget(self.btn_prev)
        
        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.on_next)
        layout.addWidget(self.btn_next)
        
        # Close button
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(25, 25)
        self.btn_close.setToolTip("Close search panel")
        self.btn_close.clicked.connect(self.hide)
        layout.addWidget(self.btn_close)
        
        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Set initial state
        self.update_ui_state(False)
        
    def on_search(self):
        """Handle search button click."""
        query = self.search_input.text().strip()
        if not query:
            return
            
        view_widget = self.main_window.get_current_view_widget()
        if view_widget and isinstance(view_widget, PDFViewWidget):
            case_sensitive = self.case_sensitive_check.isChecked()
            whole_words = self.whole_words_check.isChecked()
            success = view_widget.search_text(query, case_sensitive, whole_words)
            
            self.update_ui_state(success)
            
            if success:
                # Update the status with match info
                search_results = view_widget.get_search_results()
                self.status_label.setText(f"{search_results.get_current_match_info()}")
            else:
                query_msg = f"No matches found for '{query}'"
                # Check if this might be an image-based PDF
                has_text = self.check_document_has_text()
                if not has_text:
                    query_msg += " - This PDF may contain images or scanned text rather than searchable text"
                self.status_label.setText(query_msg)
    
    def check_document_has_text(self):
        """Check if the current document appears to have searchable text"""
        view_widget = self.main_window.get_current_view_widget()
        if not view_widget or not isinstance(view_widget, PDFViewWidget) or not view_widget.doc:
            return False
            
        # Sample a few pages to check for text
        doc = view_widget.doc
        max_pages = min(5, len(doc))
        text_found = False
        
        for i in range(max_pages):
            try:
                page = doc.load_page(i)
                text = page.get_text("text")
                if text and len(text.strip()) > 20:  # More than 20 chars is likely real text
                    text_found = True
                    break
            except:
                continue
                
        return text_found
    
    def on_next(self):
        """Find next match."""
        view_widget = self.main_window.get_current_view_widget()
        if view_widget and isinstance(view_widget, PDFViewWidget):
            view_widget.find_next(forward=True)
            search_results = view_widget.get_search_results()
            self.status_label.setText(f"{search_results.get_current_match_info()}")
    
    def on_previous(self):
        """Find previous match."""
        view_widget = self.main_window.get_current_view_widget()
        if view_widget and isinstance(view_widget, PDFViewWidget):
            view_widget.find_next(forward=False)
            search_results = view_widget.get_search_results()
            self.status_label.setText(f"{search_results.get_current_match_info()}")
    
    def update_ui_state(self, has_results):
        """Update UI elements based on search state."""
        self.btn_prev.setEnabled(has_results)
        self.btn_next.setEnabled(has_results)
        
    def show_panel(self):
        """Show the search panel and focus the search input."""
        self.show()
        self.search_input.setFocus()
        self.search_input.selectAll()
        
        # Check if there are already search results to display
        view_widget = self.main_window.get_current_view_widget()
        if view_widget and isinstance(view_widget, PDFViewWidget):
            search_results = view_widget.get_search_results()
            if search_results.has_results():
                self.search_input.setText(search_results.query)
                self.update_ui_state(True)
                self.status_label.setText(f"{search_results.get_current_match_info()}")
            else:
                self.update_ui_state(False)
                self.status_label.setText("")