import re
from datetime import datetime

def is_interview_citation(text):
    triggers = ['interview', 'oral history', 'personal communication', 'conversation with']
    return any(t in text.lower() for t in triggers)

def extract_metadata(text):
    clean_text = text.strip()
    metadata = {
        'type': 'interview',
        'raw_source': text,
        'interviewee': '',
        'interviewer': '',
        'title': '',
        'date': '',
        'medium': 'Personal interview'
    }

    # 1. SMART DATE EXTRACTION
    # Handles: 11/27/1981 -> November 27, 1981
    slash_date = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', clean_text)
    word_date = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}', clean_text, re.IGNORECASE)

    if slash_date:
        try:
            dt = datetime.strptime(slash_date.group(0).replace('-', '/'), "%m/%d/%Y")
            metadata['date'] = dt.strftime("%B %d, %Y")
        except:
            metadata['date'] = slash_date.group(0)
    elif word_date:
        metadata['date'] = word_date.group(0).title()
    else:
        year_match = re.search(r'\b(19|20)\d{2}\b', clean_text)
        if year_match: metadata['date'] = year_match.group(0)

    # 2. INTERVIEWER & INTERVIEWEE EXTRACTION
    # Pattern: "Kevin Smith interview with William Dolan"
    # Group 1 = Interviewer (Kevin Smith), Group 2 = Interviewee (William Dolan)
    complex_match = re.search(r'^([^,]+?)\s+interview\s+with\s+([^,]+)', clean_text, re.IGNORECASE)
    
    # Pattern: "Interview with William Dolan by Kevin Smith"
    by_match = re.search(r'interview with\s+([^,]+?)\s+by\s+([^,]+)', clean_text, re.IGNORECASE)

    if complex_match:
        metadata['interviewer'] = complex_match.group(1).strip().title()
        metadata['interviewee'] = complex_match.group(2).strip().title()
    elif by_match:
        metadata['interviewee'] = by_match.group(1).strip().title()
        metadata['interviewer'] = by_match.group(2).strip().title()
    else:
        # Fallback: Look for "Interview with X"
        simple_match = re.search(r'interview with\s+([^,]+)', clean_text, re.IGNORECASE)
        if simple_match:
            metadata['interviewee'] = simple_match.group(1).strip().title()
        else:
            # Last Resort: Assume start of line is interviewee
            parts = re.split(r'\binterview\b', clean_text, flags=re.IGNORECASE)
            if parts: metadata['interviewee'] = parts[0].strip().title()

    return metadata
