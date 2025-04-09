# These imports need to be fixed at the beginning of the file
import sys
import fitz  # PyMuPDF
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QScrollArea, QMessageBox, QHBoxLayout, QSpinBox, QSizePolicy,
    QTabWidget, QMenu, QLineEdit, QFrame, QCheckBox, QDialog, QListWidget,
    QListWidgetItem, QProgressDialog
)
from PyQt6.QtGui import (
    QPixmap, QImage, QIcon, QPainter, QAction, QKeySequence,
    QIntValidator, QColor, QPen, QDrag, QFont  # Add QFont here
)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, QTimer, QMimeData  # QMimeData moved here

# --- Constants ---
ASSEMBLY_PREFIX = "assembly:/"
BACKGROUND_IMAGE_FILENAME = "FreeBird.png"
ICON_FILENAME = "pdf_icon.png"
VERSION = "0.2.0 - Second Flight"  # New version constant

# --- Helper function ---
def show_message(parent, title, message, icon=QMessageBox.Icon.Information):
    msg_box = QMessageBox(parent)
    msg_box.setIcon(icon)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()

# ============================================================
#  SearchResult: Class to store search results
# ============================================================
class SearchResult:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.query = ""
        self.results = {}  # {page_index: [rect1, rect2, ...]}
        self.total_matches = 0
        self.current_page = -1
        self.current_match = -1
    
    def add_matches(self, page_index, rects):
        if rects:
            self.results[page_index] = rects
            self.total_matches += len(rects)
    
    def has_results(self):
        return self.total_matches > 0
    
    def get_match_count(self):
        return self.total_matches
    
    def get_current_match_index(self):
        """Returns the 0-based index of the current match across all pages."""
        if not self.has_results() or self.current_match < 0 or self.current_page < 0:
            return -1
        
        count = 0
        pages = sorted(self.results.keys())
        
        for page in pages:
            if page < self.current_page:
                count += len(self.results[page])
            elif page == self.current_page:
                count += self.current_match
                break
        
        return count
    
    def get_current_match_info(self):
        if self.has_results() and self.current_match >= 0:
            # Add 1 to make it 1-based indexing for display
            return f"Match {self.get_current_match_index() + 1} of {self.total_matches}"
        return ""
    
    def navigate_to_match(self, forward=True):
        if not self.has_results():
            return None, -1
        
        pages = sorted(self.results.keys())
        if not pages:
            return None, -1
        
        # First search or reset
        if self.current_page < 0 or self.current_match < 0:
            self.current_page = pages[0]
            self.current_match = 0
            return self.current_page, self.results[self.current_page][self.current_match]
        
        # Navigate forward
        if forward:
            # Move to next match on current page
            if self.current_match + 1 < len(self.results[self.current_page]):
                self.current_match += 1
            else:
                # Move to next page
                current_page_index = pages.index(self.current_page)
                if current_page_index + 1 < len(pages):
                    self.current_page = pages[current_page_index + 1]
                    self.current_match = 0
                else:
                    # Wrap around to first result
                    self.current_page = pages[0]
                    self.current_match = 0
        # Navigate backward
        else:
            # Move to previous match on current page
            if self.current_match > 0:
                self.current_match -= 1
            else:
                # Move to previous page
                current_page_index = pages.index(self.current_page)
                if current_page_index > 0:
                    self.current_page = pages[current_page_index - 1]
                    self.current_match = len(self.results[self.current_page]) - 1
                else:
                    # Wrap around to last result
                    self.current_page = pages[-1]
                    self.current_match = len(self.results[self.current_page]) - 1
        
        return self.current_page, self.results[self.current_page][self.current_match]

