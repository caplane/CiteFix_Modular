@staticmethod
    def _chicago_journal(data):
        # Format: Author, "Title," Journal Vol, no. Issue (Year): Pages.
        parts = []
        
        # 1. Authors
        authors = data.get('authors', [])
        if authors:
            if len(authors) == 1: parts.append(authors[0])
            elif len(authors) == 2: parts.append(f"{authors[0]} and {authors[1]}")
            elif len(authors) > 2: parts.append(f"{authors[0]} et al.")
        
        # 2. Title (quoted)
        title = data.get('title', 'Unknown Title')
        parts.append(f'"{title}"')
        
        # 3. Journal Details
        journal = data.get('journal', '')
        vol = data.get('volume', '')
        issue = data.get('issue', '')
        year = data.get('year', '')
        pages = data.get('pages', '')
        
        citation_part = ""
        if journal: citation_part += f"<i>{journal}</i>"
        if vol: citation_part += f" {vol}"
        if issue: citation_part += f", no. {issue}"
        if year: citation_part += f" ({year})"
        if pages: citation_part += f": {pages}"
        
        if citation_part: parts.append(citation_part)
        
        # 4. DOI or URL (Optional but recommended for electronic sources)
        doi = data.get('doi')
        if doi: parts.append(f"https://doi.org/{doi}")
        
        return ", ".join(parts) + "."
```

### **Step 3: Update `search.py`**
We need to wire the new engine into the router so it actually gets used.

**Action:** Update `resolve_single_segment` in `search.py`.
