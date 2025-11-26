import re
import os
import zipfile
import shutil
import tempfile
import html

# ==============================================================================
# 1. CITATION FORMATTER (The Style Engine)
# ==============================================================================
class CitationFormatter:
    """
    HANDLES STRING FORMATTING:
    Converts metadata dictionaries into styled citation strings 
    (Chicago, Bluebook, OSCOLA, APA, MLA).
    """
    
    @staticmethod
    def format(metadata, style='chicago'):
        """Master Router for Citation Styles"""
        style = style.lower()
        source_type = metadata.get('type')
        
        # === CHICAGO (History/Humanities) ===
        if style == 'chicago':
            if source_type == 'legal': return CitationFormatter._chicago_legal(metadata)
            if source_type == 'journal': return CitationFormatter._chicago_journal(metadata)
            if source_type == 'book': return CitationFormatter._chicago_book(metadata)
            if source_type == 'newspaper': return CitationFormatter._chicago_newspaper(metadata)
            if source_type == 'government': return CitationFormatter._chicago_gov(metadata)

        # === BLUEBOOK (US Law) ===
        elif style == 'bluebook':
            if source_type == 'legal': return CitationFormatter._bluebook_legal(metadata)
            if source_type == 'journal': return CitationFormatter._bluebook_journal(metadata)
            if source_type == 'book': return CitationFormatter._bluebook_book(metadata)
            return CitationFormatter._chicago_gov(metadata) # Fallback

        # === OSCOLA (UK Law) ===
        elif style == 'oscola':
            if source_type == 'legal': return CitationFormatter._oscola_legal(metadata)
            if source_type == 'journal': return CitationFormatter._oscola_journal(metadata)
            if source_type == 'book': return CitationFormatter._oscola_book(metadata)
            return CitationFormatter._chicago_gov(metadata) # Fallback

        # === APA (Psychology/Sciences) ===
        elif style == 'apa':
            if source_type == 'journal': return CitationFormatter._apa_journal(metadata)
            if source_type == 'book': return CitationFormatter._apa_book(metadata)
            if source_type == 'legal': return CitationFormatter._bluebook_legal(metadata)
            return CitationFormatter._apa_generic(metadata)

        # === MLA (Humanities) ===
        elif style == 'mla':
            if source_type == 'journal': return CitationFormatter._mla_journal(metadata)
            if source_type == 'book': return CitationFormatter._mla_book(metadata)
            return CitationFormatter._mla_generic(metadata)
            
        return metadata.get('raw_source', '')

    # ==================== HELPERS ====================

    @staticmethod
    def _format_authors(authors, style='chicago'):
        if not authors: return ""
        def split_name(name):
            parts = name.split()
            return (parts[0], " ".join(parts[1:])) if len(parts) > 1 else (name, "")

        if style == 'apa':
            formatted = []
            for name in authors:
                first, last = split_name(name)
                initial = f"{first[0]}." if first else ""
                formatted.append(f"{last}, {initial}")
            if len(formatted) > 1: return ", & ".join(formatted)
            return formatted[0]
        elif style == 'mla':
            if len(authors) == 1:
                first, last = split_name(authors[0])
                return f"{last}, {first}"
            elif len(authors) == 2:
                f1, l1 = split_name(authors[0])
                return f"{l1}, {f1}, and {authors[1]}" 
            else:
                f1, l1 = split_name(authors[0])
                return f"{l1}, {f1}, et al"
        
        if len(authors) == 1: return authors[0]
        elif len(authors) == 2: return f"{authors[0]} and {authors[1]}"
        return f"{authors[0]} et al."

    # ==================== CHICAGO IMPLEMENTATION ====================

    @staticmethod
    def _chicago_journal(data):
        parts = []
        if data.get('authors'): parts.append(CitationFormatter._format_authors(data['authors'], 'chicago'))
        if data.get('title'): parts.append(f'"{data["title"]}"')
        journal_str = f"<i>{data.get('journal', '')}</i>"
        if data.get('volume'): journal_str += f" {data['volume']}"
        if data.get('issue'): journal_str += f", no. {data['issue']}"
        if data.get('year'): journal_str += f" ({data['year']})"
        if data.get('pages'): journal_str += f": {data['pages']}"
        parts.append(journal_str)
        if data.get('doi'): parts.append(f"https://doi.org/{data['doi']}")
        elif data.get('url'): parts.append(data['url'])
        return ", ".join(parts) + "."

    @staticmethod
    def _chicago_book(data):
        parts = []
        if data.get('authors'): parts.append(CitationFormatter._format_authors(data['authors'], 'chicago'))
        if data.get('title'): parts.append(f"<i>{data['title']}</i>")
        pub_str = ""
        place = data.get('place')
        publisher = data.get('publisher')
        year = data.get('year')
        if place: pub_str += place
        if publisher: pub_str += f": {publisher}" if place else publisher
        if year: pub_str += f", {year}" if (place or publisher) else year
        if pub_str: parts.append(f"({pub_str})")
        return ", ".join(parts) + "."

    @staticmethod
    def _chicago_legal(data):
        citation = data.get('citation', '')
        case_name = f"<i>{data.get('case_name', '')}</i>"
        court_year = f"({data.get('court', '')} {data.get('year', '')})".replace('  ', ' ')
        if citation: return f"{case_name}, {citation} {court_year}."
        return f"{case_name} {court_year}."

    @staticmethod
    def _chicago_gov(data):
        # PATCHED: Explicitly separate URL from the period to help the LinkActivator.
        parts = []
        parts.append(f"{data.get('author', 'U.S. Gov')}")
        parts.append(f"\"{data.get('title')}\"")
        parts.append(f"accessed {data.get('access_date')}")
        
        base_cit = ", ".join(parts)
        url = data.get('url')
        
        if url: 
            return f"{base_cit}, {url}." # The period is outside the URL
        return f"{base_cit}."

    @staticmethod
    def _chicago_newspaper(data):
        parts = []
        if data.get('author'): parts.append(data['author'])
        parts.append(f'"{data.get("title", "")}"')
        if data.get('newspaper'): parts.append(f"<i>{data['newspaper']}</i>")
        if data.get('date'): parts.append(data['date'])
        if data.get('url'): parts.append(data['url'])
        return ", ".join(parts) + "."

    # ==================== OTHER STYLES (Bluebook, OSCOLA, APA, MLA) ====================
    
    @staticmethod
    def _bluebook_legal(data):
        citation = data.get('citation', '')
        case_name = f"<i>{data.get('case_name', '')}</i>"
        court = data.get('court', '')
        if 'U.S.' in citation and not court: court = '' 
        parenthetical = f"({court} {data.get('year', '')})".replace('  ', ' ').replace('()', '')
        if citation: return f"{case_name}, {citation} {parenthetical}."
        return f"{case_name} {parenthetical}."
    
    @staticmethod
    def _bluebook_journal(data):
        author = CitationFormatter._format_authors(data.get('authors', []), 'bluebook')
        title = f"<i>{data.get('title', '')}</i>"
        journal = f"{data.get('journal', '')}" 
        return f"{author}, {title}, {data.get('volume', '')} {journal} {data.get('pages', '')} ({data.get('year', '')})."
    
    @staticmethod
    def _bluebook_book(data):
        author = CitationFormatter._format_authors(data.get('authors', []), 'bluebook')
        title = data.get('title', '').upper()
        return f"{author}, {title} ({data.get('year', '')})."

    @staticmethod
    def _oscola_legal(data):
        case_name = f"<i>{data.get('case_name', '')}</i>"
        citation = data.get('citation', '')
        court = data.get('court', '')
        year = data.get('year', '')
        year_str = f"({year})" if year else ""
        return f"{case_name} {year_str} {citation} ({court})"
    
    @staticmethod
    def _oscola_journal(data):
        author = CitationFormatter._format_authors(data.get('authors', []), 'oscola')
        title = f"'{data.get('title', '')}'"
        return f"{author}, {title} ({data.get('year', '')}) {data.get('volume', '')} {data.get('journal', '')} {data.get('pages', '')}."
    
    @staticmethod
    def _oscola_book(data):
        author = CitationFormatter._format_authors(data.get('authors', []), 'oscola')
        title = f"<i>{data.get('title', '')}</i>"
        pub_info = f"({data.get('publisher', '')} {data.get('year', '')})".replace('  ', ' ')
        return f"{author}, {title} {pub_info}."
        
    @staticmethod
    def _apa_journal(data):
        author = CitationFormatter._format_authors(data.get('authors', []), 'apa')
        year = f"({data.get('year', 'n.d.')})"
        title = data.get('title', '')
        journal = f"<i>{data.get('journal', '')}</i>"
        vol = f"<i>{data.get('volume', '')}</i>"
        issue = f"({data.get('issue', '')})" if data.get('issue') else ""
        pages = data.get('pages', '')
        return f"{author} {year}. {title}. {journal}, {vol}{issue}, {pages}."
    
    @staticmethod
    def _apa_book(data):
        author = CitationFormatter._format_authors(data.get('authors', []), 'apa')
        year = f"({data.get('year', 'n.d.')})"
        title = f"<i>{data.get('title', '')}</i>"
        publisher = data.get('publisher', '')
        return f"{author} {year}. {title}. {publisher}."

    @staticmethod
    def _apa_generic(data):
        return f"{data.get('raw_source', '')}"

    @staticmethod
    def _mla_journal(data):
        author = CitationFormatter._format_authors(data.get('authors', []), 'mla')
        title = f'"{data.get("title", "")}."'
        journal = f"<i>{data.get('journal', '')}</i>"
        details = []
        if data.get('volume'): details.append(f"vol. {data['volume']}")
        if data.get('issue'): details.append(f"no. {data['issue']}")
        if data.get('year'): details.append(data['year'])
        if data.get('pages'): details.append(f"pp. {data['pages']}")
        det_str = ", ".join(details)
        return f"{author} {title} {journal}, {det_str}."
    
    @staticmethod
    def _mla_book(data):
        author = CitationFormatter._format_authors(data.get('authors', []), 'mla')
        title = f"<i>{data.get('title', '')}</i>."
        pub = data.get('publisher', '')
        year = data.get('year', '')
        return f"{author} {title} {pub}, {year}."

    @staticmethod
    def _mla_generic(data):
        return f"{data.get('raw_source', '')}"