# ============================================================
#  ThumbnailViewDialog: Dialog for visual page reordering
# ============================================================
class ThumbnailViewDialog(QDialog):
    """Dialog showing thumbnails of all pages for visual reordering."""
    
    def __init__(self, parent, pdf_widget):
        super().__init__(parent)
        self.pdf_widget = pdf_widget
        self.doc = pdf_widget.get_document()
        self.thumbnails = []
        self.drag_start_position = None
        self.drag_item = None
        self.drop_indicator_index = -1
        self.dragging = False
        
        self.setWindowTitle("Reorder Pages")
        self.setMinimumSize(800, 600)
        
        self.init_ui()
        self.load_thumbnails()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Instructions
        instruction_label = QLabel("Drag and drop thumbnails to reorder pages. Double-click a thumbnail to view the page.")
        layout.addWidget(instruction_label)
        
        # Create a custom list widget with enhanced drag-drop visual feedback
        class EnhancedListWidget(QListWidget):
            def __init__(self, parent):
                super().__init__()
                self.dialog = parent
                self.setViewMode(QListWidget.ViewMode.IconMode)
                self.setIconSize(QSize(120, 160))
                self.setResizeMode(QListWidget.ResizeMode.Adjust)
                self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
                self.setAcceptDrops(True)
                self.setDragEnabled(True)
                self.setSpacing(10)
                self.setGridSize(QSize(150, 210))
                self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
                self.viewport().setAcceptDrops(True)
                
                # Style for drop indicator
                self.setStyleSheet("""
                    QListWidget::item:selected { 
                        background: #d0e0ff; 
                        border: 2px solid #3080ff;
                    }
                    QListWidget::item:hover { 
                        background: #e0f0ff; 
                    }
                """)
            
            def dragEnterEvent(self, event):
                if event.source() == self:
                    event.accept()
                    self.dialog.dragging = True
                else:
                    event.ignore()
            
            def dragMoveEvent(self, event):
                if event.source() == self:
                    pos = event.position().toPoint()
                    index = self.indexAt(pos)
                    
                    # If over a valid item, prepare to show drop indicator
                    if index.isValid():
                        self.dialog.drop_indicator_index = index.row()
                    else:
                        # If not over a valid item, find nearest column
                        item_count = self.count()
                        if item_count > 0:
                            # Handle drop at the end of the list
                            rect = self.visualItemRect(self.item(item_count - 1))
                            if pos.x() > rect.right():
                                self.dialog.drop_indicator_index = item_count
                    
                    self.viewport().update()
                    event.accept()
                else:
                    event.ignore()
            
            def dropEvent(self, event):
                if event.source() == self:
                    # Handle drop - we'll do our own moving of items
                    pos = event.position().toPoint()
                    drop_index = self.indexAt(pos).row()
                    
                    # If we're dropping at an invalid position (like outside items)
                    # find the nearest valid position
                    if drop_index < 0:
                        # Find if we're dropping at the end
                        if self.dialog.drop_indicator_index >= self.count():
                            drop_index = self.count() - 1
                        else:
                            # Try to find closest item
                            closest_dist = float('inf')
                            for i in range(self.count()):
                                rect = self.visualItemRect(self.item(i))
                                center = rect.center()
                                dist = (center.x() - pos.x())**2 + (center.y() - pos.y())**2
                                if dist < closest_dist:
                                    closest_dist = dist
                                    drop_index = i
                    
                    # Get the source item
                    source_items = self.selectedItems()
                    if not source_items:
                        event.ignore()
                        return
                        
                    source_item = source_items[0]
                    source_index = self.row(source_item)
                    
                    # Don't move to same position
                    if source_index == drop_index:
                        event.ignore()
                        return
                    
                    # Handle case where we're dropping beyond the last item
                    if drop_index < 0:
                        drop_index = self.count() - 1
                    
                    # Take item from old position
                    item = self.takeItem(source_index)
                    
                    # Insert it at new position, adjusting for position change
                    if source_index < drop_index:
                        self.insertItem(drop_index, item)
                    else:
                        self.insertItem(drop_index, item)
                    
                    # Select the moved item
                    self.setCurrentItem(item)
                    
                    # Enable apply button
                    self.dialog.apply_button.setEnabled(True)
                    
                    # Reset state
                    self.dialog.drop_indicator_index = -1
                    self.dialog.dragging = False
                    self.viewport().update()
                    
                    event.accept()
                else:
                    event.ignore()
            
            def dragLeaveEvent(self, event):
                self.dialog.drop_indicator_index = -1
                self.dialog.dragging = False
                self.viewport().update()
                super().dragLeaveEvent(event)
            
            def paintEvent(self, event):
                super().paintEvent(event)
                
                # Draw drop indicator if we're dragging
                if self.dialog.dragging and self.dialog.drop_indicator_index >= 0:
                    painter = QPainter(self.viewport())
                    pen = QPen(QColor(30, 144, 255))  # Dodger blue
                    pen.setWidth(3)
                    painter.setPen(pen)
                    
                    # Draw indicator line
                    if self.dialog.drop_indicator_index < self.count():
                        rect = self.visualItemRect(self.item(self.dialog.drop_indicator_index))
                        # Draw a line on the left side of the item
                        painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())
                    else:
                        # We're dropping at the end - draw after last item
                        if self.count() > 0:
                            rect = self.visualItemRect(self.item(self.count() - 1))
                            # Draw a line on the right side of the last item
                            painter.drawLine(rect.right() + 5, rect.top(), 
                                           rect.right() + 5, rect.bottom())
                    
                    painter.end()
        
        # Thumbnail list widget
        self.list_widget = EnhancedListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self.on_thumbnail_double_clicked)
        layout.addWidget(self.list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.apply_changes)
        self.apply_button.setEnabled(False)  # Initially disabled until changes are made
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.apply_button)
        layout.addLayout(button_layout)
    
    def load_thumbnails(self):
        """Load thumbnails for all pages."""
        if not self.doc:
            return
            
        self.list_widget.clear()
        self.thumbnails.clear()
        
        # Use a progress dialog for many pages
        if self.pdf_widget.total_pages > 10:
            progress = QProgressDialog("Loading thumbnails...", "Cancel", 0, self.pdf_widget.total_pages, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            
        for i in range(self.pdf_widget.total_pages):
            if self.pdf_widget.total_pages > 10:
                progress.setValue(i)
                if progress.wasCanceled():
                    break
            
            # Render a thumbnail
            page = self.doc.load_page(i)
            matrix = fitz.Matrix(0.2, 0.2)  # Scale down for thumbnail
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            # Convert to QImage and QPixmap
            qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage)
            
            # Create item
            item = QListWidgetItem()
            item.setIcon(QIcon(pixmap))
            item.setText(f"Page {i+1}")
            item.setData(Qt.ItemDataRole.UserRole, i)  # Store page index
            
            self.list_widget.addItem(item)
            self.thumbnails.append(pixmap)
        
        if self.pdf_widget.total_pages > 10:
            progress.setValue(self.pdf_widget.total_pages)
    
    def on_thumbnail_double_clicked(self, item):
        """Handler for double-clicking a thumbnail."""
        page_index = item.data(Qt.ItemDataRole.UserRole)
        # Preview the page or jump to it
        self.pdf_widget.goto_page(page_index)
    
    def apply_changes(self):
        """Apply the reordering changes to the document in memory (without saving to disk)."""
        # Check if any reordering happened
        new_order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            original_page_index = item.data(Qt.ItemDataRole.UserRole)
            new_order.append(original_page_index)
        
        # Skip if order hasn't changed
        if new_order == list(range(len(new_order))):
            self.accept()
            return
        
        # Apply the new order
        try:
            # Create a copy of the document with pages in the new order
            new_doc = fitz.open()
            
            for new_index, old_index in enumerate(new_order):
                new_doc.insert_pdf(self.doc, from_page=old_index, to_page=old_index)
            
            # Close current document and replace the document object (without saving to disk)
            current_path = self.pdf_widget.get_filepath()
            current_page = self.pdf_widget.current_page
            self.pdf_widget.doc.close()
            self.pdf_widget.doc = new_doc
            
            # Update document properties
            self.pdf_widget.total_pages = len(new_doc)
            self.pdf_widget.current_page = min(current_page, self.pdf_widget.total_pages - 1)
            
            # Clear cache to ensure updated rendering
            self.pdf_widget.pixmap_cache = {}
            
            # Mark as modified but don't save to disk
            self.pdf_widget.mark_modified(True)
            
            # Refresh the display
            self.pdf_widget.display_page()
            
            self.accept()
            
        except Exception as e:
            print(f"ERROR: Failed to reorder pages: {e}")
            show_message(self, "Error", f"Failed to reorder pages: {e}", QMessageBox.Icon.Critical)

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
        
        # Search-related attributes
        self.search_results = SearchResult()
        self.highlight_rects = []
        self.current_highlight_rect = None
        
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
        self.search_results.reset()
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
            self.search_results.reset()
            
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
                    
                    # Draw search highlights if needed
                    if self.current_page in self.search_results.results:
                        self.highlight_rects = self.search_results.results[self.current_page]
                        
                        # Create a painter to draw on the pixmap
                        painter = QPainter(pixmap)
                        
                        # Draw all search highlights
                        for i, rect in enumerate(self.highlight_rects):
                            # Scaled rectangle based on zoom
                            qrect = QRect(
                                int(rect.x0 * self.zoom_factor),
                                int(rect.y0 * self.zoom_factor),
                                int((rect.x1 - rect.x0) * self.zoom_factor),
                                int((rect.y1 - rect.y0) * self.zoom_factor)
                            )
                            
                            # Check if this is the current highlight
                            is_current = (self.current_page == self.search_results.current_page and 
                                         i == self.search_results.current_match)
                            
                            # Use different colors for current vs other matches
                            if is_current:
                                highlight_color = QColor(255, 165, 0, 100)  # Orange highlight for current match
                                border_color = QColor(255, 69, 0)  # Red-orange border
                                painter.setPen(QPen(border_color, 2))
                            else:
                                highlight_color = QColor(255, 255, 0, 100)  # Yellow for other matches
                                painter.setPen(Qt.PenStyle.NoPen)
                            
                            painter.setBrush(highlight_color)
                            painter.drawRect(qrect)
                        
                        painter.end()
                    
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

    def search_text(self, query, case_sensitive=False, whole_words=False):
        """Search for text in the document."""
        if not self.doc or not query:
            return False
        
        # Reset search results
        self.search_results.reset()
        self.search_results.query = query
        self.pixmap_cache = {}  # Clear cache to redraw with highlights
        
        # PyMuPDF search flags
        # In PyMuPDF/Fitz, these are the commonly used constants:
        # 0 = Default (case-sensitive)
        # 1 = Ignore case
        # 2 = Whole words
        # 3 = Ignore case + Whole words
        
        # Start with default flags
        search_flags = 0
        
        # Apply flags based on settings
        if not case_sensitive:
            search_flags |= 1  # TEXT_SEARCH_IGNORE_CASE value
            
        if whole_words:
            search_flags |= 2  # TEXT_SEARCH_WHOLE_WORDS value
        
        try:
            # Search all pages
            for page_idx in range(self.total_pages):
                page = self.doc.load_page(page_idx)
                matches = page.search_for(query, flags=search_flags)
                if matches:
                    self.search_results.add_matches(page_idx, matches)
            
            # If we found results, navigate to the first match
            if self.search_results.has_results():
                page_idx, rect = self.search_results.navigate_to_match(forward=True)
                if page_idx >= 0:
                    self.goto_page(page_idx)
                return True
            else:
                # Redraw current page without highlights
                self.display_page()
                return False
        except Exception as e:
            print(f"ERROR: Search failed: {e}")
            return False

    def find_next(self, forward=True):
        """Find the next or previous search result."""
        if not self.search_results.has_results():
            return False
        
        try:
            page_idx, _ = self.search_results.navigate_to_match(forward)
            if page_idx >= 0:
                # Go to the page if it's different from current
                if page_idx != self.current_page:
                    self.goto_page(page_idx)
                else:
                    # Just redraw the current page to update highlights
                    self.pixmap_cache = {}  # Clear cache to redraw with highlights
                    self.display_page()
                return True
            return False
        except Exception as e:
            print(f"ERROR: Navigation failed: {e}")
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

    def get_search_results(self):
        return self.search_results

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

    def move_current_page_up(self):
        """Moves the current page up one position (earlier in the document)."""
        if not self.doc or self.current_page <= 0:
            return False
            
        try:
            # Store the page index we're moving
            page_to_move = self.current_page
            target_position = page_to_move - 1
            
            # We need to use a temporary document to reorder pages
            # because sometimes direct move_page doesn't work reliably
            temp_doc = fitz.open()
            
            # First, copy all pages up to the target position
            for i in range(target_position):
                if i != page_to_move:  # Skip the page we're moving
                    temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                    
            # Now insert the page we're moving
            temp_doc.insert_pdf(self.doc, from_page=page_to_move, to_page=page_to_move)
            
            # Then copy all remaining pages
            for i in range(target_position, self.total_pages):
                if i != page_to_move:  # Skip the page we already moved
                    temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
            
            # Close the current document and replace with our reordered one
            self.doc.close()
            self.doc = temp_doc
            
            # Update total pages count
            self.total_pages = len(self.doc)
            
            # Mark as modified
            self.mark_modified(True)
            
            # Clear cache to ensure updated rendering
            self.pixmap_cache = {}
            
            # Adjust current page index to follow the moved page
            self.current_page = target_position
            
            # Refresh display
            self.display_page()
            print(f"Successfully moved page {page_to_move+1} to position {target_position+1}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to move page up: {e}")
            show_message(self, "Error", f"Failed to move page: {e}", QMessageBox.Icon.Critical)
            return False

    def move_current_page_down(self):
        """Moves the current page down one position (later in the document)."""
        if not self.doc or self.current_page >= self.total_pages - 1:
            return False
            
        try:
            # Store the page index we're moving
            page_to_move = self.current_page
            target_position = page_to_move + 1
            
            # We need to use a temporary document to reorder pages
            # because sometimes direct move_page doesn't work reliably
            temp_doc = fitz.open()
            
            # First, copy all pages up to the page we're moving
            for i in range(page_to_move):
                temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                
            # Next, copy the page that was after our target (which will now come before)
            temp_doc.insert_pdf(self.doc, from_page=target_position, to_page=target_position)
            
            # Now insert the page we're moving
            temp_doc.insert_pdf(self.doc, from_page=page_to_move, to_page=page_to_move)
            
            # Then copy all remaining pages
            for i in range(target_position+1, self.total_pages):
                temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
            
            # Close the current document and replace with our reordered one
            self.doc.close()
            self.doc = temp_doc
            
            # Update total pages count
            self.total_pages = len(self.doc)
            
            # Mark as modified
            self.mark_modified(True)
            
            # Clear cache to ensure updated rendering
            self.pixmap_cache = {}
            
            # Adjust current page index to follow the moved page
            self.current_page = target_position
            
            # Refresh display
            self.display_page()
            print(f"Successfully moved page {page_to_move+1} to position {target_position+1}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to move page down: {e}")
            show_message(self, "Error", f"Failed to move page: {e}", QMessageBox.Icon.Critical)
            return False

    def move_page_to(self, from_index, to_index):
        """Moves a page from one position to another in the document."""
        if not self.doc or not (0 <= from_index < self.total_pages) or not (0 <= to_index < self.total_pages):
            return False
            
        # Skip if no actual move is happening
        if from_index == to_index:
            return True
            
        try:
            # Create a new document with pages in the desired order
            temp_doc = fitz.open()
            
            # Moving earlier page to later position
            if from_index < to_index:
                # Copy pages before the source page
                for i in range(from_index):
                    temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                    
                # Copy pages between source and destination (they shift up by one)
                for i in range(from_index + 1, to_index + 1):
                    temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                    
                # Insert the source page at the destination
                temp_doc.insert_pdf(self.doc, from_page=from_index, to_page=from_index)
                
                # Copy any remaining pages
                for i in range(to_index + 1, self.total_pages):
                    temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
            
            # Moving later page to earlier position
            else:  # from_index > to_index
                # Copy pages before the destination
                for i in range(to_index):
                    temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                    
                # Insert the source page at the destination
                temp_doc.insert_pdf(self.doc, from_page=from_index, to_page=from_index)
                
                # Copy pages between destination and source (they shift down by one)
                for i in range(to_index, from_index):
                    temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                    
                # Copy any remaining pages
                for i in range(from_index + 1, self.total_pages):
                    temp_doc.insert_pdf(self.doc, from_page=i, to_page=i)
            
            # Replace the current document with our reordered one
            self.doc.close()
            self.doc = temp_doc
            
            # Update total pages count
            self.total_pages = len(self.doc)
            
            # Mark as modified
            self.mark_modified(True)
            
            # Clear cache to ensure updated rendering
            self.pixmap_cache = {}
            
            # Update current page index to follow the moved page
            if self.current_page == from_index:
                self.current_page = to_index
            
            # Refresh display
            self.display_page()
            print(f"Successfully moved page {from_index+1} to position {to_index+1}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to move page from {from_index} to {to_index}: {e}")
            show_message(self, "Error", f"Failed to move page: {e}", QMessageBox.Icon.Critical)
            return False

    def show_move_page_dialog(self):
        """Shows a dialog to move a page to a specific position."""
        if not self.doc or self.total_pages <= 1:
            return
            
        current_page_human = self.current_page + 1
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Move Page {current_page_human}")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # Information label
        info_label = QLabel(f"Move page {current_page_human} to position:")
        layout.addWidget(info_label)
        
        # Spinbox for selecting destination
        spinbox = QSpinBox()
        spinbox.setRange(1, self.total_pages)
        spinbox.setValue(current_page_human)
        layout.addWidget(spinbox)
        
        # Buttons
        button_box = QHBoxLayout()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        
        move_button = QPushButton("Move")
        move_button.clicked.connect(dialog.accept)
        move_button.setDefault(True)
        
        button_box.addWidget(cancel_button)
        button_box.addWidget(move_button)
        layout.addLayout(button_box)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            target_page = spinbox.value() - 1  # Convert to 0-based
            self.move_page_to(self.current_page, target_page)

    def show_context_menu(self, position: QPoint):
        """Shows the right-click context menu."""
        # Skip if no document
        if not self.doc:
            return
            
        # Create menu
        context_menu = QMenu(self)
        
        # Existing assembly operations (only show if not in assembly document)
        if not self._is_assembly_target:
            assembly_widget = self.find_assembly_widget()
            if assembly_widget:
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
        
        # Add page reordering actions (available in any document with multiple pages)
        if self.total_pages > 1:
            # Add separator if we added assembly operations
            if not context_menu.isEmpty():
                context_menu.addSeparator()
                
            # Move page up action (disabled for first page)
            move_up_action = QAction("Move Page Up", self)
            move_up_action.triggered.connect(self.move_current_page_up)
            move_up_action.setEnabled(self.current_page > 0)
            context_menu.addAction(move_up_action)
            
            # Move page down action (disabled for last page)
            move_down_action = QAction("Move Page Down", self)
            move_down_action.triggered.connect(self.move_current_page_down)
            move_down_action.setEnabled(self.current_page < self.total_pages - 1)
            context_menu.addAction(move_down_action)
            
            # Move to specific page
            move_to_action = QAction("Move Page To...", self)
            move_to_action.triggered.connect(self.show_move_page_dialog)
            context_menu.addAction(move_to_action)
        
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
                # Remember initial state
                was_empty = assembly_widget.total_pages == 0
                
                # Insert the current page into the assembly document
                target_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
                
                # Update assembly document state
                assembly_widget.total_pages = len(target_doc)
                
                # Navigate to the newly added page in the assembly tab
                new_page_index = assembly_widget.total_pages - 1
                assembly_widget.goto_page(new_page_index)
                
                # Force refresh if this was the first page
                if was_empty:
                    assembly_widget.pixmap_cache = {}  # Clear cache
                    assembly_widget.display_page()  # Force refresh
                
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
                # Remember initial state and page count before insertion
                was_empty = assembly_widget.total_pages == 0
                num_pages_before = assembly_widget.total_pages
                
                # Insert all pages
                target_doc.insert_pdf(source_doc)
                
                # Update assembly document state
                assembly_widget.total_pages = len(target_doc)
                
                # Navigate to the first of the newly added pages
                new_page_index = num_pages_before
                assembly_widget.goto_page(new_page_index)
                
                # Force refresh if this was the first page added to an empty assembly
                if was_empty:
                    assembly_widget.pixmap_cache = {}  # Clear cache
                    assembly_widget.display_page()  # Force refresh
                
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
                self.search_results.reset()


# ============================================================
#  SearchPanel: Widget for search UI
# ============================================================
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


# ============================================================
#  AboutDialog: Dialog showing info about the application
# ============================================================
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
            script_dir = os.path.dirname(os.path.realpath(__file__))
            logo_path = os.path.join(script_dir, BACKGROUND_IMAGE_FILENAME)
            if os.path.exists(logo_path):
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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


# ============================================================
#  PDFViewer: Main Application Window using QTabWidget
# ============================================================
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


# --- Application Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("FreeBird PDF")
    viewer = PDFViewer()
    viewer.show()
    sys.exit(app.exec())