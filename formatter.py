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
        Chicago legal citation format (per CMOS 14.276-14.283):
        Case Name, Volume Reporter Page (Court Year).
        
        Examples:
            Loving v. Virginia, 388 U.S. 1 (1967).
            Roe v. Wade, 410 U.S. 113 (1973).
            Brown v. Board of Education, 347 U.S. 483 (1954).
        
        Note: For U.S. Supreme Court cases, the court name is typically
        omitted since the U.S. Reports (U.S.) implies the Supreme Court.
        """
        case_name = data.get('case_name', '')
        citation = data.get('citation', '')
        court = data.get('court', '')
        year = data.get('year', '')
        
        parts = []
        
        # Case name (italicized in formal Chicago, but we use plain text here)
        if case_name:
            parts.append(case_name)
        
        # Reporter citation (e.g., "388 U.S. 1")
        if citation:
            parts.append(citation)
        
        # Court and year in parentheses
        # For Supreme Court (indicated by "U.S." reporter), omit court name
        if year:
            if court and 'U.S.' not in citation:
                parts.append(f"({court} {year})")
            else:
                parts.append(f"({year})")
        
        return ", ".join(parts) + "."
