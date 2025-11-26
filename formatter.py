import re
import os
import zipfile
import shutil
import tempfile
import html

class LeanFormatter:
    """
    LEAN LINK ACTIVATOR (HEAVY ARTILLERY VERSION):
    Instead of using 'w:fldSimple' (which Word can ignore), this uses 
    verbose 'w:fldChar' tags. This constructs the link exactly how Word 
    does internally: [Begin Command] -> [Instruction] -> [Separator] -> [Display Text] -> [End Command].
    """

    @staticmethod
    def activate_links(docx_path, output_path=None):
        if output_path is None:
            output_path = docx_path

        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Unzip
            with zipfile.ZipFile(docx_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # 2. Target XML files
            target_files = ['word/document.xml', 'word/endnotes.xml', 'word/footnotes.xml']
            
            for xml_file in target_files:
                full_path = os.path.join(temp_dir, xml_file)
                if not os.path.exists(full_path): continue

                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 3. The Logic
                def linkify_text(match):
                    text_content = match.group(2) 
                    
                    # Regex to capture the URL
                    url_match = re.search(r'(https?://[^\s<>"]+)', text_content)
                    
                    if url_match:
                        url = url_match.group(1)
                        clean_url = url.rstrip('.,;)')
                        trailing_punct = url[len(clean_url):]
                        
                        # Escape URL for XML (e.g. & -> &amp;)
                        safe_url = html.escape(clean_url)
                        
                        parts = text_content.split(url, 1)
                        pre = parts[0]
                        post = parts[1] if len(parts) > 1 else ""
                        
                        # --- THE HEAVY ARTILLERY XML ---
                        # 1. Begin the field
                        fld_begin = r'<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
                        
                        # 2. The Instruction (HYPERLINK "url")
                        # We use xml:space='preserve' to ensure the space after HYPERLINK stays
                        instr = f'<w:r><w:instrText xml:space="preserve"> HYPERLINK "{safe_url}" </w:instrText></w:r>'
                        
                        # 3. Separator (End of instruction, start of what user sees)
                        fld_sep = r'<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
                        
                        # 4. The Display Text (Blue & Underlined)
                        display = (
                            f'<w:r>'
                            f'<w:rPr>'
                            f'<w:rStyle w:val="Hyperlink"/>'
                            f'<w:color w:val="0000FF"/>'
                            f'<w:u w:val="single"/>'
                            f'</w:rPr>'
                            f'<w:t>{clean_url}</w:t>'
                            f'</w:r>'
                        )
                        
                        # 5. End the field
                        fld_end = r'<w:r><w:fldChar w:fldCharType="end"/></w:r>'
                        
                        # Combine it all
                        full_field_xml = f"{fld_begin}{instr}{fld_sep}{display}{fld_end}"
                        
                        # Reassemble the surrounding text
                        # Close previous run, insert field block, open new run for punctuation
                        new_xml = f"{pre}</w:t></w:r>{full_field_xml}<w:r><w:t>{trailing_punct}{post}"
                        
                        return f"{match.group(1)}{new_xml}{match.group(3)}"
                        
                    return match.group(0)

                # Process Runs
                run_pattern = r'(<w:r[^\>]*>)(.*?<w:t[^>]*>.*?<\/w:t>.*?)(<\/w:r>)'
                
                def process_run(run_match):
                    run_inner = run_match.group(2)
                    if 'HYPERLINK' in run_inner: return run_match.group(0)
                    if 'w:instrText' in run_inner: return run_match.group(0)
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
            
            return True, "Links Activated (Verbose Field Codes)"

        except Exception as e:
            return False, str(e)
        finally:
            shutil.rmtree(temp_dir)
