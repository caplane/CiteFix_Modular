
"""
The Style Engine (formatter.py)
Acts as the 'Stylist'.
- Takes RAW DATA from any engine.
- Arranges it according to style rules (CMS, etc.).
"""

class CitationFormatter:
    
    @staticmethod
    def format(metadata, style='chicago'):
        source_type = metadata.get('type')
        
        # ROUTE TO CORRECT STYLE FUNCTION
        if style == 'chicago':
            if source_type == 'government':
                return CitationFormatter._chicago_gov(metadata)
            elif source_type == 'book':
                return CitationFormatter._chicago_book(metadata)
            else:
                return metadata.get('raw_source')
        
        # Placeholder for future styles (APA, MLA)
        return metadata.get('raw_source')

    # ==================== CHICAGO RULES ====================

    @staticmethod
    def _chicago_gov(data):
        # Format: Agency. "Title." Accessed Date. URL.
        agency = data.get('author')
        title = data.get('title')
        date = data.get('access_date')
        url = data.get('url')
        
        return f'{agency}. "{title}." Accessed {date}. {url}.'

    @staticmethod
    def _chicago_book(data):
        # Format: Author. Title (Italic). (Place: Publisher, Year).
        parts = []
        
        # Authors
        authors = data.get('authors', [])
        if authors:
            if len(authors) == 1:
                parts.append(authors[0])
            elif len(authors) == 2:
                parts.append(f"{authors[0]} and {authors[1]}")
            else:
                parts.append(f"{authors[0]} et al.")
        
        # Title (Italicized HTML)
        title = data.get('title')
        if title:
            parts.append(f"<i>{title}</i>")
        
        # Publication Info
        pub_info = []
        if data.get('place'): pub_info.append(data.get('place'))
        if data.get('publisher'): pub_info.append(data.get('publisher'))
        if data.get('year'): pub_info.append(data.get('year'))
        
        if pub_info:
            parts.append("(" + ", ".join(pub_info) + ")")
        
        return ". ".join(parts) + "."

