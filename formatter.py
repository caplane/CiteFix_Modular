class CitationFormatter:
    
    @staticmethod
    def format(metadata, style='chicago'):
        """
        Master Router: Dispatches the citation to the correct style engine.
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
            if source_type == 'interview': return CitationFormatter._chicago_interview(metadata) # <--- NEW

        # === BLUEBOOK (US Law) ===
        elif style == 'bluebook':
            if source_type == 'legal': return CitationFormatter._bluebook_legal(metadata)
            if source_type == 'journal': return CitationFormatter._bluebook_journal(metadata)
            if source_type == 'interview': return CitationFormatter._chicago_interview(metadata) # Bluebook defers to Chicago for interviews
            return CitationFormatter._bluebook_book(metadata)

        # === APA (Psychology/Sciences) ===
        elif style == 'apa':
            if source_type == 'journal': return CitationFormatter._apa_journal(metadata)
            if source_type == 'interview': return CitationFormatter._apa_interview(metadata) # <--- NEW
            if source_type == 'legal': return CitationFormatter._bluebook_legal(metadata)
            return CitationFormatter._apa_book(metadata)

        # === MLA (Humanities) ===
        elif style == 'mla':
            if source_type == 'journal': return CitationFormatter._mla_journal(metadata)
            if source_type == 'interview': return CitationFormatter._mla_interview(metadata) # <--- NEW
            return CitationFormatter._mla_book(metadata)
            
        # Default Fallback
        return metadata.get('raw_source', '')

    # ==================== HELPERS ====================

    @staticmethod
    def _format_authors(authors, style='chicago'):
        if not authors: return ""
        if isinstance(authors, str): return authors
        
        # Simple heuristic to split First/Last if needed
        def split_name(name):
            parts = name.split()
            return (parts[0], " ".join(parts[1:])) if len(parts) > 1 else (name, "")

        if style == 'apa':
            # APA: Last, F. M.
            formatted = []
            for name in authors:
                first, last = split_name(name)
                initial = f"{first[0]}." if first else ""
                formatted.append(f"{last}, {initial}")
            if len(formatted) > 1: return ", & ".join(formatted)
            return formatted[0]

        elif style == 'mla':
            # MLA: Last, First
            if len(authors) == 1:
                first, last = split_name(authors[0])
                return f"{last}, {first}"
            return authors[0]

        # Chicago: First Last
        if len(authors) == 1: return authors[0]
        return f"{authors[0]} et al."

    # ==================== EXISTING HANDLERS (Briefly included for context) ====================
    # (These remain the same as your previous file)
    @staticmethod
    def _chicago_journal(data):
        parts = []
        if data.get('authors'): parts.append(CitationFormatter._format_authors(data['authors'], 'chicago'))
        if data.get('title'): parts.append(f'"{data["title"]}"')
        journal_str = f"<i>{data.get('journal', '')}</i>"
        if data.get('volume'): journal_str += f" {data['volume']}"
        if data.get('year'): journal_str += f" ({data['year']})"
        if data.get('pages'): journal_str += f": {data['pages']}"
        parts.append(journal_str)
        if data.get('doi'): parts.append(f"https://doi.org/{data['doi']}")
        return ", ".join(parts) + "."

    @staticmethod
    def _chicago_book(data):
        parts = []
        if data.get('authors'): parts.append(CitationFormatter._format_authors(data['authors'], 'chicago'))
        if data.get('title'): parts.append(f"<i>{data['title']}</i>")
        pub_str = f"{data.get('publisher','')}, {data.get('year','')}"
        parts.append(f"({pub_str})")
        return ", ".join(parts) + "."

    @staticmethod
    def _chicago_legal(data):
        return f"<i>{data.get('case_name', '')}</i>, {data.get('citation', '')} ({data.get('year', '')})."
    
    @staticmethod
    def _chicago_newspaper(data):
        return f"{data.get('author','')}, \"{data.get('title','')},\" <i>{data.get('newspaper','')}</i>, {data.get('date','')}."
    
    @staticmethod
    def _chicago_gov(data):
        return f"{data.get('author', 'U.S. Gov')}, \"{data.get('title')},\" {data.get('url')}."

    # ... [Keep your Bluebook/OSCOLA handlers from previous file] ...

    # ==================== NEW INTERVIEW HANDLERS ====================

    @staticmethod
    def _chicago_interview(data):
        # Format: Interviewee, interview by Interviewer, Date, Location/Medium.
        # OR: Interviewee, "Title," interview by Interviewer, Date.
        parts = []
        
        # 1. Interviewee
        if data.get('interviewee'): 
            parts.append(data['interviewee'])
        
        # 2. Title or Descriptor
        title = data.get('title', '')
        interviewer = data.get('interviewer', '')
        
        if title:
            parts.append(f'"{title}"')
            if interviewer: parts.append(f"interview by {interviewer}")
        else:
            if interviewer: parts.append(f"interview by {interviewer}")
            else: parts.append("interview")
            
        # 3. Date & Medium
        if data.get('date'): parts.append(data['date'])
        if data.get('medium'): parts.append(data['medium'])
        
        return ", ".join(parts) + "."

    @staticmethod
    def _apa_interview(data):
        # Format: Interviewee, A. A. (Year, Month Day). [Personal communication].
        # Note: APA technically says "Personal communications are cited in text only", 
        # but for archival interviews:
        # Interviewee, A. (Year). Title [Interview]. Repository.
        author = CitationFormatter._format_authors([data.get('interviewee', 'Anonymous')], 'apa')
        date = f"({data.get('date', 'n.d.')})"
        title = data.get('title', 'Interview')
        bracket = "[Interview]"
        return f"{author} {date}. {title} {bracket}."

    @staticmethod
    def _mla_interview(data):
        # Format: Interviewee. "Title." Interview by Interviewer. Date.
        author = CitationFormatter._format_authors([data.get('interviewee', 'Anonymous')], 'mla')
        title = f'"{data.get("title", "")}."' if data.get('title') else "Interview."
        
        parts = [author, title]
        if data.get('interviewer'): parts.append(f"Conducted by {data['interviewer']}")
        if data.get('date'): parts.append(data['date'])
        
        return ". ".join(parts) + "."
