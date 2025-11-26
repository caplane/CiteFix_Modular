import os
import zipfile
import re
import html  # <--- NEW: Handles &lt;i&gt; or other browser encodings
import xml.etree.ElementTree as ET

class WordDocumentProcessor:
    """
    Handles reading and writing to .docx files by treating them
    as zipped XML directories.
    """
    
    NAMESPACES = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'xml': 'http://www.w3.org/XML/1998/namespace'
    }

    def __init__(self, filepath):
        self.filepath = filepath
        self.extract_dir = filepath + "_extracted"
        self._ensure_extracted()

    def _ensure_extracted(self):
        if not os.path.exists(self.extract_dir):
            with zipfile.ZipFile(self.filepath, 'r') as zip_ref:
                zip_ref.extractall(self.extract_dir)

    @property
    def endnotes_path(self):
        return os.path.join(self.extract_dir, 'word', 'endnotes.xml')

    def get_endnotes(self):
        if not os.path.exists(self.endnotes_path):
            return []

        try:
            tree = ET.parse(self.endnotes_path)
            root = tree.getroot()
            notes = []

            for endnote in root.findall('.//w:endnote', self.NAMESPACES):
                note_id = endnote.get(f"{{{self.NAMESPACES['w']}}}id")
                try:
                    if int(note_id) < 1: continue
                except (ValueError, TypeError):
                    continue

                text_parts = []
                for node in endnote.findall('.//w:t', self.NAMESPACES):
                    if node.text:
                        text_parts.append(node.text)
                
                full_text = "".join(text_parts)
                if full_text.strip():
                    notes.append({'id': note_id, 'text': full_text})
            
            return notes
        except Exception as e:
            print(f"Error parsing endnotes: {e}")
            return []

    def write_endnote(self, note_id, new_content):
        """
        Updates the text of a specific endnote in the XML.
        
        CRITICAL UPDATES:
        1. Unescapes HTML entities (fixes &lt;i&gt; issues).
        2. Uses flexible regex to catch <I>, <i>, </I>, </i>.
        """
        if not os.path.exists(self.endnotes_path):
            return False

        try:
            # 1. Clean the input
            # If the browser sent &lt;i&gt;, this turns it back into <i>
            clean_content = html.unescape(new_content)

            ET.register_namespace('w', self.NAMESPACES['w'])
            ET.register_namespace('xml', self.NAMESPACES['xml'])
            
            tree = ET.parse(self.endnotes_path)
            root = tree.getroot()
            
            # 2. Find the note
            target_note = None
            for endnote in root.findall('.//w:endnote', self.NAMESPACES):
                if endnote.get(f"{{{self.NAMESPACES['w']}}}id") == str(note_id):
                    target_note = endnote
                    break
            
            if target_note is None:
                return False

            # 3. Prepare the Paragraph
            paragraph = target_note.find('.//w:p', self.NAMESPACES)
            if paragraph is None:
                paragraph = ET.SubElement(target_note, f"{{{self.NAMESPACES['w']}}}p")
            else:
                for child in list(paragraph):
                    paragraph.remove(child)

            # 4. Robust Parsing (The Magic Fix)
            # This regex matches:
            # </?  -> Starts with < or </
            # i    -> The letter i (case insensitive via flag)
            # [^>]* -> Any attributes (like class="...")
            # >    -> Closing bracket
            parts = re.split(r'(</?i[^>]*>)', clean_content, flags=re.IGNORECASE)
            
            is_italic = False
            
            for part in parts:
                # Normalize text for checking
                lower_tag = part.lower().replace(' ', '')
                
                # Check start tag (matches <i>, <I>, <i class...>)
                if lower_tag.startswith('<i'):
                    is_italic = True
                    continue
                # Check end tag (matches </i>, </I>)
                elif lower_tag.startswith('</i'):
                    is_italic = False
                    continue
                
                if not part: continue

                # Create Run
                run = ET.SubElement(paragraph, f"{{{self.NAMESPACES['w']}}}r")
                
                # Apply Italic Style
                if is_italic:
                    rPr = ET.SubElement(run, f"{{{self.NAMESPACES['w']}}}rPr")
                    ET.SubElement(rPr, f"{{{self.NAMESPACES['w']}}}i")
                    
                # Write Text
                text_node = ET.SubElement(run, f"{{{self.NAMESPACES['w']}}}t")
                text_node.text = part
                # Force Word to keep spaces
                text_node.set(f"{{{self.NAMESPACES['xml']}}}space", "preserve")

            tree.write(self.endnotes_path, encoding='UTF-8', xml_declaration=True)
            return True

        except Exception as e:
            print(f"Error writing endnote: {e}")
            return False

    def save_as(self, output_path):
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.extract_dir)
                    zipf.write(file_path, arcname)
