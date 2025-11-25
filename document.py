import os
import zipfile
import shutil
import re
import xml.etree.ElementTree as ET

class WordDocumentProcessor:
    """
    Handles reading and writing to .docx files by treating them
    as zipped XML directories. 
    
    This avoids external dependencies like python-docx, which 
    often struggles with Endnote XML.
    """
    
    NAMESPACES = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'xml': 'http://www.w3.org/XML/1998/namespace'
    }

    def __init__(self, filepath):
        self.filepath = filepath
        # Create a specific directory for extraction based on filename
        self.extract_dir = filepath + "_extracted"
        self._ensure_extracted()

    def _ensure_extracted(self):
        """Unzips the .docx if it hasn't been unzipped yet."""
        if not os.path.exists(self.extract_dir):
            with zipfile.ZipFile(self.filepath, 'r') as zip_ref:
                zip_ref.extractall(self.extract_dir)

    @property
    def endnotes_path(self):
        return os.path.join(self.extract_dir, 'word', 'endnotes.xml')

    def get_endnotes(self):
        """
        Parses word/endnotes.xml and returns a list of dictionaries.
        Format: [{'id': '1', 'text': 'Citation text...'}, ...]
        """
        if not os.path.exists(self.endnotes_path):
            return []

        try:
            tree = ET.parse(self.endnotes_path)
            root = tree.getroot()
            notes = []

            for endnote in root.findall('.//w:endnote', self.NAMESPACES):
                note_id = endnote.get(f"{{{self.NAMESPACES['w']}}}id")
                
                # Filter out separators (id -1) and continuators (id 0)
                try:
                    if int(note_id) < 1: continue
                except (ValueError, TypeError):
                    continue

                # Extract text from all <w:t> nodes within the endnote
                text_parts = []
                for node in endnote.findall('.//w:t', self.NAMESPACES):
                    if node.text:
                        text_parts.append(node.text)
                
                full_text = "".join(text_parts)
                
                if full_text.strip():
                    notes.append({
                        'id': note_id,
                        'text': full_text
                    })
            
            return notes

        except Exception as e:
            print(f"Error parsing endnotes: {e}")
            return []

    def write_endnote(self, note_id, new_content):
        """
        Updates the text of a specific endnote in the XML.
        Note: This currently strips HTML tags to ensure XML validity.
        """
        if not os.path.exists(self.endnotes_path):
            return False

        try:
            # register namespace to prevent ns0: prefixes
            ET.register_namespace('w', self.NAMESPACES['w'])
            
            tree = ET.parse(self.endnotes_path)
            root = tree.getroot()
            
            target_note = None
            for endnote in root.findall('.//w:endnote', self.NAMESPACES):
                if endnote.get(f"{{{self.NAMESPACES['w']}}}id") == str(note_id):
                    target_note = endnote
                    break
            
            if target_note is None:
                return False

            # 1. Strip HTML tags (handling <i>, </i>, etc. from formatter)
            # A robust implementation would convert <i> to <w:rPr><w:i/></w:rPr>
            # For now, we strip to plain text to prevent corruption.
            clean_text = re.sub(r'<[^>]+>', '', new_content)

            # 2. Find all existing text nodes
            text_nodes = target_note.findall('.//w:t', self.NAMESPACES)
            
            if not text_nodes:
                # If no text nodes exist, we might need to create structure
                # This is a simple fallback for existing nodes
                return False

            # 3. Update the FIRST text node and clear the rest
            # This preserves the paragraph structure of the original note
            text_nodes[0].text = clean_text
            for node in text_nodes[1:]:
                node.text = ""

            tree.write(self.endnotes_path, encoding='UTF-8', xml_declaration=True)
            return True

        except Exception as e:
            print(f"Error writing endnote: {e}")
            return False

    def save_as(self, output_path):
        """
        Re-zips the extracted directory into a new .docx file.
        """
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Archive name must be relative to the extract root
                    arcname = os.path.relpath(file_path, self.extract_dir)
                    zipf.write(file_path, arcname)
