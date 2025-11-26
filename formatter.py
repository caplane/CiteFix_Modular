import re
import os
import zipfile
import shutil
import tempfile

class CitationFormatter:
    """
    HANDLES STRING FORMATTING:
    Converts metadata dictionaries into styled citation strings 
    (Chicago, Bluebook, APA, MLA, OSCOLA).
    """
    
    @staticmethod
    def format(metadata, style='chicago'):
        """
        Master Router: Dispatches the citation to the correct style engine.
        Supported styles: 'chicago', 'bluebook', 'oscola', 'apa', 'mla'.
        """
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
            if source_type == 'legal': return CitationFormatter._bluebook_legal(metadata) # APA defers to Bluebook
            return CitationFormatter._apa_generic(metadata)

        # === MLA (Humanities) ===
        elif style == 'mla':
            if source_type == 'journal': return CitationFormatter._mla_journal(metadata)
            if source_type == 'book': return CitationFormatter._mla_book(metadata)
            return CitationFormatter._mla_generic(metadata)
            
        # Default Fallback
        return metadata.get('raw_source', '')

    # ==================== HELPERS ====================

    @staticmethod
    def _format_authors(authors, style='chicago'):
        """Smart author formatting based on style rules."""
        if not authors: return ""
        
        # Simple heuristic to split First/Last if needed
        def split_name(name):
            parts = name.split()
            return (parts[0], " ".join(parts[1:])) if len(parts) > 1 else (name, "")

        if style == 'apa':
            # APA: Last, F. M., & Last, F. M.
            formatted = []
            for name in authors:
                first, last = split_name(name)
                initial = f"{first[0]}." if first else ""
                formatted.append(f"{last}, {initial}")
            if len(formatted) > 1: return ", & ".join(formatted)
            return formatted[0]

        elif style == 'mla':
            # MLA: Last, First, and First Last.
            if len(authors) == 1:
                first, last = split_name(authors[0])
                return f"{last}, {first}"
            elif len(authors) == 2:
                f1, l1 = split_name(authors[0])
                return f"{l1}, {f1}, and {authors[1]}" # Second author is normal
            else:
                f1, l1 = split_name(authors[0])
                return f"{l1}, {f1}, et al"

        # Chicago / Bluebook / OSCOLA (First Last)
        if len(authors) == 1: return authors[0]
        elif len(authors) == 2: return f"{authors[0]} and {authors[1]}"
        return f"{authors[0]} et al."

    # ==================== 1. CHICAGO STYLE (17th Ed) ====================

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
        return f"{data.get('author', 'U.S. Gov')}, \"{data.get('title')},\" accessed {data.get('access_date')}, {data.get('url')}."

    @staticmethod
    def _chicago_newspaper(data):
        parts = []
        if data.get('author'): parts.append(data['author'])
        parts.append(f'"{data.get("title", "")}"')
        if data.get('newspaper'): parts.append(f"<i>{data['newspaper']}</i>")
        if data.get('date'): parts.append(data['date'])
        if data.get('url'): parts.append(data['url'])
        return ", ".join(parts) + "."

    # ==================== 2. BLUEBOOK (US Legal) ====================

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

    # ==================== 3. OSCOLA (UK Legal) ====================

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

    # ==================== 4. APA (Psychology) ====================

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

    # ==================== 5. MLA (Humanities) ====================

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


class DocxLinkPreserver:
    """
    HANDLES FILE MANIPULATION:
    Processes the raw DOCX structure to fix broken URLs that span multiple lines.
    This mimics the logic used in Incipit Genie (direct XML editing).
    """

    def __init__(self):
        # Regex to find URLs split by a hyphen and a newline/space
        # Matches: "http://...management-" + whitespace + "plan"
        self.url_split_pattern = r'(https?://[^\s<>"]+)-\s+([^\s<>"]+)'
        
        # Regex to find URLs split by just whitespace
        # Matches: "http://...management" + whitespace + "/plan"
        self.url_break_pattern = r'(https?://[^\s<>"]+)\s+(\/[^\s<>"]+)'

    def clean_text_content(self, text):
        """
        Fixes broken URLs in a plain text string.
        """
        # Fix hyphenated breaks
        text = re.sub(self.url_split_pattern, r'\1\2', text)
        # Fix whitespace breaks
        text = re.sub(self.url_break_pattern, r'\1\2', text)
        return text

    def _stitch_xml_nodes(self, xml_content):
        """
        Core logic to find split text nodes in endnotes/footnotes
        and stitch them back together without breaking surrounding tags.
        """
        # Pattern to find endnotes or footnotes blocks
        # We capture the ID to ensure we process distinct notes
        note_pattern = r'(<w:endnote[^>]*w:id="(\d+)"[^>]*>)(.*?)(</w:endnote>)'
        
        def replace_note_content(match):
            open_tag = match.group(1)
            # note_id = match.group(2) # Unused but available for debugging
            inner_xml = match.group(3)
            close_tag = match.group(4)

            # 1. Extract all text nodes <w:t> from this specific note
            text_node_pattern = r'(<w:t[^>]*>)([^<]+)(</w:t>)'
            text_matches = list(re.finditer(text_node_pattern, inner_xml))

            if not text_matches:
                return match.group(0)

            # 2. Join all text parts to form one cohesive string
            full_text = "".join([m.group(2) for m in text_matches])
            
            # 3. Apply the URL Fixer
            cleaned_text = self.clean_text_content(full_text)

            # 4. Reconstruction:
            # Inject clean text into the FIRST text node.
            # Delete subsequent text nodes (the fragments).
            # Preserve all non-text XML (formatting tags, runs, etc).
            
            first_match = text_matches[0]
            
            # Start of inner XML (before the first text)
            new_inner_xml = inner_xml[:first_match.start()]
            
            # The consolidated text node
            new_inner_xml += f"{first_match.group(1)}{cleaned_text}{first_match.group(3)}"
            
            # Append remaining XML, skipping the text nodes we just merged
            last_end = first_match.end()
            for next_match in text_matches[1:]:
                # Append content between the previous match and this one
                new_inner_xml += inner_xml[last_end:next_match.start()]
                last_end = next_match.end()
            
            # Append remaining XML after the last text node
            new_inner_xml += inner_xml[last_end:]

            return f"{open_tag}{new_inner_xml}{close_tag}"

        # Apply the replacement function
        return re.sub(note_pattern, replace_note_content, xml_content, flags=re.DOTALL)

    def process_document(self, input_path, output_path=None):
        """
        Main entry point for file processing.
        Unzips DOCX, repairs XML, Rezips.
        """
        if output_path is None:
            output_path = input_path

        temp_dir = tempfile.mkdtemp()
        
        try:
            # 1. Unzip
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # 2. Process Endnotes and Footnotes
            target_files = ['word/endnotes.xml', 'word/footnotes.xml']
            
            for target in target_files:
                full_path = os.path.join(temp_dir, target)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Apply stitching logic
                    new_content = self._stitch_xml_nodes(content)
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

            # 3. Re-zip
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            return True, "Links successfully preserved."

        except Exception as e:
            return False, f"Error processing links: {str(e)}"
        finally:
            shutil.rmtree(temp_dir)
