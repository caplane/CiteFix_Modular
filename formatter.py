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
        
        Format: Case Name, Volume Reporter Page (Year).
        
        Examples:
            Plessy v. Ferguson, 163 U.S. 537 (1896).
            Loving v. Virginia, 388 U.S. 1 (1967).
            Roe v. Wade, 410 U.S. 113 (1973).
            Brown v. Board of Education, 347 U.S. 483 (1954).
        
        Note: For U.S. Supreme Court cases, the court name is typically
        omitted since the U.S. Reports (U.S.) implies the Supreme Court.
        For lower courts, include court abbreviation: (5th Cir. 2020).
        """
        case_name = data.get('case_name', '')
        citation = data.get('citation', '')
        court = data.get('court', '')
        year = data.get('year', '')
        
        # Build citation string
        # Format: Case Name, Citation (Year).
        # NOT: Case Name, Citation, (Year).  <-- no comma before parenthetical
        
        result = ""
        
        if case_name:
            result = case_name
        
        if citation:
            if result:
                result += ", " + citation
            else:
                result = citation
        
        # Year in parentheses (no comma before)
        # For Supreme Court (U.S. reporter), omit court name
        # For other courts, include court abbreviation
        if year:
            if citation and 'U.S.' in citation:
                # Supreme Court - just year
                result += f" ({year})"
            elif court:
                # Lower court - include court name
                result += f" ({court} {year})"
            else:
                # No court info - just year
                result += f" ({year})"
        
        # Add final period
        if result:
            result += "."
        else:
            # Fallback if nothing extracted
            result = data.get('raw_source', '')
        
        return result
