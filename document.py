import os
import zipfile
import html
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, NavigableString # Robust HTML parsing

class WordDocumentProcessor:
    """
    Handles reading and writing to .docx files by treating them
    as zipped XML directories. Uses BeautifulSoup for robust HTML-to-XML conversion.
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
        Updates the endnote using BeautifulSoup to parse HTML tags (<i>, <em>)
        and convert them to MS Word XML runs (<w:r><w:rPr><w:i/>...).
        """
        if not os.path.exists(self.endnotes_path):
            return False

        try:
            # 1. Setup XML Parsing
            ET.register_namespace('w', self.NAMESPACES['w'])
            tree = ET.parse(self.endnotes_path)
            root = tree.getroot()
            
            # 2. Find the target endnote
            target_note = None
            for endnote in root.findall('.//w:endnote', self.NAMESPACES):
                if endnote.get(f"{{{self.NAMESPACES['w']}}}id") == str(note_id):
                    target_note = endnote
                    break
            
            if target_note is None:
                return False

            # 3. Clear existing paragraph content
            paragraph = target_note.find('.//w:p', self.NAMESPACES)
            if paragraph is None:
                paragraph = ET.SubElement(target_note, f"{{{self.NAMESPACES['w']}}}p")
            else:
                # Remove all children (runs) to start fresh
                for child in list(paragraph):
                    paragraph.remove(child)

            # 4. ROBUST PARSING WITH BEAUTIFUL SOUP
            # Unescape first to ensure < and > are real tags
            clean_html = html.unescape(new_content)
            soup = BeautifulSoup(clean_html, 'html.parser')
            
            # Helper to write a run to the paragraph
            def write_run(text, italic=False, bold=False):
                if not text: return
                run = ET.SubElement(paragraph, f"{{{self.NAMESPACES['w']}}}r")
                
                # Add properties (Italic/Bold)
                if italic or bold:
                    rPr = ET.SubElement(run, f"{{{self.NAMESPACES['w']}}}rPr")
                    if italic:
                        ET.SubElement(rPr, f"{{{self.NAMESPACES['w']}}}i")
                    if bold:
                        ET.SubElement(rPr, f"{{{self.NAMESPACES['w']}}}b")
                
                # Add Text
                text_node = ET.SubElement(run, f"{{{self.NAMESPACES['w']}}}t")
                text_node.text = text
                # Critical: preserve space so " v. " doesn't collapse
                text_node.set(f"{{{self.NAMESPACES['xml']}}}space", "preserve")

            # 5. Iterate through parsed nodes
            # Note: This simple parser handles flat structures. 
            # If you have nested tags (<b><i>text</i></b>), it treats the outer one as dominant
            # or splits them. For citations, flat is usually sufficient.
            
            for element in soup.contents:
                if isinstance(element, NavigableString):
                    # It's just text
                    write_run(str(element), italic=False)
                elif element.name in ['i', 'em']:
                    # It's Italic
                    write_run(element.get_text(), italic=True)
                elif element.name in ['b', 'strong']:
                    # It's Bold
                    write_run(element.get_text(), bold=True)
                else:
                    # Fallback for other tags (span, etc) - just write text
                    write_run(element.get_text(), italic=False)

            # 6. Save
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
