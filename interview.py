import re
from datetime import datetime

def is_interview_citation(text):
    """Detects if text looks like an interview citation."""
    triggers = ['interview', 'oral history', 'personal communication', 'conversation with']
    clean = text.lower()
    return any(t in clean for t in triggers)

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

    # 1. Try to find Date
    date_match = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', clean_text, re.IGNORECASE)
    if date_match:
        metadata['date'] = date_match.group(0)
    else:
        # Try finding just a year
        year_match = re.search(r'\b(19|20)\d{2}\b', clean_text)
        if year_match: metadata['date'] = year_match.group(0)

    # 2. Try to identify Interviewee vs Interviewer
    # Pattern: "Interview with [Person A] by [Person B]"
    with_match = re.search(r'interview with ([^,]+)', clean_text, re.IGNORECASE)
    if with_match:
        metadata['interviewee'] = with_match.group(1).strip()
        
    by_match = re.search(r'by ([^,(\.]+)', clean_text, re.IGNORECASE)
    if by_match:
        metadata['interviewer'] = by_match.group(1).strip()

    # Fallback: If starts with Name, assume Interviewee
    if not metadata['interviewee']:
        # Split by comma or "interview"
        parts = re.split(r',|interview', clean_text, flags=re.IGNORECASE)
        if parts:
            metadata['interviewee'] = parts[0].strip()

    return metadata
