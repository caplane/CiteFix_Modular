\"""
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

    # ==================== CHICAGO RULES (NOTE STYLE) ====================

    @staticmethod
    def _chicago_gov(data):
        # Format: Agency, "Title," accessed Date, URL.
        agency = data.get('author')
        title = data.get('title')
        date = data.get('access_date')
        url = data.get('url')
        
        # Note style uses commas
        return f'{agency}, "{title}," accessed {date}, {url}.'

    @staticmethod
    def _chicago_book(data):
        # Format: Author, Title (Place: Publisher, Year).
        parts = []
        
        # 1. Authors
        authors = data.get('authors', [])
        if authors:
            if len(authors) == 1:
                parts.append(authors[0])
            elif len(authors) == 2:
                parts.append(f"{authors[0]} and {authors[1]}")
            else:
                parts.append(f"{authors[0]} et al.")
        
        # 2. Title (Italicized HTML)
        title = data.get('title')
        if title:
            parts.append(f"<i>{title}</i>")
        
        # 3. Publication Info: (Place: Publisher, Year)
        # We need to build the string inside the parentheses carefully
        pub_str = ""
        place = data.get('place')
        publisher = data.get('publisher')
        year = data.get('year')

        if place:
            pub_str += place
        
        if publisher:
            if place:
                pub_str += f": {publisher}" # Colon after place
            else:
                pub_str += publisher
        
        if year:
            if place or publisher:
                pub_str += f", {year}" # Comma before year
            else:
                pub_str += year
        
        if pub_str:
            parts.append(f"({pub_str})")
        
        # Join main parts with COMMAS, not periods
        return ", ".join(parts) + "."
