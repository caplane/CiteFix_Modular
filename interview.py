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
        'interviewee': 'Unknown',
        'interviewer': 'author',
        'title': '',
        'date': '',
        'location': '', 
        'medium': 'Personal interview'
    }

    # 1. SMART DATE EXTRACTION
    slash_date = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', clean_text)
    word_date = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}', clean_text, re.IGNORECASE)

    # Track where the date ends so we can look for location afterwards
    date_end_index = len(clean_text)

    if slash_date:
        try:
            dt = datetime.strptime(slash_date.group(0).replace('-', '/'), "%m/%d/%Y")
            metadata['date'] = dt.strftime("%B %d, %Y")
        except:
            metadata['date'] = slash_date.group(0)
        date_end_index = slash_date.end()
        
    elif word_date:
        metadata['date'] = word_date.group(0).title()
        date_end_index = word_date.end()
    else:
        year_match = re.search(r'\b(19|20)\d{2}\b', clean_text)
        if year_match: 
            metadata['date'] = year_match.group(0)
            date_end_index = year_match.end()

    # 2. LOCATION EXTRACTION (Improved State Handling)
    # Grab everything after the date, strip punctuation
    potential_location = clean_text[date_end_index:].strip().strip('.,;')
    
    if potential_location:
        # Handle "austin, tx" -> "Austin, TX"
        if ',' in potential_location:
            parts = potential_location.split(',', 1)
            city = parts[0].strip().title()
            state_raw = parts[1].strip()
            
            # Logic: If it has exactly 2 letters (ignoring dots), it's an abbreviation -> UPPERCASE
            # "tx" -> "TX", "d.c." -> "D.C.", "n.y." -> "N.Y."
            # "mass." -> "Mass." (4 letters), "Ohio" -> "Ohio" (4 letters)
            clean_letters = state_raw.replace('.', '')
            
            if len(clean_letters) == 2:
                state = state_raw.upper()
            else:
                state = state_raw.title()
            
            metadata['location'] = f"{city}, {state}"
        else:
            # Fallback for single words
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
            parts = re.split(r'\binterview\b', clean_text, flags=re.IGNORECASE)
            if parts: 
                raw_name = parts[0].strip().title()
                metadata['interviewee'] = raw_name.rstrip(',')

    return metadata
