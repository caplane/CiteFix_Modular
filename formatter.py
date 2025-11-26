class CitationFormatter:
    
    @staticmethod
    def format(metadata, style='chicago'):
        source_type = metadata.get('type')
        
        if style == 'chicago':
            if source_type == 'government':
                return CitationFormatter._chicago_gov(metadata)
            elif source_type == 'book':
                return CitationFormatter._chicago_book(metadata)
            elif source_type == 'newspaper':
                return CitationFormatter._chicago_newspaper(metadata)
            elif source_type == 'legal':
                return CitationFormatter._chicago_legal(metadata)
            elif source_type == 'journal':
                return CitationFormatter._chicago_journal(metadata)
            else:
                return metadata.get('raw_source', '')
        
        return metadata.get('raw_source', '')

    # ==================== CHICAGO RULES ====================

    @staticmethod
    def _chicago_gov(data):
        agency = data.get('author', '')
        title = data.get('title', '')
        date = data.get('access_date', '')
        url = data.get('url', '')
        return f'{agency}, "{title}," accessed {date}, {url}.'

    @staticmethod
    def _chicago_book(data):
        parts = []
        authors = data.get('authors', [])
        if authors:
            if len(authors) == 1: parts.append(authors[0])
            elif len(authors) == 2: parts.append(f"{authors[0]} and {authors[1]}")
            else: parts.append(f"{authors[0]} et al.")
        
        title = data.get('title')
        if title: parts.append(f"<i>{title}</i>")
        
        pub_str = ""
        place = data.get('place')
        publisher = data.get('publisher')
        year = data.get('year')

        if place: pub_str += place
        if publisher:
            if place: pub_str += f": {publisher}"
            else: pub_str += publisher
        if year:
            if place or publisher: pub_str += f", {year}"
            else: pub_str += year
        
        if pub_str: parts.append(f"({pub_str})")
        
        return ", ".join(parts) + "."

    @staticmethod
    def _chicago_newspaper(data):
        parts = []
        
        if data.get('author'):
            parts.append(data['author'])
            
        title = data.get('title', 'Unknown Title')
        parts.append(f'"{title}"')
        
        newspaper = data.get('newspaper')
        if newspaper:
            parts.append(f"<i>{newspaper}</i>")
            
        date = data.get('date')
        if date:
            parts.append(date)
            
        url = data.get('url')
        if url:
            parts.append(url)
            
        return ", ".join(parts) + "."

    @staticmethod
    def _chicago_legal(data):
        """
        Chicago legal citation format (per CMOS 14.276-14.283).
        Format: Case Name, Volume Reporter Page (Year).
        """
        case_name = data.get('case_name', '')
        citation = data.get('citation', '')
        court = data.get('court', '')
        year = data.get('year', '')
        
        result = ""
        
        # 1. Case Name (Italicized)
        if case_name:
            result = f"<i>{case_name}</i>"
        
        # 2. Citation (Volume Reporter Page)
        if citation:
            if result:
                result += ", " + citation
            else:
                result = citation
        
        # 3. Parenthetical (Court & Year)
        # Logic: Supreme Court (U.S.) gets just year; others get court + year
        if year:
            if citation and 'U.S.' in citation:
                # Supreme Court: (1973)
                result += f" ({year})"
            elif court:
                # Lower Court: (2d Cir. 1947)
                result += f" ({court} {year})"
            else:
                # Fallback: (1973)
                result += f" ({year})"
        
        # 4. Final Punctuation
        if result:
            result += "."
        else:
            result = data.get('raw_source', '')
        
        return result

    @staticmethod
    def _chicago_journal(data):
        """
        Format: Author, "Title," Journal Vol, no. Issue (Year): Pages.
        """
        parts = []
        
        # 1. Authors
        authors = data.get('authors', [])
        if authors:
            if len(authors) == 1: parts.append(authors[0])
            elif len(authors) == 2: parts.append(f"{authors[0]} and {authors[1]}")
            else: parts.append(f"{authors[0]} et al.")
        
        # 2. Title (Quoted)
        title = data.get('title')
        if title: parts.append(f'"{title}"')
        
        # 3. Journal Details
        # "JournalName Vol, no. Issue (Year): Pages"
        journal_str = ""
        
        journal_name = data.get('journal')
        if journal_name: journal_str += f"<i>{journal_name}</i>"
        
        vol = data.get('volume')
        if vol: journal_str += f" {vol}"
        
        issue = data.get('issue')
        if issue: journal_str += f", no. {issue}"
        
        year = data.get('year')
        if year: journal_str += f" ({year})"
        
        pages = data.get('pages')
        if pages: journal_str += f": {pages}"
        
        if journal_str: parts.append(journal_str)
        
        # 4. DOI / URL (Chicago prefers DOI)
        doi = data.get('doi')
        url = data.get('url')
        
        if doi:
            parts.append(f"https://doi.org/{doi}")
        elif url:
            parts.append(url)
            
        return ", ".join(parts) + "."