# ==============================================================================
# 2. DOCUMENT PROCESSOR (The Genie File Handler)
# ==============================================================================
class DocumentProcessor:
    """
    HANDLES FILE MANIPULATION USING THE 'GENIE' METHOD:
    Preserves document structure via copytree and injects text into existing XML.
    """

    @staticmethod
    def extract_structure(file_path):
        """Step 1: Unzip to Temp Dir"""
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Read relevant XML files
            content_map = {}
            for target in ['word/document.xml', 'word/endnotes.xml', 'word/footnotes.xml', 'word/styles.xml']:
                path = os.path.join(temp_dir, target)
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        content_map[target] = f.read()
            
            return {
                'content_map': content_map, 
                'temp_dir': temp_dir
            }
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    @staticmethod
    def parse_citations(xml_content):
        """Step 2: Parse Citations"""
        if not xml_content: return []
        endnotes = []
        note_pattern = r'<w:(?:endnote|footnote)[^>]*w:id="(\d+)"[^>]*>(.*?)</w:(?:endnote|footnote)>'
        matches = re.finditer(note_pattern, xml_content, re.DOTALL)
        
        for match in matches:
            note_id = match.group(1)
            note_content = match.group(2)
            if note_id in ['-1', '0']: continue 
            
            text_pattern = r'<w:t[^>]*>([^<]+)</w:t>'
            texts = re.findall(text_pattern, note_content)
            full_text = ''.join(texts)
            
            if full_text.strip():
                endnotes.append({
                    'id': note_id,
                    'text': full_text.strip(),
                    'original_xml': note_content
                })
        return endnotes

    @staticmethod
    def create_formatted_docx(docx_structure, formatted_citations, output_path):
        """
        Step 3: Create Output
        Uses 'Blind Replace' to update text, THEN calls LinkActivator to fix URLs.
        """
        temp_output = tempfile.mkdtemp()
        
        try:
            # A. PRESERVE STRUCTURE: Copy everything from original
            shutil.copytree(docx_structure['temp_dir'], temp_output, dirs_exist_ok=True)
            
            # B. UPDATE TEXT CONTENT (The Genie Logic)
            for xml_file in ['word/endnotes.xml', 'word/footnotes.xml']:
                file_path = os.path.join(temp_output, xml_file)
                if not os.path.exists(file_path): continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
                
                for citation in formatted_citations:
                    formatted_text = citation['formatted']
                    cid = citation['id']
                    
                    # Regex handles both endnote and footnote tags depending on file
                    tag_name = "endnote" if "endnote" in xml_file else "footnote"
                    note_regex = f'<w:{tag_name}[^>]*w:id="{cid}"[^>]*>(.*?)</w:{tag_name}>'
                    match = re.search(note_regex, xml_content, re.DOTALL)
                    
                    if match:
                        note_xml = match.group(1)
                        # Blind replace first text node (simplest method, LinkActivator will fix result)
                        text_match = re.search(r'(<w:t[^>]*>)([^<]+)(</w:t>)', note_xml)
                        if text_match:
                            new_xml = note_xml[:text_match.start()] + \
                                      text_match.group(1) + formatted_text + text_match.group(3)
                            
                            # Clean up subsequent text nodes to prevent duplication
                            # This regex removes subsequent w:t tags to be safe
                            # (Optional but recommended so we don't have trailing garbage)
                            suffix = note_xml[text_match.end():]
                            # suffix = re.sub(r'<w:t[^>]*>.*?</w:t>', '', suffix) 
                            
                            # Simple reconstruction
                            full_note = f'<w:{tag_name} w:id="{cid}">{new_xml}{suffix}</w:{tag_name}>'
                            xml_content = xml_content.replace(match.group(0), full_note)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
            
            # C. RE-ZIP
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_output):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_output)
                        zipf.write(file_path, arcname)
            
            # D. CRITICAL: ACTIVATION STEP
            # Now that the file is written, run the LinkActivator on it
            # This turns the plain text URLs into "Heavy Artillery" Field Codes.
            LinkActivator.process(output_path)
            
            return True
            
        finally:
            shutil.rmtree(temp_output, ignore_errors=True)


