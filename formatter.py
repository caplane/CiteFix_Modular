def _chicago_journal(data):
    """
    Formats a journal article citation in Chicago Author-Date style.
    """
    author = data.get("author", "Unknown Author")
    if not author.endswith("."):
        author += "."

    year = data.get("year", "n.d.")
    
    title = data.get("title", "Untitled")
    if not title.endswith(".") and not title.endswith("?"):
        title += "."
    
    journal = data.get("journal", "Unknown Journal")
    volume = data.get("volume", "")
    issue = data.get("issue", "")
    pages = data.get("pages", "")
    
    citation = f"{author} {year}. \"{title}\" {journal} {volume}"
    
    if issue:
        citation += f", no. {issue}"
    if pages:
        citation += f": {pages}"
        
    citation += "."
    
    if data.get("doi"):
        citation += f" https://doi.org/{data['doi']}."
    elif data.get("url"):
        citation += f" {data['url']}."
        
    return citation

def _format_legal_case(data):
    """
    Formats a legal case (Bluebook/Chicago style).
    Expected keys from court.py: case_name (or plaintiff/defendant), volume, reporter, page, court, year
    """
    # 1. Case Name (italicized in formatted text, plain here)
    case_name = data.get("case_name")
    if not case_name:
        # Fallback if separate plaintiff/defendant keys exist
        p = data.get("plaintiff", "Plaintiff")
        d = data.get("defendant", "Defendant")
        case_name = f"{p} v. {d}"

    # 2. Reporter Info
    volume = data.get("volume", "")
    reporter = data.get("reporter", "")
    page = data.get("page", "")
    
    # 3. Court and Year
    court = data.get("court", "")
    year = data.get("year", "")
    
    # Construct: Case Name, Vol Reporter Page (Court Year).
    # Example:  Osheroff v. Chestnut Lodge, 490 A.2d 720 (Md. Ct. Spec. App. 1985).
    
    citation = f"{case_name}, {volume} {reporter} {page}"
    
    # Only add parens if we have court or year info
    if court or year:
        citation += f" ({court} {year})"
        
    citation += "."
    
    if data.get("url"):
        citation += f" {data['url']}."

    return citation

def format_citation(data, style="chicago"):
    """
    Public interface. Automatically detects if the input is a legal case or journal article.
    """
    # DETECT TYPE: Check for keys specific to legal cases
    is_legal_case = (
        data.get("type") == "case" or 
        "reporter" in data or 
        "plaintiff" in data or
        "case_name" in data
    )

    if is_legal_case:
        return _format_legal_case(data)
    else:
        # Default to journal for everything else
        return _chicago_journal(data)
