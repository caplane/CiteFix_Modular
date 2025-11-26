import re
import os
import zipfile
import shutil
import tempfile

class CitationFormatter:
    """
    HANDLES STRING FORMATTING:
    Converts metadata dictionaries into styled citation strings.
    """
    
    @staticmethod
    def format(metadata, style='chicago'):
        """Master Router for Citation Styles"""
        style = style.lower()
        source_type = metadata.get('type')
        
        # === CHICAGO ===
        if style == 'chicago':
            if source_type == 'legal': return CitationFormatter._chicago_legal(metadata)
            if source_type == 'journal': return CitationFormatter._chicago_journal(metadata)
            if source_type == 'book': return CitationFormatter._chicago_book(metadata)
            if source_type == 'newspaper': return CitationFormatter._chicago_newspaper(metadata)
            if source_type == 'government': return CitationFormatter._chicago_gov(metadata)

        # === BLUEBOOK ===
        elif style == 'bluebook':
            if source_type == 'legal': return CitationFormatter._bluebook_legal(metadata)
            if source_type == 'journal': return CitationFormatter._bluebook_journal(metadata)
            if source_type == 'book': return CitationFormatter._bluebook_book(metadata)
            return CitationFormatter._chicago_gov(metadata) 

        # === OSCOLA ===
        elif style == 'oscola':
            if source_type == 'legal': return CitationFormatter._oscola_legal(metadata)
            if source_type == 'journal': return CitationFormatter._oscola_journal(metadata)
            if source_type == 'book': return CitationFormatter._oscola_book(metadata)
            return CitationFormatter._chicago_gov(metadata) 

        # === APA ===
        elif style == 'apa':
            if source_type == 'journal': return CitationFormatter._apa_journal(metadata)
            if source_type == 'book': return CitationFormatter._apa_book(metadata)
            if source_type == 'legal': return CitationFormatter._bluebook_legal(metadata)
            return CitationFormatter._apa_generic(metadata)

        # === MLA ===
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

    # ==================== STYLE IMPLEMENTATIONS ====================

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
        parts = []
        parts.append(f"{data.get('author', 'U.S. Gov')}")
        parts.append(f"\"{data.get('title')}\"")
        parts.append(f"accessed {data.get('access_date')}")
        base_cit = ", ".join(parts)
        url = data.get('url')
        if url: 
            # Ensure the period is separate from the URL string
            return f"{base_cit}, {url}."
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

    # ... (Bluebook, OSCOLA, APA, MLA methods remain unchanged)
    
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
            
            # Read files
            content = ""
            doc_path = os.path.join(temp_dir, 'word', 'document.xml')
            if os.path.exists(doc_path):
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            endnotes_content = ""
            endnotes_path = os.path.join(temp_dir, 'word', 'endnotes.xml')
            if os.path.exists(endnotes_path):
                with open(endnotes_path, 'r', encoding='utf-8') as f:
                    endnotes_content = f.read()
            
            styles_content = ""
            styles_path = os.path.join(temp_dir, 'word', 'styles.xml')
            if os.path.exists(styles_path):
                with open(styles_path, 'r', encoding='utf-8') as f:
                    styles_content = f.read()
            
            return {
                'document': content,
                'endnotes': endnotes_content,
                'styles': styles_content,
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
        endnote_pattern = r'<w:endnote[^>]*w:id="(\d+)"[^>]*>(.*?)</w:endnote>'
        matches = re.finditer(endnote_pattern, xml_content, re.DOTALL)
        
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
        Uses 'Smart Replacement' to preserve hyperlinks.
        Instead of blindly overwriting the first node (which deletes links if they appear later),
        it detects <w:hyperlink> and injects the URL component specifically into the link tag.
        """
        temp_output = tempfile.mkdtemp()
        
        try:
            shutil.copytree(docx_structure['temp_dir'], temp_output, dirs_exist_ok=True)
            
            endnotes_path = os.path.join(temp_output, 'word', 'endnotes.xml')
            if os.path.exists(endnotes_path) and formatted_citations:
                with open(endnotes_path, 'r', encoding='utf-8') as f:
                    endnotes_content = f.read()
                
                for citation in formatted_citations:
                    formatted_text = citation['formatted']
                    
                    # Find the specific endnote block
                    pattern = f'<w:endnote[^>]*w:id="{citation["id"]}"[^>]*>(.*?)</w:endnote>'
                    match = re.search(pattern, endnotes_content, re.DOTALL)
                    
                    if match:
                        note_xml = match.group(1)
                        
                        # SMART LOGIC: Check if this note has a Hyperlink tag
                        hyperlink_match = re.search(r'(<w:hyperlink[^>]*>)(.*?)(</w:hyperlink>)', note_xml, re.DOTALL)
                        
                        if hyperlink_match:
                            # 1. Extract URL from the new formatted text
                            url_regex = re.search(r'(https?://[^\s<>]+?)([.,;]?)$', formatted_text)
                            
                            if url_regex:
                                found_url = url_regex.group(1)
                                punctuation = url_regex.group(2)
                                
                                # Split text into Pre-URL and URL parts
                                pre_text = formatted_text.replace(found_url + punctuation, "")
                                
                                # 2. Inject Pre-Text into the FIRST text node (before the link)
                                text_pattern = r'(<w:t[^>]*>)([^<]+)(</w:t>)'
                                text_matches = list(re.finditer(text_pattern, note_xml))
                                if text_matches:
                                    first_match = text_matches[0]
                                    # Replace first node content
                                    note_xml = note_xml[:first_match.start()] + \
                                               first_match.group(1) + pre_text + first_match.group(3) + \
                                               note_xml[first_match.end():]

                                # 3. Re-find the Hyperlink (content shifted) and inject URL into IT
                                hyperlink_match = re.search(r'(<w:hyperlink[^>]*>)(.*?)(</w:hyperlink>)', note_xml, re.DOTALL)
                                if hyperlink_match:
                                    link_inner = hyperlink_match.group(2)
                                    # Replace text inside the hyperlink tag
                                    link_inner = re.sub(r'(<w:t[^>]*>)([^<]+)(</w:t>)', r'\1' + found_url + r'\3', link_inner)
                                    
                                    # Add the punctuation (period) AFTER the link
                                    post_link = f"<w:r><w:t>{punctuation}</w:t></w:r>" if punctuation else ""
                                    
                                    # Reassemble
                                    note_xml = note_xml[:hyperlink_match.start()] + \
                                               hyperlink_match.group(1) + link_inner + hyperlink_match.group(3) + \
                                               post_link + \
                                               note_xml[hyperlink_match.end():]
                                    
                                    # Update content
                                    full_note = f'<w:endnote w:id="{citation["id"]}">{note_xml}</w:endnote>'
                                    endnotes_content = endnotes_content.replace(match.group(0), full_note)
                                    continue # Skip to next citation

                        # FALLBACK: No hyperlink tag found, or no URL in text? Use Standard Genie Blind Replace
                        text_pattern = r'(<w:t[^>]*>)([^<]+)(</w:t>)'
                        text_matches = list(re.finditer(text_pattern, note_xml))
                        
                        if text_matches:
                            first_match = text_matches[0]
                            new_xml = note_xml[:first_match.start()] + \
                                      first_match.group(1) + formatted_text + first_match.group(3)
                            
                            for sub_match in reversed(text_matches[1:]):
                                new_xml = new_xml[:sub_match.start()] + new_xml[sub_match.end():]
                            
                            full_note = f'<w:endnote w:id="{citation["id"]}">{new_xml}</w:endnote>'
                            endnotes_content = endnotes_content.replace(match.group(0), full_note)

                with open(endnotes_path, 'w', encoding='utf-8') as f:
                    f.write(endnotes_content)
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_output):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_output)
                        zipf.write(file_path, arcname)
            return True
            
        finally:
            shutil.rmtree(temp_output, ignore_errors=True)
