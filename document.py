import os
import zipfile
import re
import xml.etree.ElementTree as ET

class WordDocumentProcessor:
    """
    Handles reading and writing to .docx files by treating them
    as zipped XML directories.
    
    UPDATED: Now supports writing italics into the XML structure.
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
        
        CRITICAL UPDATE:
        Instead of stripping HTML, this now parses <i> tags and converts 
        them to Word's <w:i/> XML tags to preserve italics.
        """
        if not os.path.exists(self.endnotes_path):
            return False

        try:
            # register namespace to prevent ns0: prefixes in output
            ET.register_namespace('w', self.NAMESPACES['w'])
            ET.register_namespace('xml', self.NAMESPACES['xml'])
            
            tree = ET.parse(self.endnotes_path)
            root = tree.getroot()
            
            # 1. Find the specific endnote by ID
            target_note = None
            for endnote in root.findall('.//w:endnote', self.NAMESPACES):
                if endnote.get(f"{{{self.NAMESPACES['w']}}}id") == str(note_id):
                    target_note = endnote
                    break
            
            if target_note is None:
                return False

            # 2. Find the first Paragraph <w:p> inside the note
            # We will clear this paragraph and rebuild it with our new runs
            paragraph = target_note.find('.//w:p', self.NAMESPACES)
            
            if paragraph is None:
                # If no paragraph exists (rare), create one
                paragraph = ET.SubElement(target_note, f"{{{self.NAMESPACES['w']}}}p")
            else:
                # Clear existing content (runs, text, etc.) from the paragraph
                # This ensures we don't duplicate text or leave old text behind
                for child in list(paragraph):
                    paragraph.remove(child)

            # 3. Parse the HTML content and build XML Runs (<w:r>)
            # We split by tags to separate italic parts from normal parts
            parts = re.split(r'(<i>|</i>)', new_content)
            is_italic = False
            
            for part in parts:
                if part == '<i>':
                    is_italic = True
                    continue
                elif part == '</i>':
                    is_italic = False
                    continue
                
                # Skip empty strings from the split
                if not part: continue

                # Create a new Run <w:r>
                run = ET.SubElement(paragraph, f"{{{self.NAMESPACES['w']}}}r")
                
                # If currently inside <i> tags, add the Property <w:rPr> and Italic <w:i/>
                if is_italic:
                    rPr = ET.SubElement(run, f"{{{self.NAMESPACES['w']}}}rPr")
                    ET.SubElement(rPr, f"{{{self.NAMESPACES['w']}}}i")
                    
                # Add the Text node <w:t>
                text_node = ET.SubElement(run, f"{{{self.NAMESPACES['w']}}}t")
                text_node.text = part
                
                # CRITICAL: Preserve spaces (otherwise Word might trim leading/trailing spaces)
                text_node.set(f"{{{self.NAMESPACES['xml']}}}space", "preserve")

            # 4. Save the modified XML back to disk
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
