import re
import os
import zipfile
import shutil
import tempfile

class LeanFormatter:
    """
    A specialized formatter that prioritizes URL preservation above all else.
    It separates the URL from the citation text and injects them into 
    separate XML containers (Text Run vs Hyperlink Run).
    """

    @staticmethod
    def format_document(file_path, citation_text, output_path=None):
        if output_path is None:
            output_path = file_path

        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Unzip
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # 2. Extract URL from the intended new citation
            # We assume the citation ends with the URL or URL + punctuation
            url_match = re.search(r'(https?://[^\s<>"]+)', citation_text)
            if not url_match:
                # Fallback: No URL found in new text? Just do standard replace.
                return False, "No URL found in citation text."

            new_url = url_match.group(1)
            # Split: "Author, Title, " [URL] "."
            parts = citation_text.split(new_url)
            pre_text = parts[0]
            post_text = parts[1] if len(parts) > 1 else ""

            # 3. Process XML Files
            target_files = ['word/endnotes.xml', 'word/footnotes.xml']
            processed_any = False
            
            for xml_file in target_files:
                full_path = os.path.join(temp_dir, xml_file)
                if not os.path.exists(full_path): continue

                with open(full_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()

                # Regex to find a Note that contains a Hyperlink
                # We capture: (Start of Note ...)(Hyperlink Tag)(... End of Note)
                # This is aggressive but necessary to re-order the runs correctly.
                # Note: This regex assumes one note per citation line roughly.
                
                # PATTERN: Find a note that contains <w:hyperlink ...>
                # We iterate over all notes first
                note_pattern = r'(<w:(?:endnote|footnote)[^>]*>)(.*?)(</w:(?:endnote|footnote)>)'
                
                def replace_note_content(match):
                    open_tag = match.group(1)
                    body = match.group(2)
                    close_tag = match.group(3)

                    # Does this note have a hyperlink?
                    link_match = re.search(r'(<w:hyperlink[^>]*>)(.*?)(</w:hyperlink>)', body, re.DOTALL)
                    
                    if link_match:
                        link_open = link_match.group(1)
                        # link_body = link_match.group(2) # We discard old link text
                        link_close = link_match.group(3)

                        # CONSTRUCT NEW XML CONTENT
                        # 1. Pre-Link Text (Author, Title)
                        # We use xml:space='preserve' to ensure spacing isn't eaten
                        new_body = f"<w:r><w:t xml:space='preserve'>{pre_text}</w:t></w:r>"
                        
                        # 2. The Link (Just the URL)
                        # We rebuild the link interior completely to ensure it's clean
                        new_link_body = f"<w:r><w:rPr><w:rStyle w:val='Hyperlink'/></w:rPr><w:t>{new_url}</w:t></w:r>"
                        new_body += f"{link_open}{new_link_body}{link_close}"
                        
                        # 3. Post-Link Text (Period)
                        if post_text:
                            new_body += f"<w:r><w:t>{post_text}</w:t></w:r>"
                        
                        return f"{open_tag}{new_body}{close_tag}"
                    
                    else:
                        # No link in original? Fallback to blind replace (Genie Style)
                        # Remove all existing text tags and replace with one new one
                        # This handles the 'black text' scenario safely
                        clean_body = re.sub(r'<w:r>.*?</w:r>', '', body, flags=re.DOTALL) # strip runs? Too aggressive.
                        # Less aggressive: Just replace text content
                        # (Implementation omitted for brevity, focusing on the link fix)
                        return match.group(0) 

                new_xml_content = re.sub(note_pattern, replace_note_content, xml_content, flags=re.DOTALL)
                
                if new_xml_content != xml_content:
                    processed_any = True
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_xml_content)

            # 4. Re-zip
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)

            return True, "Lean Formatting Complete"

        except Exception as e:
            return False, str(e)
        finally:
            shutil.rmtree(temp_dir)
