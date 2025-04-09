def show_signature_dialog(self):
    """Show the signature dialog and process the result."""
    if not self.doc:
        show_message(self, "No Document", "Please open a document before signing.",
                    QMessageBox.Icon.Warning)
        return

    dialog = SignatureDialog(self.window(), self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        signature_info = dialog.get_all_signature_info()
        self.sign_document(signature_info)

def sign_document(self, signature_info):
    """Sign the current document with the provided signature info."""
    try:
        # Get PDF data
        pdf_data = None
        temp_file = None
        
        if self.doc:
            # We need to save the current state to a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.close()
            
            self.doc.save(temp_file.name)
            with open(temp_file.name, 'rb') as f:
                pdf_data = f.read()
        
        if not pdf_data:
            raise Exception("Could not get PDF data from the document.")
        
        # Show progress dialog
        progress = QProgressDialog("Signing document...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Sign the document using Endesive
        service = EndesiveService()
        signed_pdf, signed_page = service.sign_document(pdf_data, signature_info)
        
        # Create a new document with the signed PDF
        temp_signed = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_signed.write(signed_pdf)
        temp_signed.close()
        
        # Close current document
        self.close_document()
        
        # Load the signed document
        self.load_pdf(temp_signed.name)
        
        # Add text annotations
        service.add_text_annotations(self.doc, signature_info)
        
        # Go to the signed page
        self.goto_page(signed_page)
        
        # Mark as modified
        self.mark_modified(True)
        
        # Close progress dialog
        progress.close()
        
        # Clean up temporary files
        try:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            if os.path.exists(temp_signed.name):
                os.remove(temp_signed.name)
        except:
            pass
        
        # Show success message
        show_message(self, "Signature Complete", 
                    "The document has been successfully signed.",
                    QMessageBox.Icon.Information)
                    
    except Exception as e:
        # Show error message
        import traceback
        traceback.print_exc()
        show_message(self, "Signature Error", 
                    f"An error occurred while signing the document:\n{str(e)}",
                    QMessageBox.Icon.Critical)