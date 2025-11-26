import re
import os
import zipfile
import shutil
import tempfile

class LeanFormatter:
    """
    LEAN LINK ACTIVATOR:
    A specialized class that takes any .docx file and 'activates' plain text URLs.
    It works by wrapping detected URLs in Word Field Codes (HYPERLINK), 
    which forces Word to render them as clickable links without needing 
    complex Relationship (_rels) definitions.
    """

    @staticmethod
    def activate_links(docx_path, output_path=None):
        if output_path is None:
            output_path = docx_path

        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Unzip the DOCX
            with zipfile.ZipFile(docx_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # 2. Target XML files where citations live
            target_files = ['word/document.xml', 'word/endnotes.xml', 'word/footnotes.xml']
            
            for xml_file in target_files:
                full_path = os.path.join(temp_dir, xml_file)
                if not os.path.exists(full_path): continue

                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 3. The Activation Logic
                # We look for text nodes <w:t> that contain http/https
                # AND are NOT already inside a hyperlink or field code.
                
                def linkify_text(match):
                    text_content = match.group(2) # The inner text of the <w:t> tag
                    
                    # Regex to find the URL within the text node
                    # Matches http(s)://... up to a space, quote, or bracket
                    url_match = re.search(r'(https?://[^\s<>"]+)', text_content)
                    
                    if url_match:
                        url = url_match.group(1)
                        
                        # Separate potential punctuation (e.g., URL.)
                        clean_url = url.rstrip('.,;)')
                        trailing_punct = url[len(clean_url):]
                        
                        # Split the text node content into 3 parts: Pre, URL, Post
                        # Note: This simple split handles the first URL found in the node.
                        parts = text_content.split(url, 1)
                        pre = parts[0]
                        post = parts[1] if len(parts) > 1 else ""
                        
                        # BUILD THE FIELD CODE XML
                        # This tells Word: "This is a HYPERLINK field pointing to clean_url"
                        field_code = (
                            f'<w:fldSimple w:instr=" HYPERLINK &quot;{clean_url}&quot; ">'
                            f'<w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>'
                            f'<w:t>{clean_url}</w:t>'
                            f'</w:r>'
                            f'</w:fldSimple>'
                        )
                        
                        # Reassemble the XML
                        # We close the original <w:t>, start the field code, then maybe start a new <w:t>
                        
                        # Note: We must return valid run content. 
                        # Since we are inside a <w:t>, we technically need to close the <w:t> and <w:r> 
                        # and start new ones, but finding the parent <w:r> via regex is risky.
                        # SAFE STRATEGY: We assume we are inside a <w:r>. We close it, insert field, open new one.
                        
                        new_xml = f"{pre}</w:t></w:r>{field_code}<w:r><w:t>{trailing_punct}{post}"
                        
                        return f"{match.group(1)}{new_xml}{match.group(3)}"
                        
                    return match.group(0)

                # We strictly target <w:t> tags to avoid breaking XML structure
                # We assume standard Word XML structure: <w:r><w:t>TEXT</w:t></w:r>
                # This regex looks for w:t tags and applies the logic
                # It includes a check to ensure we aren't already in a hyperlink (rough heuristic)
                
                # A robust regex pass:
                # 1. Find runs <w:r>...<w:t>...</w:t>...</w:r>
                # 2. Check if they contain http
                run_pattern = r'(<w:r[^\>]*>)(.*?<w:t[^>]*>.*?<\/w:t>.*?)(<\/w:r>)'
                
                def process_run(run_match):
                    run_open = run_match.group(1)
                    run_inner = run_match.group(2)
                    run_close = run_match.group(3)
                    
                    # Double check: ignore if this run is part of an existing field code or link
                    # (This context check is hard with simple regex, but 'instr' usually appears in w:fldSimple parent)
                    
                    if 'HYPERLINK' in run_inner: return run_match.group(0)
                    
                    # Find the text node inside this run
                    return re.sub(r'(<w:t[^>]*>)(.*?)(</w:t>)', linkify_text, run_match.group(0))

                new_content = re.sub(run_pattern, process_run, content, flags=re.DOTALL)
                
                if new_content != content:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

            # 4. Re-zip
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            return True, "Links Activated"

        except Exception as e:
            return False, str(e)
        finally:
            shutil.rmtree(temp_dir)

# ====================
# HOW TO INTEGRATE
# ====================
# In your main app, after you create the formatted document using the existing logic,
# run this LeanFormatter on the output file.
# 
# Example:
# create_formatted_docx(..., output_path, ...)
# LeanFormatter.activate_links(output_path)
