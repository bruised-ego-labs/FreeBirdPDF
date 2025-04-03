import sys
import fitz  # PyMuPDF
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QScrollArea, QMessageBox, QHBoxLayout, QSpinBox, QSizePolicy,
    QTabWidget, QMenu # Import QMenu
)
from PyQt6.QtGui import QPixmap, QImage, QIcon, QPainter, QAction # Import QAction
from PyQt6.QtCore import Qt, QSize, QPoint

# --- Constants ---
ASSEMBLY_PREFIX = "assembly:/" # Use a prefix to identify assembly docs

# --- Helper function for consistent message boxes ---
# ... (show_message function remains the same) ...
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
    # __init__, init_ui, load_pdf, display_page, get_current_page_info,
    # goto_page, next_page, prev_page, apply_zoom remain largely the same
    # Minor updates might be needed below based on new features

    def __init__(self, filepath=None, parent=None, is_assembly=False): # Add is_assembly flag
        super().__init__(parent)
        self.doc = None
        self.current_filepath = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.is_modified = False
        self.pixmap_cache = {}
        self._is_assembly_target = is_assembly # Store if this is the assembly doc

        self.init_ui()

        if filepath:
            # Handle regular file loading or setting up assembly doc
            if self._is_assembly_target:
                self.setup_assembly_doc(filepath) # Special setup
            else:
                self.load_pdf(filepath)


    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel("Loading...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Enable context menu policy on the label where the PDF is shown
        self.image_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.image_label.customContextMenuRequested.connect(self.show_context_menu)

        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)

    def setup_assembly_doc(self, name):
        """Initializes this widget with a new empty document for assembly."""
        self.close_document() # Ensure no previous doc
        self.doc = fitz.open() # Create new empty PDF
        self.current_filepath = ASSEMBLY_PREFIX + name # Mark with prefix
        self.total_pages = 0
        self.current_page = 0
        self.zoom_factor = 1.0
        self.is_modified = False # Starts unmodified
        self.pixmap_cache = {}
        self._is_assembly_target = True
        self.display_page() # Show "no pages" message


    def load_pdf(self, filepath):
        if self._is_assembly_target:
            print("Warning: Tried to load a regular PDF into an assembly widget.")
            return False # Don't load regular files into assembly widget

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
        # --- Add handling for Assembly Target having 0 pages ---
        if self.total_pages == 0:
             if self._is_assembly_target:
                 self.image_label.setText("Assembly Document\n(Add pages using right-click from other tabs)")
             else:
                 self.image_label.setText("Document has no pages.")
             self.image_label.setPixmap(QPixmap())
             return
        # --- Original display logic ---
        if not self.doc or not (0 <= self.current_page < self.total_pages):
            self.image_label.setText("No page to display." if not self.doc else "Invalid page number.")
            self.image_label.setPixmap(QPixmap())
            return

        page_key = (self.current_page, self.zoom_factor)
        pixmap = self.pixmap_cache.get(page_key)

        if not pixmap:
            try:
                page = self.doc.load_page(self.current_page)
                matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
                self.pixmap_cache[page_key] = pixmap
                if len(self.pixmap_cache) > 10:
                    self.pixmap_cache.pop(next(iter(self.pixmap_cache)))
            except Exception as e:
                 print(f"ERROR: Could not render page {self.current_page + 1} for {self.current_filepath}: {e}")
                 error_pixmap = QPixmap(400, 300)
                 error_pixmap.fill(Qt.GlobalColor.white)
                 painter = QPainter(error_pixmap)
                 painter.setPen(Qt.GlobalColor.red)
                 painter.drawText(error_pixmap.rect(), Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.TextWordWrap , f"Error rendering page {self.current_page + 1}")
                 painter.end()
                 pixmap = error_pixmap

        self.image_label.setPixmap(pixmap)
        self.image_label.adjustSize()

    def get_current_page_info(self):
        """Returns current page index and total pages."""
        if self.doc:
            # Ensure current_page is valid, especially after potential deletions
            if self.total_pages == 0:
                self.current_page = 0 # Or maybe -1? Let's stick with 0
            elif self.current_page >= self.total_pages:
                self.current_page = max(0, self.total_pages - 1)
            return self.current_page, self.total_pages
        return 0, 0

    # goto_page, next_page, prev_page, apply_zoom remain the same

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
             # Limit zoom factor range if desired, e.g., 0.1 to 5.0
             factor = max(0.1, min(factor, 5.0))
             if abs(self.zoom_factor - factor) > 0.01: # Avoid re-render if no significant change
                 self.zoom_factor = factor
                 self.pixmap_cache = {} # Invalidate cache on zoom change
                 self.display_page()
                 return True
        return False
    
    def goto_page(self, page_index):
        """Sets the current page and redraws."""
        if self.doc and 0 <= page_index < self.total_pages:
            if self.current_page != page_index:
                self.current_page = page_index
                self.display_page()
                # Update main UI immediately after successful jump
                main_window = self.window()
                if isinstance(main_window, PDFViewer) and main_window.get_current_view_widget() is self:
                     main_window.update_ui_for_current_tab()
                return True
        return False

    def get_document(self):
         """Returns the fitz.Document object."""
         return self.doc

    def get_filepath(self):
         """Returns the current filepath."""
         return self.current_filepath

    def is_assembly_target(self):
         """Returns True if this widget holds the assembly document."""
         return self._is_assembly_target

    def mark_modified(self, modified=True):
        """Sets the modified state and updates the parent tab's text."""
        if self.is_modified == modified:
             return # No change needed

        self.is_modified = modified

        # Find the parent QTabWidget
        parent_widget = self.parent()
        parent_tab_widget = None
        if isinstance(parent_widget, QTabWidget): # Direct parent
             parent_tab_widget = parent_widget
        else: # Search upwards (might be nested)
             current_parent = parent_widget
             while current_parent is not None:
                  if isinstance(current_parent, QTabWidget):
                       parent_tab_widget = current_parent
                       break
                  current_parent = current_parent.parent()

        if parent_tab_widget:
            index = parent_tab_widget.indexOf(self)
            if index != -1:
                current_text = parent_tab_widget.tabText(index)
                # Remove existing '*' suffix if present
                if current_text.endswith("*"):
                    base_text = current_text[:-1]
                else:
                    base_text = current_text

                # Add '*' if modified, otherwise use base text
                new_text = base_text + "*" if self.is_modified else base_text
                parent_tab_widget.setTabText(index, new_text)
                # Update tooltip for assembly doc
                if self._is_assembly_target:
                     tooltip_suffix = " (Modified)" if self.is_modified else " (Unsaved)" if not self.current_filepath.startswith(ASSEMBLY_PREFIX + "Untitled") else ""
                     parent_tab_widget.setTabToolTip(index, f"Assembly Document{tooltip_suffix}")


    def is_document_modified(self):
         """Checks if the document has unsaved changes."""
         return self.is_modified

    # --- Save As ---
    def save_as(self, suggested_dir=""):
        """Saves the current document (regular or assembly) to a new file."""
        if not self.doc:
            show_message(self, "Nothing to Save", "No document loaded in this tab.", QMessageBox.Icon.Warning)
            return False

        # Suggest a filename
        if self.current_filepath and not self.current_filepath.startswith(ASSEMBLY_PREFIX):
            base, ext = os.path.splitext(os.path.basename(self.current_filepath))
            suggested_name = f"{base}_modified{ext}"
        elif self._is_assembly_target:
             suggested_name = self.current_filepath[len(ASSEMBLY_PREFIX):] + ".pdf" # e.g., Untitled.pdf
        else:
             suggested_name = "document.pdf"

        default_path = os.path.join(suggested_dir, suggested_name)

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF As...", default_path, "PDF Files (*.pdf);;All Files (*)"
        )

        if save_path:
            try:
                print(f"Saving document {'(Assembly)' if self._is_assembly_target else ''} to: {save_path}")
                # Use garbage collection and deflate for potentially smaller file size
                self.doc.save(save_path, garbage=4, deflate=True)
                self.current_filepath = save_path # Update path
                self._is_assembly_target = False # Once saved, it's a regular doc
                self.mark_modified(False) # No longer modified relative to the saved file
                # Update tab text directly after saving (mark_modified handles '*')
                parent_tab_widget = self.find_parent_tab_widget()
                if parent_tab_widget:
                    index = parent_tab_widget.indexOf(self)
                    if index != -1:
                         base_name = os.path.basename(save_path)
                         parent_tab_widget.setTabText(index, base_name)
                         parent_tab_widget.setTabToolTip(index, save_path)

                show_message(self, "Success", f"Document saved successfully to:\n{save_path}")
                print(f"Save successful.")
                return True
            except Exception as e:
                print(f"ERROR: Could not save PDF file: {e}")
                show_message(self, "Error", f"Could not save PDF file:\n{e}", QMessageBox.Icon.Critical)
                return False
        else:
            print("Save cancelled by user.")
            return False

    # --- Delete Page ---
    def delete_page(self):
        """Deletes the currently visible page."""
        if not self.doc or self.total_pages <= 1:
            show_message(self, "Cannot Delete",
                         "Cannot delete page. Document must have more than one page.",
                         QMessageBox.Icon.Warning)
            return False

        page_num_to_delete = self.current_page
        page_num_human = page_num_to_delete + 1

        reply = QMessageBox.question(self, 'Confirm Deletion',
                                     f"Are you sure you want to delete page {page_num_human} from '{os.path.basename(self.current_filepath)}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                print(f"Attempting to delete page: {page_num_to_delete}")
                self.doc.delete_page(page_num_to_delete)
                self.total_pages -= 1
                self.mark_modified(True)
                self.pixmap_cache = {} # Clear cache

                # Adjust current page if needed (display_page call will handle index check)
                # Ensure page index remains valid for the next display call
                if self.current_page >= self.total_pages:
                    self.current_page = max(0, self.total_pages - 1)

                print(f"Page deleted. New total pages: {self.total_pages}, Current page: {self.current_page}")

                show_message(self, "Success", f"Page {page_num_human} deleted.")
                self.display_page() # Refresh display
                # Need to signal main window to update UI (handled by caller)
                return True

            except Exception as e:
                 print(f"ERROR: Could not delete page: {e}")
                 show_message(self, "Error", f"Could not delete page:\n{e}", QMessageBox.Icon.Critical)
                 return False
        else:
            return False # Deletion cancelled

    # --- Context Menu ---
    def show_context_menu(self, position: QPoint):
        """Shows the right-click context menu."""
        if not self.doc or self._is_assembly_target:
            return # No menu for assembly doc or if no doc loaded

        assembly_widget = self.find_assembly_widget()
        if not assembly_widget:
            # Maybe show a message? Or just disable actions? For now, do nothing.
            print("No active Assembly Document found.")
            return

        context_menu = QMenu(self)

        add_current_action = QAction(f"Add Page {self.current_page + 1} to Assembly", self)
        add_current_action.triggered.connect(self.add_current_page_to_assembly)
        context_menu.addAction(add_current_action)

        add_all_action = QAction("Add All Pages to Assembly", self)
        add_all_action.triggered.connect(self.add_all_pages_to_assembly)
        context_menu.addAction(add_all_action)

        # Map the position from the label to global coordinates
        global_pos = self.image_label.mapToGlobal(position)
        context_menu.exec(global_pos)

    def find_parent_tab_widget(self):
        """Helper to find the QTabWidget containing this widget."""
        parent_widget = self.parent()
        while parent_widget is not None and not isinstance(parent_widget, QTabWidget):
            parent_widget = parent_widget.parent()
        return parent_widget

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
        if assembly_widget and self.doc:
            target_doc = assembly_widget.get_document()
            source_doc = self.doc
            page_num = self.current_page
            try:
                target_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
                assembly_widget.total_pages = len(target_doc)
                assembly_widget.mark_modified(True)
                # Navigate to the newly added page in the assembly tab
                new_page_index = assembly_widget.total_pages - 1
                assembly_widget.goto_page(new_page_index)
                # Bring assembly tab to front? Optional.
                # tab_widget = self.find_parent_tab_widget()
                # if tab_widget: tab_widget.setCurrentWidget(assembly_widget)
                print(f"Added page {page_num + 1} from {os.path.basename(self.current_filepath)} to Assembly.")
            except Exception as e:
                print(f"Error adding page {page_num+1} to assembly: {e}")
                show_message(self, "Error", f"Could not add page to assembly:\n{e}", QMessageBox.Icon.Warning)


    def add_all_pages_to_assembly(self):
        """Adds all pages from the current document to the assembly document."""
        assembly_widget = self.find_assembly_widget()
        if assembly_widget and self.doc:
            target_doc = assembly_widget.get_document()
            source_doc = self.doc
            try:
                num_pages_before = assembly_widget.total_pages
                target_doc.insert_pdf(source_doc)
                assembly_widget.total_pages = len(target_doc)
                assembly_widget.mark_modified(True)
                 # Navigate to the first of the newly added pages
                new_page_index = num_pages_before
                assembly_widget.goto_page(new_page_index)
                # Bring assembly tab to front? Optional.
                # tab_widget = self.find_parent_tab_widget()
                # if tab_widget: tab_widget.setCurrentWidget(assembly_widget)
                print(f"Added all {len(source_doc)} pages from {os.path.basename(self.current_filepath)} to Assembly.")
            except Exception as e:
                 print(f"Error adding all pages to assembly: {e}")
                 show_message(self, "Error", f"Could not add all pages to assembly:\n{e}", QMessageBox.Icon.Warning)

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
    # __init__ remains the same

    def __init__(self):
        super().__init__()
        self.assembly_tab_count = 0 # To create unique assembly names
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("FreeBird PDF")
        self.setGeometry(100, 100, 1000, 800)

        # --- Set Window Icon ---
        try:
            script_dir = os.path.dirname(os.path.realpath(__file__))
            icon_path = os.path.join(script_dir, 'pdf_icon.png')
            if os.path.exists(icon_path):
                 self.setWindowIcon(QIcon(icon_path))
            else:
                 print("INFO: Icon file 'pdf_icon.png' not found.")
        except Exception as e:
            print(f"WARNING: Could not set window icon: {e}")

        # --- Central Widget ---
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Toolbar ---
        toolbar_layout = QHBoxLayout()
        self.create_toolbar(toolbar_layout)
        main_layout.addLayout(toolbar_layout)

        # --- Tab Widget ---
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_ui_for_current_tab)

        main_layout.addWidget(self.tabs)
        self.update_button_states()


    def create_toolbar(self, layout):
        # File Operations
        btn_open = QPushButton("Open")
        btn_open.setToolTip("Open PDF file(s)")
        btn_open.clicked.connect(self.open_files)
        layout.addWidget(btn_open)

        # --- Add New Assembly Button ---
        btn_new_assembly = QPushButton("New Assembly")
        btn_new_assembly.setToolTip("Create a new empty document tab for assembling pages")
        btn_new_assembly.clicked.connect(self.create_new_assembly_tab)
        layout.addWidget(btn_new_assembly)

        self.btn_save_as = QPushButton("Save As...")
        self.btn_save_as.setToolTip("Save the document in the active tab")
        # --- Connect Save As Button ---
        self.btn_save_as.clicked.connect(self.save_current_tab_as)
        layout.addWidget(self.btn_save_as)

        layout.addStretch(1)

        # Page Navigation/Manipulation
        self.btn_delete_page = QPushButton("Delete Page")
        self.btn_delete_page.setToolTip("Delete the current page in the active tab")
        # --- Connect Delete Page Button ---
        self.btn_delete_page.clicked.connect(self.delete_current_tab_page)
        layout.addWidget(self.btn_delete_page)

        btn_prev = QPushButton("Previous")
        btn_prev.setToolTip("Go to the previous page in the active tab")
        btn_prev.clicked.connect(self.prev_page)
        self.btn_prev = btn_prev
        layout.addWidget(btn_prev)

        self.page_label = QLabel("Page: - / -")
        self.page_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.page_label)

        btn_next = QPushButton("Next")
        btn_next.setToolTip("Go to the next page in the active tab")
        btn_next.clicked.connect(self.next_page)
        self.btn_next = btn_next
        layout.addWidget(btn_next)

        layout.addStretch(1)

        # Zoom Controls
        zoom_label = QLabel("Zoom:")
        layout.addWidget(zoom_label)
        self.zoom_spinbox = QSpinBox()
        self.zoom_spinbox.setRange(10, 500)
        self.zoom_spinbox.setSingleStep(10)
        self.zoom_spinbox.setValue(100)
        self.zoom_spinbox.setSuffix(" %")
        self.zoom_spinbox.valueChanged.connect(self.apply_zoom)
        self.zoom_spinbox.setToolTip("Adjust zoom for the active tab")
        layout.addWidget(self.zoom_spinbox)

    # get_current_view_widget remains the same
    def get_current_view_widget(self):
        """Gets the PDFViewWidget from the currently active tab."""
        return self.tabs.currentWidget()

    # open_files remains the same
    def open_files(self):
        """Opens one or more PDF files, each in a new tab."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open PDF File(s)", "", "PDF Files (*.pdf);;All Files (*)"
        )

        opened_count = 0
        first_new_index = -1
        for file_path in file_paths:
            already_open = False
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                # Check if it's a PDF widget and if the path matches (or tooltip if path not set)
                if isinstance(widget, PDFViewWidget) and widget.get_filepath() == file_path:
                     # Or maybe check tooltip: self.tabs.tabToolTip(i) == file_path
                    self.tabs.setCurrentIndex(i)
                    already_open = True
                    break
            if already_open:
                continue

            # Ensure we don't try to open into an assembly target slot by mistake
            view_widget = PDFViewWidget(is_assembly=False) # Explicitly not assembly
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
             print("No files were opened successfully.")


    # close_tab needs update for Save As interaction
    def close_tab(self, index):
        """Handles the request to close a tab."""
        widget_to_close = self.tabs.widget(index)
        if not isinstance(widget_to_close, PDFViewWidget):
             self.tabs.removeTab(index)
             return

        if widget_to_close.is_document_modified():
             filename = self.tabs.tabText(index).replace("*","")
             reply = QMessageBox.question(self, 'Unsaved Changes',
                                          f"'{filename}' has unsaved changes.\nDo you want to save before closing?",
                                          QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                          QMessageBox.StandardButton.Cancel)

             if reply == QMessageBox.StandardButton.Save:
                 # --- Call the new save method ---
                 success = self.save_current_tab_as(index) # Pass index to save specific tab
                 if not success:
                     return # Don't close if save fails/cancelled
             elif reply == QMessageBox.StandardButton.Cancel:
                 return # Don't close
             # else: Discard, proceed to close

        # Proceed with closing
        tab_text = self.tabs.tabText(index)
        print(f"Closing tab: {tab_text}")
        widget_to_close.close_document()
        self.tabs.removeTab(index)


    # update_ui_for_current_tab remains the same
    def update_ui_for_current_tab(self, index=-1):
        current_widget = self.get_current_view_widget()
        if current_widget and isinstance(current_widget, PDFViewWidget) and current_widget.doc:
            page, total = current_widget.get_current_page_info()
            current_page_display = max(0, page) + 1 if total > 0 else 0
            self.page_label.setText(f"Page: {current_page_display} / {total}")
            self.zoom_spinbox.blockSignals(True)
            self.zoom_spinbox.setValue(int(current_widget.zoom_factor * 100))
            self.zoom_spinbox.blockSignals(False)
        else:
            self.page_label.setText("Page: - / -")
            self.zoom_spinbox.blockSignals(True)
            self.zoom_spinbox.setValue(100)
            self.zoom_spinbox.blockSignals(False)
        self.update_button_states()

    # update_button_states remains the same (uses the corrected logic)
    def update_button_states(self):
        current_widget = self.get_current_view_widget()
        has_valid_widget_check = current_widget and isinstance(current_widget, PDFViewWidget) and current_widget.doc
        is_widget_valid_bool = bool(has_valid_widget_check)

        if is_widget_valid_bool:
            page, total = current_widget.get_current_page_info()
            valid_page_index = 0 <= page < total
            can_go_prev = valid_page_index and page > 0
            can_go_next = valid_page_index and page < total - 1
            can_delete = total > 1 # Can delete if document exists and has > 1 page
            is_modified = current_widget.is_document_modified()
        else:
            can_go_prev = False
            can_go_next = False
            can_delete = False # Cannot delete if no valid doc
            is_modified = False

        # Enable based on flags
        self.btn_save_as.setEnabled(is_widget_valid_bool and is_modified)
        self.btn_delete_page.setEnabled(is_widget_valid_bool and can_delete)
        self.btn_prev.setEnabled(is_widget_valid_bool and can_go_prev)
        self.btn_next.setEnabled(is_widget_valid_bool and can_go_next)
        self.zoom_spinbox.setEnabled(is_widget_valid_bool)

    # --- Implement New Toolbar Action Handlers ---

# Inside PDFViewer class

    def save_current_tab_as(self, checked=None, *, index=None): # Accept 'checked' argument but ignore it, force 'index' as keyword if used
        """Saves the document in the specified tab index, or the current tab if index is None/invalid."""
        widget_to_save = None

        # Prioritize explicitly passed valid index (e.g., from close_tab)
        if index is not None and 0 <= index < self.tabs.count():
            print(f"\nDEBUG save_current_tab_as: Getting widget at specified index={index}...")
            widget_to_save = self.tabs.widget(index)
            if widget_to_save and isinstance(widget_to_save, PDFViewWidget):
                 print(f"DEBUG save_current_tab_as: Widget at index {index} filepath = {widget_to_save.get_filepath()}")
                 print(f"DEBUG save_current_tab_as: Widget at index {index} object ID = {id(widget_to_save)}")
            else:
                 print(f"DEBUG save_current_tab_as: No valid PDFViewWidget found at index {index}!")
                 widget_to_save = None # Ensure it's None if not valid

        # If no valid index was passed, default to the currently selected tab
        if widget_to_save is None:
            print(f"\nDEBUG save_current_tab_as: Getting CURRENT widget (index was None or invalid)...")
            widget_to_save = self.get_current_view_widget()
            if widget_to_save and isinstance(widget_to_save, PDFViewWidget):
                 print(f"DEBUG save_current_tab_as: Current widget filepath = {widget_to_save.get_filepath()}")
                 print(f"DEBUG save_current_tab_as: Current widget object ID = {id(widget_to_save)}")
            else:
                 print(f"DEBUG save_current_tab_as: No valid current PDFViewWidget found!")
                 widget_to_save = None # Ensure it's None

        # Proceed only if we successfully identified a valid widget
        if widget_to_save and isinstance(widget_to_save, PDFViewWidget):
            suggested_dir = "" # Keep suggestion simple for now
            # Suggest directory logic can be added here if needed

            print(f"DEBUG save_current_tab_as: Calling save_as on widget with ID {id(widget_to_save)} associated with path '{widget_to_save.get_filepath()}'")
            success = widget_to_save.save_as(suggested_dir) # Call the widget's save method

            if success:
                # Update button states if the *currently visible* tab was the one saved
                if widget_to_save is self.get_current_view_widget():
                    self.update_button_states()
            return success
        else:
            # Show error only if the action was triggered when it shouldn't have been
            # (Button should be disabled if no valid widget, but check anyway)
            print("Save Error: No valid document selected/found to save.")
            # Avoid showing message box if simply no tab was active
            # show_message(self, "Save Error", "No valid document selected to save.", QMessageBox.Icon.Warning)
            return False

    def delete_current_tab_page(self):
        """Deletes the current page in the active tab."""
        current_widget = self.get_current_view_widget()
        if current_widget and isinstance(current_widget, PDFViewWidget):
            success = current_widget.delete_page()
            if success:
                # Update page label and button states
                self.update_ui_for_current_tab()
        else:
             show_message(self, "Delete Error", "No document selected to delete pages from.", QMessageBox.Icon.Warning)

    def create_new_assembly_tab(self):
        """Creates a new tab holding an empty assembly document."""
        self.assembly_tab_count += 1
        assembly_name = f"Untitled Assembly {self.assembly_tab_count}"

        # Check if an assembly tab with this default name already exists? Unlikely but possible.
        # for i in range(self.tabs.count()): ...

        assembly_widget = PDFViewWidget(is_assembly=True)
        assembly_widget.setup_assembly_doc(assembly_name) # Pass the name

        index = self.tabs.addTab(assembly_widget, assembly_name + "*") # Mark as unsaved
        self.tabs.setTabToolTip(index, f"Assembly Document: {assembly_name} (Unsaved)")
        self.tabs.setCurrentIndex(index)
        print(f"Created new assembly tab: {assembly_name}")
        # UI should update via signal/slot


    # next_page, prev_page, apply_zoom remain the same (delegating)
    def next_page(self):
        widget = self.get_current_view_widget()
        if widget and isinstance(widget, PDFViewWidget) and widget.next_page():
             self.update_ui_for_current_tab()

    def prev_page(self):
        widget = self.get_current_view_widget()
        if widget and isinstance(widget, PDFViewWidget) and widget.prev_page():
             self.update_ui_for_current_tab()



    def apply_zoom(self):
        widget = self.get_current_view_widget()
        if widget and isinstance(widget, PDFViewWidget):
             factor = self.zoom_spinbox.value() / 100.0
             widget.apply_zoom(factor)

    # closeEvent remains the same
    def closeEvent(self, event):
        modified_tabs_indices = []
        modified_tabs_names = []
        for i in range(self.tabs.count()):
             widget = self.tabs.widget(i)
             if isinstance(widget, PDFViewWidget) and widget.is_document_modified():
                 modified_tabs_indices.append(i)
                 # Use tooltip for potentially saved assembly docs, otherwise tab text
                 tab_name = self.tabs.tabToolTip(i) if widget.is_assembly_target() and not widget.get_filepath().startswith(ASSEMBLY_PREFIX+"Untitled") else self.tabs.tabText(i).replace("*","")
                 modified_tabs_names.append(os.path.basename(tab_name))


        if modified_tabs_names:
             filenames = "\n - ".join(modified_tabs_names)
             reply = QMessageBox.question(self, 'Unsaved Changes',
                                          f"The following documents have unsaved changes:\n - {filenames}\n\nQuit without saving?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, # Quit? Yes / No
                                          QMessageBox.StandardButton.No) # Default to No (don't quit)

             if reply == QMessageBox.StandardButton.No:
                  event.ignore()
                  if modified_tabs_indices:
                       self.tabs.setCurrentIndex(modified_tabs_indices[0])
                  return

        print("Closing application...")
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, PDFViewWidget):
                widget.close_document()

        event.accept()

# --- Application Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = PDFViewer()
    viewer.show()
    sys.exit(app.exec())