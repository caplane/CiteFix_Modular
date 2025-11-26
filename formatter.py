class CitationFormatter:
    
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
            if source_type == 'interview': return CitationFormatter._chicago_interview(metadata)

        # === BLUEBOOK (US Law) ===
        elif style == 'bluebook':
            if source_type == 'legal': return CitationFormatter._bluebook_legal(metadata)
            if source_type == 'journal': return CitationFormatter._bluebook_journal(metadata)
            if source_type == 'interview': return CitationFormatter._chicago_interview(metadata) # Bluebook defers to Chicago for interviews
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
            if source_type == 'interview': return CitationFormatter._apa_interview(metadata)
            if source_type == 'book': return CitationFormatter._apa_book(metadata)
            if source_type == 'legal': return CitationFormatter._bluebook_legal(metadata) # APA defers to Bluebook
            return CitationFormatter._apa_generic(metadata)

        # === MLA (Humanities) ===
        elif style == 'mla':
            if source_type == 'journal': return CitationFormatter._mla_journal(metadata)
            if source_type == 'interview': return CitationFormatter._mla_interview(metadata)
            if source_type == 'book': return CitationFormatter._mla_book(metadata)
            return CitationFormatter._mla_generic(metadata)
            
        # Default Fallback
        return metadata.get('raw_source', '')

    # ==================== HELPERS ====================

    @staticmethod
    def _format_authors(authors, style='chicago'):
        """Smart author formatting based on style rules."""
        if not authors: return ""
        if isinstance(authors, str): return authors
        
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

    @staticmethod
    def _chicago_interview(data):
        # Target: Joh Brown, Interview by author, May 7, 1918.
        
        parts = []
        
        # 1. Interviewee (First Last)
        interviewee = data.get('interviewee', '')
        if interviewee:
            # Check for "Last, First" and flip it to "First Last" if needed
            if ',' in interviewee:
                names = interviewee.split(',')
                interviewee = f"{names[1].strip()} {names[0].strip()}"
            parts.append(interviewee)
        
        # 2. Descriptor
        interviewer = data.get('interviewer', '')
        if interviewer:
            descriptor = f"Interview by {interviewer}"
        else:
            descriptor = "Interview by author"
            
        # Join Name and Descriptor with a COMMA
        result = f"{parts[0]}, {descriptor}" if parts else descriptor
        
        # 3. Date (Added with a COMMA)
        if data.get('date'):
            result += f", {data['date']}"
            
        return result + "."

    # ==================== 2. BLUEBOOK (US Legal) ====================

    @staticmethod
    def _bluebook_legal(data):
        # Case Name, Vol Rep Page (Court Year). 
        citation = data.get('citation', '')
        case_name = f"<i>{data.get('case_name', '')}</i>"
        
        court = data.get('court', '')
        if 'U.S.' in citation and not court: court = '' 
        
        parenthetical = f"({court} {data.get('year', '')})".replace('  ', ' ').replace('()', '')
        
        if citation: return f"{case_name}, {citation} {parenthetical}."
        return f"{case_name} {parenthetical}."

    @staticmethod
    def _bluebook_journal(data):
        # Author, Title, Vol Journal Page (Year).
        author = CitationFormatter._format_authors(data.get('authors', []), 'bluebook')
        title = f"<i>{data.get('title', '')}</i>"
        journal = f"{data.get('journal', '')}" 
        return f"{author}, {title}, {data.get('volume', '')} {journal} {data.get('pages', '')} ({data.get('year', '')})."

    @staticmethod
    def _bluebook_book(data):
        # Author, Title (Year).
        author = CitationFormatter._format_authors(data.get('authors', []), 'bluebook')
        title = data.get('title', '').upper()
        return f"{author}, {title} ({data.get('year', '')})."

    # ==================== 3. OSCOLA (UK Legal) ====================

    @staticmethod
    def _oscola_legal(data):
        # Case Name [Year] OR (Year) Vol Report Page (Court).
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
    def _apa_interview(data):
        # Author, A. (Year). Title [Interview]. Repository.
        author = CitationFormatter._format_authors([data.get('interviewee', 'Anonymous')], 'apa')
        date = f"({data.get('date', 'n.d.')})"
        title = data.get('title', 'Interview')
        bracket = "[Interview]"
        return f"{author} {date}. {title} {bracket}."

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
    def _mla_interview(data):
        # Interviewee. "Title." Interview by Interviewer. Date.
        author = CitationFormatter._format_authors([data.get('interviewee', 'Anonymous')], 'mla')
        title = f'"{data.get("title", "")}."' if data.get('title') else "Interview."
        
        parts = [author, title]
        if data.get('interviewer'): parts.append(f"Conducted by {data['interviewer']}")
        if data.get('date'): parts.append(data['date'])
        
        return ". ".join(parts) + "."

    @staticmethod
    def _mla_generic(data):
        return f"{data.get('raw_source', '')}"
