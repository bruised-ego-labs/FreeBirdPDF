import sys
import fitz  # PyMuPDF
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QScrollArea, QMessageBox, QHBoxLayout, QSpinBox, QSizePolicy,
    QTabWidget, QMenu, QLineEdit
)
from PyQt6.QtGui import (
    QPixmap, QImage, QIcon, QPainter, QAction, QKeySequence,
    QIntValidator
)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect

# --- Constants ---
ASSEMBLY_PREFIX = "assembly:/"
BACKGROUND_IMAGE_FILENAME = "FreeBird.png"
ICON_FILENAME = "pdf_icon.png"

# --- Helper function ---
def show_message(parent, title, message, icon=QMessageBox.Icon.Information):
    msg_box = QMessageBox(parent)
    msg_box.setIcon(icon)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()

# ============================================================
#  PDFViewWidget: Widget to display a single PDF document
# ============================================================
class PDFViewWidget(QWidget):
    def __init__(self, filepath=None, parent=None, is_assembly=False):
        super().__init__(parent)
        self.doc = None
        self.current_filepath = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.is_modified = False
        self.pixmap_cache = {}
        self._is_assembly_target = is_assembly
        self._update_in_progress = False  # Flag to prevent update loops
        
        self.init_ui()
        
        if filepath:
            if self._is_assembly_target:
                self.setup_assembly_doc(filepath)
            else:
                self.load_pdf(filepath)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.image_label = QLabel("Loading...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.image_label.customContextMenuRequested.connect(self.show_context_menu)
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)

    def setup_assembly_doc(self, name):
        """Initializes this widget with a new empty document for assembly."""
        self.close_document()
        self.doc = fitz.open()
        self.current_filepath = ASSEMBLY_PREFIX + name
        self.total_pages = 0
        self.current_page = 0
        self.zoom_factor = 1.0
        self.is_modified = False
        self.pixmap_cache = {}
        self._is_assembly_target = True
        self.display_page()

    def load_pdf(self, filepath):
        """Loads a PDF file into this widget."""
        if self._is_assembly_target:
            print("Warning: Tried to load PDF into assembly widget.")
            return False
            
        try:
            self.close_document()
            self.doc = fitz.open(filepath)
            self.current_filepath = filepath
            self.total_pages = len(self.doc)
            self.current_page = 0
            self.zoom_factor = 1.0
            self.is_modified = False
            self.pixmap_cache = {}
            
            if self.total_pages > 0:
                self.display_page()
            else:
                self.image_label.setText("Document has no pages.")
            return True
        except Exception as e:
            self.doc = None
            self.current_filepath = None
            self.total_pages = 0
            self.image_label.setText(f"Error opening file:\n{e}")
            print(f"ERROR: Could not open PDF file: {filepath}\n{e}")
            return False

    def display_page(self):
        """Displays the current page of the document."""
        # Prevent recursive update loops
        if self._update_in_progress:
            return
            
        self._update_in_progress = True
        
        try:
            # Handle empty document case
            if self.total_pages == 0:
                message = "Assembly Document\n(Add pages...)" if self._is_assembly_target else "Document has no pages."
                self.image_label.setText(message)
                self.image_label.setPixmap(QPixmap())
                return
                
            # Check if current page is valid
            if not self.doc or not (0 <= self.current_page < self.total_pages):
                message = "No page to display." if not self.doc else f"Invalid page index {self.current_page}"
                self.image_label.setText(message)
                self.image_label.setPixmap(QPixmap())
                return
                
            # Check for cached page
            page_key = (self.current_page, self.zoom_factor)
            pixmap = self.pixmap_cache.get(page_key)
            
            # Render the page if not cached
            if not pixmap:
                try:
                    page = self.doc.load_page(self.current_page)
                    matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimage)
                    
                    # Cache the page
                    self.pixmap_cache[page_key] = pixmap
                    
                    # Limit cache size
                    if len(self.pixmap_cache) > 10:
                        self.pixmap_cache.pop(next(iter(self.pixmap_cache)))
                except Exception as e:
                    print(f"ERROR: Render page {self.current_page + 1} for {self.current_filepath}: {e}")
                    error_pixmap = QPixmap(400, 300)
                    error_pixmap.fill(Qt.GlobalColor.white)
                    painter = QPainter(error_pixmap)
                    painter.setPen(Qt.GlobalColor.red)
                    painter.drawText(error_pixmap.rect(), Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.TextWordWrap, 
                                    f"Error rendering page {self.current_page + 1}")
                    painter.end()
                    pixmap = error_pixmap
            
            # Display the page
            self.image_label.setPixmap(pixmap)
            self.image_label.adjustSize()
        finally:
            # Always release the update lock and trigger UI update
            self._update_in_progress = False
            
            # Update UI after display is complete
            # This call is explicit and controlled, not causing cascade
            main_window = self.window()
            if isinstance(main_window, PDFViewer) and main_window.get_current_view_widget() is self:
                main_window.update_ui_for_current_tab()

    def get_current_page_info(self):
        """Returns current page index and total pages."""
        if self.doc:
            # Ensure current_page is valid
            if self.total_pages == 0:
                self.current_page = 0
            elif self.current_page >= self.total_pages:
                self.current_page = max(0, self.total_pages - 1)
            return self.current_page, self.total_pages
        return 0, 0

    def goto_page(self, page_index):
        """Sets the current page and redraws."""
        if self.doc and 0 <= page_index < self.total_pages:
            if self.current_page != page_index:
                self.current_page = page_index
                self.display_page()
                return True
        return False

    def next_page(self):
        """Moves to the next page if possible and redraws."""
        if self.doc and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.display_page()
            return True
        return False

    def prev_page(self):
        """Moves to the previous page if possible and redraws."""
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.display_page()
            return True
        return False

    def apply_zoom(self, factor):
        """Applies a new zoom factor (e.g., 1.0 = 100%)."""
        if self.doc and factor > 0:
            # Limit zoom factor range
            factor = max(0.1, min(factor, 5.0))
            
            # Only update if zoom changed significantly
            if abs(self.zoom_factor - factor) > 0.01:
                self.zoom_factor = factor
                self.pixmap_cache = {}  # Invalidate cache on zoom change
                self.display_page()
                return True
        return False

    # Simple getter methods
    def get_document(self):
        return self.doc

    def get_filepath(self):
        return self.current_filepath

    def is_assembly_target(self):
        return self._is_assembly_target

    def is_document_modified(self):
        return self.is_modified

    def mark_modified(self, modified=True):
        """Sets the modified state and updates the parent tab's text."""
        if self.is_modified == modified:
            return  # No change needed

        self.is_modified = modified
        
        # Find the parent QTabWidget and update tab text
        parent_tab_widget = self.find_parent_tab_widget()
        if parent_tab_widget:
            index = parent_tab_widget.indexOf(self)
            if index != -1:
                current_text = parent_tab_widget.tabText(index)
                
                # Remove existing '*' suffix if present
                if current_text.endswith("*"):
                    base_text = current_text[:-1]
                else:
                    base_text = current_text

                # Add '*' if modified
                new_text = base_text + "*" if self.is_modified else base_text
                parent_tab_widget.setTabText(index, new_text)
                
                # Update tooltip for assembly doc
                if self._is_assembly_target:
                    tooltip_suffix = " (Modified)" if self.is_modified else ""
                    parent_tab_widget.setTabToolTip(index, f"Assembly Document: {base_text}{tooltip_suffix}")

        # Update button states when modified state changes
        main_window = self.window()
        if isinstance(main_window, PDFViewer) and main_window.get_current_view_widget() is self:
            main_window.update_button_states()

    def save_as(self, suggested_dir=""):
        """Saves the current document to a new file."""
        if not self.doc:
            show_message(self, "Nothing to Save", "No document loaded.", QMessageBox.Icon.Warning)
            return False

        # Suggest a filename
        if self.current_filepath and not self.current_filepath.startswith(ASSEMBLY_PREFIX):
            base, ext = os.path.splitext(os.path.basename(self.current_filepath))
            suggested_name = f"{base}_modified{ext}"
        elif self._is_assembly_target:
            base_name = self.current_filepath[len(ASSEMBLY_PREFIX):]
            suggested_name = base_name + ".pdf"
        else:
            suggested_name = "document.pdf"
            
        # Use current directory if none suggested
        if not suggested_dir:
            suggested_dir = os.getcwd()
            
        default_path = os.path.join(suggested_dir, suggested_name)
        
        # Get save path from user
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF As...", default_path, "PDF Files (*.pdf);;All Files (*)"
        )

        if save_path:
            try:
                # Save with optimization options
                self.doc.save(save_path, garbage=4, deflate=True)
                
                # Update document state
                self.current_filepath = save_path
                self._is_assembly_target = False
                self.mark_modified(False)
                
                # Update tab text
                parent_tab_widget = self.find_parent_tab_widget()
                if parent_tab_widget:
                    index = parent_tab_widget.indexOf(self)
                    if index != -1:
                        parent_tab_widget.setTabText(index, os.path.basename(save_path))
                        parent_tab_widget.setTabToolTip(index, save_path)
                
                show_message(self, "Success", f"Document saved to:\n{save_path}")
                return True
            except Exception as e:
                print(f"ERROR: Could not save PDF file: {e}")
                show_message(self, "Error", f"Could not save PDF file:\n{e}", QMessageBox.Icon.Critical)
                return False
        else:
            print("Save cancelled.")
            return False

    def delete_page(self):
        """Deletes the currently visible page."""
        if not self.doc or self.total_pages <= 1:
            show_message(self, "Cannot Delete",
                         "Document must have more than one page.",
                         QMessageBox.Icon.Warning)
            return False

        page_num_to_delete = self.current_page
        page_num_human = page_num_to_delete + 1
        
        # Get tab name for confirmation message
        filename_for_msg = "current document"
        parent_tab_widget = self.find_parent_tab_widget()
        if parent_tab_widget:
            index = parent_tab_widget.indexOf(self)
            if index != -1:
                filename_for_msg = parent_tab_widget.tabText(index).replace("*", "")

        # Confirm deletion
        reply = QMessageBox.question(self, 'Confirm Deletion',
                                    f"Delete page {page_num_human} from '{filename_for_msg}'?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                print(f"Deleting page index: {page_num_to_delete}")
                
                # Perform deletion
                self.doc.delete_page(page_num_to_delete)
                self.total_pages -= 1
                
                # Mark as modified and clear cache
                self.mark_modified(True)
                self.pixmap_cache = {}
                
                # Adjust current page index
                if self.current_page >= self.total_pages and self.total_pages > 0:
                    self.current_page = self.total_pages - 1
                elif self.total_pages == 0:
                    self.current_page = 0
                
                print(f"Page {page_num_human} deleted. New total: {self.total_pages}, Current: {self.current_page}")
                
                # Display updated page
                self.display_page()
                return True
            except Exception as e:
                print(f"ERROR: Could not delete page: {e}")
                show_message(self, "Error", f"Could not delete page:\n{e}", QMessageBox.Icon.Critical)
                return False
        else:
            return False  # Deletion cancelled

    def show_context_menu(self, position: QPoint):
        """Shows the right-click context menu."""
        # Don't show menu for empty documents or assembly targets
        if not self.doc or self._is_assembly_target:
            return
            
        # Find assembly widget first to avoid creating menu if none exists
        assembly_widget = self.find_assembly_widget()
        if not assembly_widget:
            print("No active Assembly Document found.")
            return
            
        # Only create menu if document has pages
        if self.total_pages <= 0:
            return
            
        context_menu = QMenu(self)
        
        # Only add "Add Current Page" if there's a valid current page
        if 0 <= self.current_page < self.total_pages:
            add_current_action = QAction(f"Add Page {self.current_page + 1} to Assembly", self)
            add_current_action.triggered.connect(self.add_current_page_to_assembly)
            context_menu.addAction(add_current_action)
        
        # Add "Add All Pages" if document has pages
        if self.total_pages > 0:
            add_all_action = QAction(f"Add All {self.total_pages} Pages to Assembly", self)
            add_all_action.triggered.connect(self.add_all_pages_to_assembly)
            context_menu.addAction(add_all_action)
        
        # Only show menu if it has actions
        if not context_menu.isEmpty():
            global_pos = self.image_label.mapToGlobal(position)
            context_menu.exec(global_pos)

    def find_parent_tab_widget(self):
        """Helper to find the QTabWidget containing this widget."""
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parent()
        return None

    def find_assembly_widget(self):
        """Finds the currently active assembly widget instance."""
        tab_widget = self.find_parent_tab_widget()
        if tab_widget:
            for i in range(tab_widget.count()):
                widget = tab_widget.widget(i)
                if isinstance(widget, PDFViewWidget) and widget.is_assembly_target():
                    return widget
        return None

    def add_current_page_to_assembly(self):
        """Adds the currently viewed page to the assembly document."""
        assembly_widget = self.find_assembly_widget()
        if assembly_widget and self.doc and 0 <= self.current_page < self.total_pages:
            target_doc = assembly_widget.get_document()
            source_doc = self.doc
            page_num = self.current_page
            
            try:
                # Insert the current page into the assembly document
                target_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
                
                # Update assembly document state
                assembly_widget.total_pages = len(target_doc)
                
                # Navigate to the newly added page in the assembly tab
                new_page_index = assembly_widget.total_pages - 1
                assembly_widget.goto_page(new_page_index)
                
                # Mark assembly as modified
                assembly_widget.mark_modified(True)
                
                # Switch to assembly tab
                tab_widget = self.find_parent_tab_widget()
                if tab_widget:
                    tab_widget.setCurrentWidget(assembly_widget)
                    
                print(f"Added page {page_num + 1} from {os.path.basename(self.current_filepath)} to Assembly.")
            except Exception as e:
                print(f"Error adding page {page_num+1}: {e}")
                show_message(self, "Error", f"Could not add page:\n{e}", QMessageBox.Icon.Warning)

    def add_all_pages_to_assembly(self):
        """Adds all pages from the current document to the assembly document."""
        assembly_widget = self.find_assembly_widget()
        if assembly_widget and self.doc and self.total_pages > 0:
            target_doc = assembly_widget.get_document()
            source_doc = self.doc
            
            try:
                # Remember page count before insertion
                num_pages_before = assembly_widget.total_pages
                
                # Insert all pages
                target_doc.insert_pdf(source_doc)
                
                # Update assembly document state
                assembly_widget.total_pages = len(target_doc)
                
                # Navigate to the first of the newly added pages
                new_page_index = num_pages_before
                assembly_widget.goto_page(new_page_index)
                
                # Mark assembly as modified
                assembly_widget.mark_modified(True)
                
                # Switch to assembly tab
                tab_widget = self.find_parent_tab_widget()
                if tab_widget:
                    tab_widget.setCurrentWidget(assembly_widget)
                    
                print(f"Added all {len(source_doc)} pages from {os.path.basename(self.current_filepath)} to Assembly.")
            except Exception as e:
                print(f"Error adding all pages: {e}")
                show_message(self, "Error", f"Could not add pages:\n{e}", QMessageBox.Icon.Warning)

    def close_document(self):
        """Closes the fitz document if open."""
        if self.doc:
            try:
                filepath_msg = self.current_filepath if self.current_filepath else "(No Path)"
                print(f"Closing fitz document: {filepath_msg}")
                self.doc.close()
            except Exception as e:
                print(f"Error closing document {filepath_msg}: {e}")
            finally:
                self.doc = None
                self.current_filepath = None
                self.total_pages = 0
                self.current_page = 0
                self.is_modified = False
                self.pixmap_cache = {}


# ============================================================
#  PDFViewer: Main Application Window using QTabWidget
# ============================================================
class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.assembly_tab_count = 0
        self.background_pixmap = None
        
        # Load icon and background
        self.load_resources()
        
        # Initialize UI elements
        self.init_ui()
        
        # Set up keyboard shortcut actions
        self.create_actions()
        
        # Set focus policy for keyboard events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def load_resources(self):
        """Loads icon and background image."""
        try:
            script_dir = os.path.dirname(os.path.realpath(__file__))
            
            # Load window icon
            icon_path = os.path.join(script_dir, ICON_FILENAME)
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                print(f"INFO: Icon file '{ICON_FILENAME}' loaded.")
            else:
                print(f"INFO: Icon file '{ICON_FILENAME}' not found.")
                
            # Load background image
            background_image_path = os.path.join(script_dir, BACKGROUND_IMAGE_FILENAME)
            if os.path.exists(background_image_path):
                self.background_pixmap = QPixmap(background_image_path)
                if self.background_pixmap.isNull():
                    print(f"WARNING: Failed to load background image: {BACKGROUND_IMAGE_FILENAME}")
                    self.background_pixmap = None
                else:
                    print(f"INFO: Background image '{BACKGROUND_IMAGE_FILENAME}' loaded.")
            else:
                print(f"INFO: Background image '{BACKGROUND_IMAGE_FILENAME}' not found.")
        except Exception as e:
            print(f"WARNING: Could not load resources: {e}")
            self.background_pixmap = None

    def init_ui(self):
        self.setWindowTitle("FreeBird PDF")
        self.setGeometry(100, 100, 1100, 800)

        # Central Widget and Main Layout
        container_widget = QWidget(self)
        self.setCentralWidget(container_widget)
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar Layout setup first
        toolbar_layout = QHBoxLayout()
        self.create_toolbar(toolbar_layout)  # Create toolbar FIRST - this creates all buttons
        container_layout.addLayout(toolbar_layout)

        # Tab Widget setup
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_ui_for_current_tab)
        # Set stylesheet for transparent background pane
        self.tabs.setStyleSheet("QTabWidget::pane { border: none; background: transparent; } QTabBar::tab { background: lightgray; min-width: 100px; padding: 5px;} QTabBar::tab:selected { background: white; }")
        container_layout.addWidget(self.tabs)

        # NOW call update_button_states AFTER all buttons have been created
        self.update_button_states()

    def paintEvent(self, event):
        """Overrides paint event to draw background image when no tabs are open."""
        # Draw standard window elements first
        super().paintEvent(event)
        
        # Draw background only if image loaded and no tabs are open
        if self.background_pixmap and self.tabs.count() == 0:
            painter = QPainter(self)
            
            # Scale pixmap to fit window while keeping aspect ratio
            scaled_pixmap = self.background_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Calculate position to center the scaled image
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            
            painter.drawPixmap(x, y, scaled_pixmap)

    def create_toolbar(self, layout):
        """Creates the toolbar with buttons and controls."""
        # File operations
        btn_open = QPushButton("Open")
        btn_open.setToolTip("Open PDF file(s)")
        btn_open.clicked.connect(self.open_files)
        layout.addWidget(btn_open)
        
        btn_new_assembly = QPushButton("New Assembly")
        btn_new_assembly.setToolTip("Create empty document tab")
        btn_new_assembly.clicked.connect(self.create_new_assembly_tab)
        layout.addWidget(btn_new_assembly)
        
        self.btn_save_as = QPushButton("Save As...")
        self.btn_save_as.setToolTip("Save active document")
        self.btn_save_as.clicked.connect(self.save_current_tab_as)
        layout.addWidget(self.btn_save_as)
        
        layout.addStretch(1)
        
        # Page manipulation
        self.btn_delete_page = QPushButton("Delete Page")
        self.btn_delete_page.setToolTip("Delete current page")
        self.btn_delete_page.clicked.connect(self.delete_current_tab_page)
        layout.addWidget(self.btn_delete_page)
        
        # Navigation
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.setToolTip("Previous page (Left Arrow/PgUp)")
        self.btn_prev.clicked.connect(self.prev_page)
        layout.addWidget(self.btn_prev)
        
        # Page jump
        goto_label = QLabel("Go To:")
        layout.addWidget(goto_label)
        
        self.goto_page_input = QLineEdit()
        self.goto_page_input.setPlaceholderText("#")
        self.goto_page_input.setFixedWidth(50)
        self.goto_page_input.setValidator(QIntValidator(1, 999999))
        self.goto_page_input.returnPressed.connect(self.jump_to_page)
        layout.addWidget(self.goto_page_input)
        
        self.btn_goto = QPushButton("Go")
        self.btn_goto.setToolTip("Jump to page number")
        self.btn_goto.clicked.connect(self.jump_to_page)
        layout.addWidget(self.btn_goto)
        
        # Page info
        self.page_label = QLabel("Page: - / -")
        self.page_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.page_label)
        
        self.btn_next = QPushButton("Next")
        self.btn_next.setToolTip("Next page (Right Arrow/PgDn)")
        self.btn_next.clicked.connect(self.next_page)
        layout.addWidget(self.btn_next)
        
        layout.addStretch(1)
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        layout.addWidget(zoom_label)
        
        self.zoom_spinbox = QSpinBox()
        self.zoom_spinbox.setRange(10, 500)
        self.zoom_spinbox.setSingleStep(10)
        self.zoom_spinbox.setValue(100)
        self.zoom_spinbox.setSuffix(" %")
        self.zoom_spinbox.valueChanged.connect(self.apply_zoom)
        self.zoom_spinbox.setToolTip("Adjust zoom")
        layout.addWidget(self.zoom_spinbox)

    def create_actions(self):
        """Creates QActions for keyboard shortcuts."""
        # Previous page shortcuts
        self.prev_action = QAction("Previous Page", self)
        self.prev_action.setShortcuts([QKeySequence(Qt.Key.Key_Left), QKeySequence(Qt.Key.Key_PageUp)])
        self.prev_action.triggered.connect(self.prev_page)
        self.addAction(self.prev_action)
        
        # Next page shortcuts
        self.next_action = QAction("Next Page", self)
        self.next_action.setShortcuts([QKeySequence(Qt.Key.Key_Right), QKeySequence(Qt.Key.Key_PageDown)])
        self.next_action.triggered.connect(self.next_page)
        self.addAction(self.next_action)
        
        # First page shortcut
        self.home_action = QAction("First Page", self)
        self.home_action.setShortcut(QKeySequence(Qt.Key.Key_Home))
        self.home_action.triggered.connect(self.goto_first_page)
        self.addAction(self.home_action)
        
        # Last page shortcut
        self.end_action = QAction("Last Page", self)
        self.end_action.setShortcut(QKeySequence(Qt.Key.Key_End))
        self.end_action.triggered.connect(self.goto_last_page)
        self.addAction(self.end_action)

    def get_current_view_widget(self):
        """Gets the PDFViewWidget from the currently active tab."""
        return self.tabs.currentWidget()

    def open_files(self):
        """Opens one or more PDF files, each in a new tab."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open PDF File(s)", "", "PDF Files (*.pdf);;All Files (*)"
        )
        
        opened_count = 0
        first_new_index = -1
        
        for file_path in file_paths:
            # Check if already open
            already_open_index = -1
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                if isinstance(widget, PDFViewWidget) and widget.get_filepath() == file_path:
                    already_open_index = i
                    break
                    
            if already_open_index != -1:
                self.tabs.setCurrentIndex(already_open_index)
                continue
                
            # Create new view widget
            view_widget = PDFViewWidget(is_assembly=False)
            
            # Load PDF file
            if view_widget.load_pdf(file_path):
                filename = os.path.basename(file_path)
                index = self.tabs.addTab(view_widget, filename)
                self.tabs.setTabToolTip(index, file_path)
                
                if first_new_index == -1:
                    first_new_index = index
                    
                opened_count += 1
            else:
                view_widget.deleteLater()
                
        if first_new_index != -1:
            self.tabs.setCurrentIndex(first_new_index)
            
        if opened_count == 0 and file_paths:
            print("No files opened successfully.")
            
        # Trigger repaint for background if needed
        self.update()

    def close_tab(self, index):
        """Handles the request to close a tab."""
        widget_to_close = self.tabs.widget(index)
        
        if not isinstance(widget_to_close, PDFViewWidget):
            self.tabs.removeTab(index)
            return
            
        # Check for unsaved changes
        if widget_to_close.is_document_modified():
            filename = self.tabs.tabText(index).replace("*", "")
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                f"'{filename}' has changes. Save before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                success = self.save_current_tab_as(index=index)
                if not success:
                    return  # Exit if save failed/cancelled
            elif reply == QMessageBox.StandardButton.Cancel:
                return  # Exit if cancelled
                
        # Close the tab
        tab_text = self.tabs.tabText(index)
        print(f"Closing tab: {tab_text}")
        widget_to_close.close_document()
        self.tabs.removeTab(index)
        
        # Trigger repaint for background if needed
        self.update()

    def update_ui_for_current_tab(self, index=-1):
        """Updates UI elements to reflect the current tab's state."""
        current_widget = self.get_current_view_widget()
        
        if current_widget and isinstance(current_widget, PDFViewWidget) and current_widget.doc:
            # Update page display
            page, total = current_widget.get_current_page_info()
            current_page_display = max(0, page) + 1 if total > 0 else 0
            self.page_label.setText(f"Page: {current_page_display} / {total}")
            
            # Update zoom display
            self.zoom_spinbox.blockSignals(True)
            self.zoom_spinbox.setValue(int(current_widget.zoom_factor * 100))
            self.zoom_spinbox.blockSignals(False)
            
            # Clear page input
            self.goto_page_input.clear()
        else:
            # No document loaded
            self.page_label.setText("Page: - / -")
            self.zoom_spinbox.blockSignals(True)
            self.zoom_spinbox.setValue(100)
            self.zoom_spinbox.blockSignals(False)
            self.goto_page_input.clear()
            
        # Update button states
        self.update_button_states()
        
        # Trigger repaint
        self.update()

    def update_button_states(self):
        current_widget = self.get_current_view_widget()
        has_valid_widget_check = current_widget and isinstance(current_widget, PDFViewWidget) and current_widget.doc
        is_widget_valid_bool = bool(has_valid_widget_check)
        
        if is_widget_valid_bool:
            page, total = current_widget.get_current_page_info()
            valid_page_index = 0 <= page < total
            can_go_prev = valid_page_index and page > 0
            can_go_next = valid_page_index and page < total - 1
            can_delete = total > 1
            is_modified = current_widget.is_document_modified()
            can_goto = total > 0
        else:
            can_go_prev = False
            can_go_next = False
            can_delete = False
            is_modified = False
            can_goto = False
        
        # CRITICAL: Check if each button exists before setting its state
        if hasattr(self, 'btn_save_as') and self.btn_save_as is not None:
            self.btn_save_as.setEnabled(is_widget_valid_bool and is_modified)
        
        if hasattr(self, 'btn_delete_page') and self.btn_delete_page is not None:
            self.btn_delete_page.setEnabled(is_widget_valid_bool and can_delete)
        
        if hasattr(self, 'btn_prev') and self.btn_prev is not None:
            self.btn_prev.setEnabled(is_widget_valid_bool and can_go_prev)
        
        if hasattr(self, 'btn_next') and self.btn_next is not None:
            self.btn_next.setEnabled(is_widget_valid_bool and can_go_next)
        
        if hasattr(self, 'zoom_spinbox') and self.zoom_spinbox is not None:
            self.zoom_spinbox.setEnabled(is_widget_valid_bool)
        
        if hasattr(self, 'goto_page_input') and self.goto_page_input is not None:
            self.goto_page_input.setEnabled(is_widget_valid_bool and can_goto)
        
        if hasattr(self, 'btn_goto') and self.btn_goto is not None:
            self.btn_goto.setEnabled(is_widget_valid_bool and can_goto)

    def save_current_tab_as(self, checked=None, *, index=None):
        """Saves the document in the specified tab index, or the current tab if index is None."""
        widget_to_save = None
        
        # Prioritize explicitly passed valid index
        if index is not None and 0 <= index < self.tabs.count():
            widget_to_save = self.tabs.widget(index)
            
        # If no valid index was passed, default to the currently selected tab
        if widget_to_save is None:
            widget_to_save = self.get_current_view_widget()
            
        # Proceed only if we successfully identified a valid widget
        if widget_to_save and isinstance(widget_to_save, PDFViewWidget):
            suggested_dir = ""
            success = widget_to_save.save_as(suggested_dir)
            
            if success and widget_to_save is self.get_current_view_widget():
                self.update_button_states()
                
            return success
        else:
            print("Save Error: No valid document selected/found to save.")
            return False

    def delete_current_tab_page(self):
        """Deletes the current page in the active tab."""
        current_widget = self.get_current_view_widget()
        if current_widget and isinstance(current_widget, PDFViewWidget):
            current_widget.delete_page()
            # UI update is handled by the widget's display_page method
        else:
            show_message(self, "Delete Error", "No document selected.", QMessageBox.Icon.Warning)

    def create_new_assembly_tab(self):
        """Creates a new tab holding an empty assembly document."""
        self.assembly_tab_count += 1
        assembly_name = f"Untitled Assembly {self.assembly_tab_count}"
        
        assembly_widget = PDFViewWidget(is_assembly=True)
        assembly_widget.setup_assembly_doc(assembly_name)
        
        index = self.tabs.addTab(assembly_widget, assembly_name + "*")
        self.tabs.setTabToolTip(index, f"Assembly Document: {assembly_name} (Unsaved)")
        self.tabs.setCurrentIndex(index)
        
        print(f"Created new assembly tab: {assembly_name}")
        
        # Trigger repaint
        self.update()

    # Navigation methods
    def next_page(self):
        """Go to next page in current document."""
        widget = self.get_current_view_widget()
        if widget and isinstance(widget, PDFViewWidget):
            widget.next_page()

    def prev_page(self):
        """Go to previous page in current document."""
        widget = self.get_current_view_widget()
        if widget and isinstance(widget, PDFViewWidget):
            widget.prev_page()

    def jump_to_page(self):
        """Jump to specified page number."""
        widget = self.get_current_view_widget()
        if not (widget and isinstance(widget, PDFViewWidget)):
            return
            
        try:
            page_num_str = self.goto_page_input.text().strip()
            if not page_num_str:
                return
                
            page_num = int(page_num_str)
            page_index = page_num - 1
            
            _, total_pages = widget.get_current_page_info()
            
            if 0 <= page_index < total_pages:
                widget.goto_page(page_index)
            else:
                show_message(
                    self, 
                    "Invalid Page", 
                    f"Page must be between 1 and {total_pages}.", 
                    QMessageBox.Icon.Warning
                )
                self.goto_page_input.selectAll()
        except ValueError:
            show_message(self, "Invalid Input", "Enter page number.", QMessageBox.Icon.Warning)
            self.goto_page_input.selectAll()

    def goto_first_page(self):
        """Go to first page in current document."""
        widget = self.get_current_view_widget()
        if widget and isinstance(widget, PDFViewWidget):
            widget.goto_page(0)

    def goto_last_page(self):
        """Go to last page in current document."""
        widget = self.get_current_view_widget()
        if widget and isinstance(widget, PDFViewWidget):
            _, total_pages = widget.get_current_page_info()
            if total_pages > 0:
                widget.goto_page(total_pages - 1)

    def apply_zoom(self):
        """Apply zoom level from spinbox."""
        widget = self.get_current_view_widget()
        if widget and isinstance(widget, PDFViewWidget):
            factor = self.zoom_spinbox.value() / 100.0
            widget.apply_zoom(factor)

    def closeEvent(self, event):
        """Handle application close event."""
        # Check for unsaved changes
        modified_tabs_indices = []
        modified_tabs_names = []
        
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, PDFViewWidget) and widget.is_document_modified():
                modified_tabs_indices.append(i)
                
                # Get user-friendly name for the document
                if widget.is_assembly_target():
                    name_for_msg = self.tabs.tabText(i).replace("*", "")
                elif widget.get_filepath():
                    name_for_msg = os.path.basename(widget.get_filepath())
                else:
                    name_for_msg = self.tabs.tabText(i).replace("*", "")
                    
                modified_tabs_names.append(name_for_msg)
                
        # Prompt to save unsaved changes
        if modified_tabs_names:
            filenames = "\n - ".join(modified_tabs_names)
            reply = QMessageBox.question(
                self, 
                'Unsaved Changes', 
                f"Documents have unsaved changes:\n - {filenames}\n\nQuit without saving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                if modified_tabs_indices:
                    self.tabs.setCurrentIndex(modified_tabs_indices[0])
                return
                
        # Close all documents
        print("Closing application...")
        indices = list(range(self.tabs.count()))
        
        for i in reversed(indices):
            widget = self.tabs.widget(i)
            if isinstance(widget, PDFViewWidget):
                widget.close_document()
                
        event.accept()


# --- Application Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("FreeBird PDF")
    viewer = PDFViewer()
    viewer.show()
    sys.exit(app.exec())