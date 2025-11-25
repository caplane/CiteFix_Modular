class CitationFormatter:
    
    @staticmethod
    def format(metadata, style='chicago'):
        source_type = metadata.get('type')
        
        if style == 'chicago':
            if source_type == 'government':
                return CitationFormatter._chicago_gov(metadata)
            elif source_type == 'book':
                return CitationFormatter._chicago_book(metadata)
            elif source_type == 'newspaper': # CRITICAL CHECK
                return CitationFormatter._chicago_newspaper(metadata)
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
