# freebird/utils/thumbnail.py

import fitz
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QProgressDialog
)
from PyQt6.QtGui import (
    QPixmap, QImage, QIcon, QPainter, QPen, QColor
)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect

from freebird.utils.helpers import show_message

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