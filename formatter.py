import re
import os
import zipfile
import shutil
import tempfile

class CitationFormatter:
    """
    HANDLES STRING FORMATTING:
    Converts metadata dictionaries into styled citation strings 
    (Chicago, Bluebook, OSCOLA, APA, MLA).
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
        # Author, "Title," Journal Vol, no. Issue (Year): Pages.
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
        
        # FIX: Ensure URL is joined cleanly, allowing regex to detect it later
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
        # Case Name, Vol Rep Page (Court Year).
        citation = data.get('citation', '')
        case_name = f"<i>{data.get('case_name', '')}</i>"
        court_year = f"({data.get('court', '')} {data.get('year', '')})".replace('  ', ' ')
        if citation: return f"{case_name}, {citation} {court_year}."
        return f"{case_name} {court_year}."

    @staticmethod
    def _chicago_gov(data):
        # FIX: Prevent the "Trailing Period" bug.
        # We build the base citation first, then append the URL, then append the period outside the URL.
        parts = []
        parts.append(f"{data.get('author', 'U.S. Gov')}")
        parts.append(f"\"{data.get('title')}\"")
        parts.append(f"accessed {data.get('access_date')}")
        
        base_cit = ", ".join(parts)
        
        url = data.get('url')
        if url:
            # Return "Base, URL." (Dot is separate)
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

    # ==================== 2. BLUEBOOK (US Legal) ====================

    @staticmethod
    def _bluebook_legal(data):
        # Case Name, Vol Rep Page (Court Year). 
        # Note: Bluebook standard technically does NOT italicize case names in footnotes 
        # unless grammatically part of the sentence, but practitioner standard often does. 
        # We will use italics for clarity as it's safer.
        citation = data.get('citation', '')
        case_name = f"<i>{data.get('case_name', '')}</i>"
        
        court = data.get('court', '')
        # Special logic: If SCOTUS (U.S. report), court name is omitted from parenthetical
        if 'U.S.' in citation and not court: court = '' 
        
        parenthetical = f"({court} {data.get('year', '')})".replace('  ', ' ').replace('()', '')
        
        if citation: return f"{case_name}, {citation} {parenthetical}."
        return f"{case_name} {parenthetical}."

    @staticmethod
    def _bluebook_journal(data):
        # Author, Title, Vol Journal Page (Year).
        # Journal name is Small Caps in Bluebook. We use italics here for web compatibility.
        author = CitationFormatter._format_authors(data.get('authors', []), 'bluebook')
        title = f"<i>{data.get('title', '')}</i>"
        journal = f"{data.get('journal', '')}" 
        return f"{author}, {title}, {data.get('volume', '')} {journal} {data.get('pages', '')} ({data.get('year', '')})."

    @staticmethod
    def _bluebook_book(data):
        # Author, Title (Year).
        # Title is Small Caps. We use ALL CAPS to mimic this.
        author = CitationFormatter._format_authors(data.get('authors', []), 'bluebook')
        title = data.get('title', '').upper()
        return f"{author}, {title} ({data.get('year', '')})."

    # ==================== 3. OSCOLA (UK Legal) ====================

    @staticmethod
    def _oscola_legal(data):
        # Case Name [Year] OR (Year) Vol Report Page (Court).
        # OSCOLA: Italics for name, no punctuation after name.
        case_name = f"<i>{data.get('case_name', '')}</i>"
        citation = data.get('citation', '')
        court = data.get('court', '')
        year = data.get('year', '')

        # Heuristic: If citation has brackets [], it's neutral/year-based. If not, use parens ().
        year_str = f"({year})" if year else ""
        
        return f"{case_name} {year_str} {citation} ({court})"

    @staticmethod
    def _oscola_journal(data):
        # Author, 'Title' (Year) Vol Journal Page.
        # Note: Single quotes for title, no "p" or "pp" for pages.
        author = CitationFormatter._format_authors(data.get('authors', []), 'oscola')
        title = f"'{data.get('title', '')}'"
        return f"{author}, {title} ({data.get('year', '')}) {data.get('volume', '')} {data.get('journal', '')} {data.get('pages', '')}."

    @staticmethod
    def _oscola_book(data):
        # Author, Title (Publisher Year).
        author = CitationFormatter._format_authors(data.get('authors', []), 'oscola')
        title = f"<i>{data.get('title', '')}</i>"
        pub_info = f"({data.get('publisher', '')} {data.get('year', '')})".replace('  ', ' ')
        return f"{author}, {title} {pub_info}."

    # ==================== 4. APA (Psychology) ====================

    @staticmethod
    def _apa_journal(data):
        # Author, A. A. (Year). Title. Journal, Vol(Issue), Page.
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
        # Author, A. A. (Year). Title. Publisher.
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
        # Author. "Title." Journal, vol. X, no. X, Year, pp. X-X.
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
        # Author. Title. Publisher, Year.
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
    HANDLES FILE MANIPULATION (The 'Genie' Logic):
    1. Stitches broken URLs that span multiple lines (fixing 'management- plan').
    2. 'Auto-Linkifies' plain text URLs using Word Field Codes (HYPERLINK),
       so they are clickable even if the input text was just black text.
    """

    def __init__(self):
        # Regex to find URLs split by hyphen+newline (Fixes "...management- plan")
        self.url_split_pattern = r'(https?://[^\s<>"]+)-\s+([^\s<>"]+)'
        
        # Regex to find URLs split by simple whitespace (Fixes "...epa .gov")
        self.url_break_pattern = r'(https?://[^\s<>"]+)\s+(\/[^\s<>"]+)'

    def clean_text_content(self, text):
        """Stitches broken text URLs back together."""
        text = re.sub(self.url_split_pattern, r'\1\2', text)
        text = re.sub(self.url_break_pattern, r'\1\2', text)
        return text

    def _generate_hyperlink_xml(self, url, text_content):
        """
        Creates a 'w:fldSimple' XML block.
        This forces Word to treat the text as a live HYPERLINK field 
        without needing complex relationship definitions in other XML files.
        """
        # XML escape the URL for the instruction attribute
        safe_url = url.replace('"', '&quot;')
        
        # We construct the raw XML for a Word field code
        xml = (
            f'<w:fldSimple w:instr=" HYPERLINK &quot;{safe_url}&quot; ">'
            f'<w:r>'
            f'<w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>'  # Makes it Blue/Underlined
            f'<w:t>{text_content}</w:t>'
            f'</w:r>'
            f'</w:fldSimple>'
        )
        return xml

    def _stitch_and_linkify(self, xml_content):
        """
        Scans Endnotes/Footnotes/Body XML.
        1. Stitches split text nodes.
        2. Detects URLs.
        3. Wraps URLs in Hyperlink Field Codes.
        """
        # Pattern to catch paragraphs <w:p> and notes <w:endnote/footnote>
        block_pattern = r'(<(?:w:p|w:endnote|w:footnote)[^>]*>)(.*?)(</(?:w:p|w:endnote|w:footnote)>)'
        
        def replace_block(match):
            open_tag, inner_xml, close_tag = match.groups()

            # 1. Extract text nodes
            text_node_pattern = r'(<w:t[^>]*>)([^<]+)(</w:t>)'
            text_matches = list(re.finditer(text_node_pattern, inner_xml))
            if not text_matches: return match.group(0)

            # 2. Join all text to fix the split (Stitching)
            full_text = "".join([m.group(2) for m in text_matches])
            cleaned_text = self.clean_text_content(full_text)

            # 3. Check if the RESULTING text contains a URL
            # We look for http... and capture it, separating trailing punctuation ([.,;]?)
            url_match = re.search(r'(https?://[^\s<>"]+?)([.,;]?)$', cleaned_text)

            if url_match:
                # WE HAVE A URL! -> Upgrade to Hyperlink
                found_url = url_match.group(1)
                punctuation = url_match.group(2)
                
                # Generate the Field Code XML for the link
                link_xml = self._generate_hyperlink_xml(found_url, found_url)
                
                # Handle text BEFORE the URL (e.g. "Accessed date, ")
                pre_text = cleaned_text.replace(found_url + punctuation, "")
                
                # Reconstruct: Pre-Text + Hyperlink + Punctuation
                new_content = ""
                if pre_text:
                    new_content += f"<w:r><w:t xml:space='preserve'>{pre_text}</w:t></w:r>"
                
                new_content += link_xml
                
                if punctuation:
                    new_content += f"<w:r><w:t>{punctuation}</w:t></w:r>"

                # Return the new structure inside the block
                return f"{open_tag}{new_content}{close_tag}"

            else:
                # NO URL -> Just return the stitched text (Normal behavior)
                # This fixes the split text but leaves it as plain text if no http detected
                first_match = text_matches[0]
                new_inner = inner_xml[:first_match.start()] + \
                            f"{first_match.group(1)}{cleaned_text}{first_match.group(3)}" + \
                            inner_xml[text_matches[-1].end():]
                return f"{open_tag}{new_inner}{close_tag}"

        return re.sub(block_pattern, replace_block, xml_content, flags=re.DOTALL)

    def process_document(self, input_path, output_path=None):
        """
        Main entry point: Unzips DOCX, repairs XML, Rezips.
        """
        if output_path is None: output_path = input_path
        
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Unzip
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # 2. Process XML Files (Endnotes, Footnotes, Body)
            target_files = ['word/endnotes.xml', 'word/footnotes.xml', 'word/document.xml']
            for target in target_files:
                full_path = os.path.join(temp_dir, target)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Apply Stitching + Auto-Linking
                    new_content = self._stitch_and_linkify(content)
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

            # 3. Re-zip
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            return True, "Fixed split URLs and auto-generated live hyperlinks."

        except Exception as e:
            return False, f"Error: {str(e)}"
        finally:
            shutil.rmtree(temp_dir)