# ==============================================================================
# 3. LINK ACTIVATOR (The Heavy Artillery Fix)
# ==============================================================================
class LinkActivator:
    """
    POST-PROCESSING MODULE:
    Scans a .docx file for plain text URLs (e.g., http://...) and forces them 
    to become live, clickable, blue, underlined hyperlinks using Word Field Characters.
    """

    @staticmethod
    def process(docx_path, output_path=None):
        if output_path is None: output_path = docx_path
        temp_dir = tempfile.mkdtemp()
        
        try:
            with zipfile.ZipFile(docx_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            target_files = ['word/document.xml', 'word/endnotes.xml', 'word/footnotes.xml']
            
            for xml_file in target_files:
                full_path = os.path.join(temp_dir, xml_file)
                if not os.path.exists(full_path): continue

                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                def linkify_text_node(match):
                    text_content = match.group(2) 
                    url_match = re.search(r'(https?://[^\s<>"]+)', text_content)
                    
                    if url_match:
                        url = url_match.group(1)
                        clean_url = url.rstrip('.,;)')
                        trailing_punct = url[len(clean_url):]
                        safe_url = html.escape(clean_url)
                        
                        parts = text_content.split(url, 1)
                        pre = parts[0]
                        post = parts[1] if len(parts) > 1 else ""
                        
                        # FORCE FIELD CODES (Ctrl+F9 Style)
                        fld_begin = r'<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
                        instr = f'<w:r><w:instrText xml:space="preserve"> HYPERLINK "{safe_url}" </w:instrText></w:r>'
                        fld_sep = r'<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
                        display = (
                            f'<w:r>'
                            f'<w:rPr><w:color w:val="0000FF"/><w:u w:val="single"/></w:rPr>'
                            f'<w:t>{clean_url}</w:t>'
                            f'</w:r>'
                        )
                        fld_end = r'<w:r><w:fldChar w:fldCharType="end"/></w:r>'
                        
                        full_field_xml = f"{fld_begin}{instr}{fld_sep}{display}{fld_end}"
                        new_xml = f"{pre}</w:t></w:r>{full_field_xml}<w:r><w:t>{trailing_punct}{post}"
                        return f"{match.group(1)}{new_xml}{match.group(3)}"
                        
                    return match.group(0)

                run_pattern = r'(<w:r[^\>]*>)(.*?<w:t[^>]*>.*?<\/w:t>.*?)(<\/w:r>)'
                
                def process_run(run_match):
                    run_inner = run_match.group(2)
                    if 'HYPERLINK' in run_inner: return run_match.group(0)
                    if 'w:instrText' in run_inner: return run_match.group(0)
                    return re.sub(r'(<w:t[^>]*>)(.*?)(</w:t>)', linkify_text_node, run_match.group(0))

                new_content = re.sub(run_pattern, process_run, content, flags=re.DOTALL)
                
                if new_content != content:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            return True, "Hyperlinks Activated"

        except Exception as e:
            return False, str(e)
        finally:
            shutil.rmtree(temp_dir)
