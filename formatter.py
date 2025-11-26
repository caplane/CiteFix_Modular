def _chicago_journal(data):
    """
    Formats a journal article citation in Chicago Author-Date style.
    Expected data keys: author, title, journal, volume, issue, year, pages, doi
    """
    # 1. Author (Last, First M.)
    author = data.get("author", "Unknown Author")
    if not author.endswith("."):
        author += "."

    # 2. Year
    year = data.get("year", "n.d.")

    # 3. Article Title (in quotes)
    title = data.get("title", "Untitled")
    if not title.endswith(".") and not title.endswith("?"):
        title += "."
    
    # 4. Journal Name (Italicized logic handled by Markdown or HTML usually, keeping plain text here)
    journal = data.get("journal", "Unknown Journal")
    
    # 5. Volume, Issue, Pages
    volume = data.get("volume", "")
    issue = data.get("issue", "")
    pages = data.get("pages", "")
    
    # Constructing the citation parts
    citation = f"{author} {year}. \"{title}\" {journal} {volume}"
    
    if issue:
        citation += f", no. {issue}"
        
    if pages:
        citation += f": {pages}"
        
    citation += "."
    
    # Add DOI or URL if present
    if data.get("doi"):
        citation += f" https://doi.org/{data['doi']}."
    elif data.get("url"):
        citation += f" {data['url']}."
        
    return citation

def format_citation(data, style="chicago"):
    """
    Public interface to format citations.
    """
    if style.lower() == "chicago":
        # logic to determine if it's a journal, book, etc.
        # For now, defaulting to journal based on your error logs
        return _chicago_journal(data)
    
    return "Style not supported."
