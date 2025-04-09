# freebird/ui/pdf_view.py

import os
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QMessageBox, 
    QHBoxLayout, QDialog, QMenu, QFileDialog
)
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QAction
)
from PyQt6.QtCore import Qt, QRect, QBuffer

from freebird.constants import ASSEMBLY_PREFIX
from freebird.utils.helpers import show_message

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
            if main_window is not None and hasattr(main_window, 'get_current_view_widget') and callable(main_window.get_current_view_widget):
                if main_window.get_current_view_widget() is self:
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
        if main_window is not None and hasattr(main_window, 'update_button_states') and callable(main_window.update_button_states):
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
        from PyQt6.QtWidgets import QSpinBox
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

    def show_context_menu(self, position):
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
        from PyQt6.QtWidgets import QTabWidget
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