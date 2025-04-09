# freebird/ui/main_window.py

import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QHBoxLayout, QSpinBox, QSizePolicy,
    QTabWidget, QMessageBox, QProgressDialog, QLineEdit
)
from PyQt6.QtGui import (
    QPixmap, QIcon, QAction, QKeySequence, QPainter,
    QIntValidator
)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, QTimer

# Import from other modules in the new structure
from freebird.ui.pdf_view import PDFViewWidget
from freebird.ui.search_panel import SearchPanel
from freebird.ui.about_dialog import AboutDialog
from freebird.utils.thumbnail import ThumbnailViewDialog
from freebird.utils.helpers import show_message
from freebird.constants import BACKGROUND_IMAGE_PATH, ICON_PATH, VERSION, ASSEMBLY_PREFIX

class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.assembly_tab_count = 0
        self.background_pixmap = None
        self.search_panel = None
        
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
            # Load window icon
            if os.path.exists(ICON_PATH):
                self.setWindowIcon(QIcon(ICON_PATH))
                print(f"INFO: Icon file loaded.")
            else:
                print(f"INFO: Icon file not found.")
                
            # Load background image
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                self.background_pixmap = QPixmap(BACKGROUND_IMAGE_PATH)
                if self.background_pixmap.isNull():
                    print(f"WARNING: Failed to load background image.")
                    self.background_pixmap = None
                else:
                    print(f"INFO: Background image loaded.")
            else:
                print(f"INFO: Background image not found.")
        except Exception as e:
            print(f"WARNING: Could not load resources: {e}")
            self.background_pixmap = None

    def init_ui(self):
        self.setWindowTitle(f"FreeBird PDF v{VERSION}")
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

        # Search panel (initially hidden)
        self.search_panel = SearchPanel(self)
        self.search_panel.hide()
        container_layout.addWidget(self.search_panel)

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
        
        self.btn_save = QPushButton("Save")
        self.btn_save.setToolTip("Save document (Ctrl+S)")
        self.btn_save.clicked.connect(self.save_current_document)
        layout.addWidget(self.btn_save)
        
        self.btn_save_as = QPushButton("Save As...")
        self.btn_save_as.setToolTip("Save document as (Ctrl+Shift+S)")
        self.btn_save_as.clicked.connect(self.save_current_tab_as)
        layout.addWidget(self.btn_save_as)
        
        layout.addStretch(1)
        
        # Search button
        self.btn_search = QPushButton("Search")
        self.btn_search.setToolTip("Search text (Ctrl+F)")
        self.btn_search.clicked.connect(self.toggle_search_panel)
        layout.addWidget(self.btn_search)
        
        # Page manipulation
        self.btn_delete_page = QPushButton("Delete Page")
        self.btn_delete_page.setToolTip("Delete current page")
        self.btn_delete_page.clicked.connect(self.delete_current_tab_page)
        layout.addWidget(self.btn_delete_page)
        
        # Add new reorder button
        self.btn_reorder_pages = QPushButton("Reorder Pages")
        self.btn_reorder_pages.setToolTip("Reorder pages in document")
        self.btn_reorder_pages.clicked.connect(self.show_reorder_dialog)
        layout.addWidget(self.btn_reorder_pages)
        
        layout.addStretch(1)
        
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
        
        # About button (new)
        layout.addStretch(1)
        btn_about = QPushButton("About")
        btn_about.setToolTip("About FreeBird PDF")
        btn_about.clicked.connect(self.show_about_dialog)
        layout.addWidget(btn_about)

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
        
        # Search shortcut (Ctrl+F)
        self.search_action = QAction("Search", self)
        self.search_action.setShortcut(QKeySequence.StandardKey.Find)
        self.search_action.triggered.connect(self.toggle_search_panel)
        self.addAction(self.search_action)
        
        # Find next (F3)
        self.find_next_action = QAction("Find Next", self)
        self.find_next_action.setShortcut(QKeySequence(Qt.Key.Key_F3))
        self.find_next_action.triggered.connect(self.find_next)
        self.addAction(self.find_next_action)
        
        # Find previous (Shift+F3)
        self.find_prev_action = QAction("Find Previous", self)
        self.find_prev_action.setShortcut(QKeySequence(Qt.KeyboardModifier.ShiftModifier | Qt.Key.Key_F3))
        self.find_prev_action.triggered.connect(self.find_previous)
        self.addAction(self.find_prev_action)
        
        # Page reordering shortcuts
        self.page_up_action = QAction("Move Page Up", self)
        self.page_up_action.setShortcut(QKeySequence("Ctrl+Shift+Up"))
        self.page_up_action.triggered.connect(self.move_current_page_up)
        self.addAction(self.page_up_action)
        
        self.page_down_action = QAction("Move Page Down", self)
        self.page_down_action.setShortcut(QKeySequence("Ctrl+Shift+Down"))
        self.page_down_action.triggered.connect(self.move_current_page_down)
        self.addAction(self.page_down_action)
        
        # Save shortcut (Ctrl+S)
        self.save_action = QAction("Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_current_document)
        self.addAction(self.save_action)
        
        # Save As shortcut (Ctrl+Shift+S)
        self.save_as_action = QAction("Save As...", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self.save_current_tab_as)
        self.addAction(self.save_as_action)

    def get_current_view_widget(self):
        """Gets the PDFViewWidget from the currently active tab."""
        return self.tabs.currentWidget()

    def toggle_search_panel(self):
        """Toggle the search panel visibility."""
        if not self.search_panel.isVisible():
            # Only show if we have a valid PDF document
            current_widget = self.get_current_view_widget()
            if current_widget and isinstance(current_widget, PDFViewWidget) and current_widget.doc:
                self.search_panel.show_panel()
        else:
            self.search_panel.hide()
            
    def find_next(self):
        """Find next search result."""
        if self.search_panel.isVisible():
            self.search_panel.on_next()
        else:
            # Show search panel if it's not visible
            self.toggle_search_panel()
            
    def find_previous(self):
        """Find previous search result."""
        if self.search_panel.isVisible():
            self.search_panel.on_previous()
        else:
            # Show search panel if it's not visible
            self.toggle_search_panel()

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
        
        # Hide search panel if no tabs
        if self.tabs.count() == 0 and self.search_panel.isVisible():
            self.search_panel.hide()
        
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
            
            # Enable search button
            self.btn_search.setEnabled(True)
            
            # Update search panel if visible
            if self.search_panel.isVisible():
                search_results = current_widget.get_search_results()
                if search_results.has_results():
                    self.search_panel.search_input.setText(search_results.query)
                    self.search_panel.update_ui_state(True)
                    self.search_panel.status_label.setText(f"{search_results.get_current_match_info()}")
                else:
                    # Clear search panel
                    self.search_panel.search_input.clear()
                    self.search_panel.update_ui_state(False)
                    self.search_panel.status_label.setText("")
        else:
            # No document loaded
            self.page_label.setText("Page: - / -")
            self.zoom_spinbox.blockSignals(True)
            self.zoom_spinbox.setValue(100)
            self.zoom_spinbox.blockSignals(False)
            self.goto_page_input.clear()
            
            # Disable search button
            self.btn_search.setEnabled(False)
            
            # Hide search panel if visible
            if self.search_panel.isVisible():
                self.search_panel.hide()
            
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
            can_reorder = total > 1
            is_modified = current_widget.is_document_modified()
            can_goto = total > 0
            has_path = current_widget.get_filepath() and not current_widget.get_filepath().startswith(ASSEMBLY_PREFIX)
        else:
            can_go_prev = False
            can_go_next = False
            can_delete = False
            can_reorder = False
            is_modified = False
            can_goto = False
            has_path = False
        
        # CRITICAL: Check if each button exists before setting its state
        if hasattr(self, 'btn_save') and self.btn_save is not None:
            self.btn_save.setEnabled(is_widget_valid_bool and is_modified)
            
        if hasattr(self, 'btn_save_as') and self.btn_save_as is not None:
            self.btn_save_as.setEnabled(is_widget_valid_bool)
        
        if hasattr(self, 'btn_delete_page') and self.btn_delete_page is not None:
            self.btn_delete_page.setEnabled(is_widget_valid_bool and can_delete)
        
        if hasattr(self, 'btn_reorder_pages') and self.btn_reorder_pages is not None:
            self.btn_reorder_pages.setEnabled(is_widget_valid_bool and can_reorder)
            
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
            
        if hasattr(self, 'btn_search') and self.btn_search is not None:
            self.btn_search.setEnabled(is_widget_valid_bool)
            
        # If we have a sign button (for signatures), update it too
        if hasattr(self, 'btn_sign') and self.btn_sign is not None:
            self.btn_sign.setEnabled(is_widget_valid_bool)

    def show_about_dialog(self):
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

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
            
    def save_current_document(self):
        """Save the current document (if it has been modified and has a path)."""
        current_widget = self.get_current_view_widget()
        if not current_widget or not isinstance(current_widget, PDFViewWidget):
            return
            
        # If the document is modified and has a path (not an assembly doc), save it directly
        if current_widget.is_document_modified():
            if current_widget.get_filepath() and not current_widget.get_filepath().startswith(ASSEMBLY_PREFIX):
                try:
                    # Save to the existing path
                    current_widget.doc.save(current_widget.get_filepath(), garbage=4, deflate=True)
                    current_widget.mark_modified(False)
                    print(f"Saved document to {current_widget.get_filepath()}")
                    return True
                except Exception as e:
                    print(f"ERROR: Could not save file: {e}")
                    show_message(self, "Save Error", f"Could not save file: {e}", QMessageBox.Icon.Critical)
                    return False
            else:
                # If it's an assembly doc or doesn't have a path, use Save As
                return self.save_current_tab_as()
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

    def show_reorder_dialog(self):
        """Show the thumbnail view dialog for reordering pages."""
        current_widget = self.get_current_view_widget()
        if current_widget and isinstance(current_widget, PDFViewWidget) and current_widget.doc:
            if current_widget.total_pages <= 1:
                show_message(self, "Cannot Reorder", 
                           "Document must have more than one page for reordering.",
                           QMessageBox.Icon.Information)
                return
                
            # Create and show the dialog
            dialog = ThumbnailViewDialog(self, current_widget)
            dialog.exec()
            
            # After dialog closes, update UI
            self.update_ui_for_current_tab()

    def move_current_page_up(self):
        """Move current page up in the document order."""
        current_widget = self.get_current_view_widget()
        if current_widget and isinstance(current_widget, PDFViewWidget):
            current_widget.move_current_page_up()
            
    def move_current_page_down(self):
        """Move current page down in the document order."""
        current_widget = self.get_current_view_widget()
        if current_widget and isinstance(current_widget, PDFViewWidget):
            current_widget.move_current_page_down()

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