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
        if citation: return f"{case_
