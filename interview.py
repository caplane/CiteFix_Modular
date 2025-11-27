import re
from datetime import datetime

# ==================== DATE FORMAT MAP ====================
# The system will try these formats in order until one works.
DATE_FORMATS = [
    "%B %d, %Y",    # January 1, 2020
    "%b %d, %Y",    # Jan 1, 2020
    "%m/%d/%Y",     # 11/27/1981
    "%m-%d-%Y",     # 11-27-1981
    "%Y-%m-%d",     # 1981-11-27 (ISO)
    "%d %B %Y",     # 1 January 2020 (Euro)
    "%d %b %Y",     # 1 Jan 2020 (Euro short)
    "%B %Y",        # January 1981 (Partial)
    "%Y"            # 1981 (Year only)
]

def is_interview_citation(text):
    triggers = ['interview', 'oral history', 'personal communication', 'conversation with']
    return any(t in text.lower() for t in triggers)

def clean_ordinal_date(text):
    """Removes st, nd, rd, th from dates (May 7th -> May 7) for parsing."""
    return re.sub(r'(?<=\d)(st|nd|rd|th)\b', '', text)

def try_parse_date(date_string):
    """Loops through the DATE_FORMATS map to find a match."""
    clean = clean_ordinal_date(date_string.strip())
    # Fix: Ensure periods in abbreviations don't break parsing (Jan. -> Jan)
    clean = clean.replace('.', '') 
    
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(clean, fmt)
            # Return in the standard Chicago format
            return dt.strftime("%B %d, %Y")
        except ValueError:
            continue
    return date_string # Return original if all parses fail

def extract_metadata(text):
    clean_text = text.strip()
    metadata = {
        'type': 'interview',
        'raw_source': text,
        'interviewee': 'Unknown',
        'interviewer': 'author',
        'title': '',
        'date': '',
        'location': '',
        'medium': 'Personal interview'
    }

    # 1. ROBUST DATE EXTRACTION
    # We use a broad regex to grab the "Candidate String", then pass it to the parser map.
    
    # Pattern A: Numeric (11/27/1981 or 1981-11-27)
    numeric_match = re.search(r'\b\d{1,4}[/-]\d{1,2}[/-]\d{2,4}\b', clean_text)
    
    # Pattern B: Written (Jan 1, 2020 or 1 Jan 2020)
    # Matches: Month (3+ letters), optional dot, space, day, comma?, space, year
    written_match = re.search(
        r'\b(?:[A-Z][a-z]{2,}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})|(?:\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]{2,}\.?\s+\d{4})\b', 
        clean_text, 
        re.IGNORECASE
    )
    
    # Pattern C: Year Only fallback
    year_match = re.search(r'\b(19|20)\d{2}\b', clean_text)

    date_end_index = len(clean_text)

    if numeric_match:
        metadata['date'] = try_parse_date(numeric_match.group(0))
        date_end_index = numeric_match.end()
    elif written_match:
        metadata['date'] = try_parse_date(written_match.group(0))
        date_end_index = written_match.end()
    elif year_match:
        metadata['date'] = year_match.group(0)
        date_end_index = year_match.end()

    # 2. LOCATION EXTRACTION
    # Grab everything after the date, strip punctuation
    potential_location = clean_text[date_end_index:].strip().strip('.,;')
    
    if potential_location:
        if ',' in potential_location:
            parts = potential_location.split(',', 1)
            city = parts[0].strip().title()
            state_raw = parts[1].strip()
            
            # Logic: If state is exactly 2 letters, UPPERCASE it.
            clean_letters = state_raw.replace('.', '')
            
            if len(clean_letters) == 2:
                state = state_raw.upper()
            else:
                state = state_raw.title()
            
            metadata['location'] = f"{city}, {state}"
        else:
            metadata['location'] = potential_location.title()

    # 3. INTERVIEWER & INTERVIEWEE EXTRACTION
    complex_match = re.search(r'^([^,]+?)\s+interview\s+with\s+([^,]+)', clean_text, re.IGNORECASE)
    by_match = re.search(r'interview with\s+([^,]+?)\s+by\s+([^,]+)', clean_text, re.IGNORECASE)

    if complex_match:
        metadata['interviewer'] = complex_match.group(1).strip().title()
        metadata['interviewee'] = complex_match.group(2).strip().title()
    elif by_match:
        metadata['interviewee'] = by_match.group(1).strip().title()
        metadata['interviewer'] = by_match.group(2).strip().title()
    else:
        simple_match = re.search(r'interview with\s+([^,]+)', clean_text, re.IGNORECASE)
        if simple_match:
            metadata['interviewee'] = simple_match.group(1).strip().title()
        else:
            # Last Resort
            parts = re.split(r'\binterview\b', clean_text, flags=re.IGNORECASE)
            if parts: 
                raw_name = parts[0].strip().title()
                metadata['interviewee'] = raw_name.rstrip(',')

    return metadata
