import re
from datetime import datetime

# ==================== LOGIC: DATE PARSING ====================
def parse_date(text):
    """
    Attempts to find a date in the string.
    Returns (formatted_date, original_string_segment)
    """
    # Regex for standard dates: Month Day, Year OR Month Day
    # Examples: "May 3, 2024", "Jan 12", "October 5th"
    date_pattern = r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,?\s+\d{4})?'
    match = re.search(date_pattern, text, re.IGNORECASE)
    
    if match:
        found_date = match.group(0)
        
        # If no year is present (e.g., just "May 3"), add a placeholder
        if not re.search(r'\d{4}', found_date):
            found_date += ", [Year?]"
            
        return found_date, match.group(0)
        
    return None, None

# ==================== LOGIC: EXTRACTION ====================
def extract_metadata(text):
    clean_text = text.strip()
    
    # Default Values
    data = {
        'subject': 'Unknown Subject',
        'interviewer': 'author', # Default rule
        'location': '',
        'date': '',
        'raw_source': text
    }

    # 1. EXTRACT DATE (and remove it from text)
    found_date, date_str = parse_date(clean_text)
    if found_date:
        data['date'] = found_date
        clean_text = clean_text.replace(date_str, '')

    # 2. IDENTIFY INTERVIEWER ("BY [Name]")
    # If the text says "by John Doe", we update the interviewer
    by_match = re.search(r'\bby\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', clean_text)
    if by_match:
        data['interviewer'] = by_match.group(1)
        clean_text = clean_text.replace(by_match.group(0), '')

    # 3. IDENTIFY SUBJECT ("WITH [Name]" or "OF [Name]")
    # Most common case: "Interview with Phil Hirschkop"
    subject_match = re.search(r'\b(with|of)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', clean_text, re.IGNORECASE)
    if subject_match:
        data['subject'] = subject_match.group(2)
        clean_text = clean_text.replace(subject_match.group(0), '')
    else:
        # Fallback: If no "with/of", look for the first capitalized name at the start
        fallback_name = re.search(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', clean_text)
        if fallback_name:
            data['subject'] = fallback_name.group(1)
            clean_text = clean_text.replace(fallback_name.group(0), '')

    # 4. IDENTIFY LOCATION (The Leftovers)
    # Remove keywords like "interview", "in", "at", and punctuation
    cleanup_pattern = r'\b(interview|in|at)\b'
    location_text = re.sub(cleanup_pattern, '', clean_text, flags=re.IGNORECASE)
    location_text = re.sub(r'[,;]', ' ', location_text).strip()
    
    # Remove multiple spaces
    location_text = " ".join(location_text.split())
    
    if location_text:
        data['location'] = location_text

    return {
        'type': 'interview',
        'subject': data['subject'],
        'interviewer': data['interviewer'],
        'location': data['location'],
        'date': data['date'],
        'raw_source': text
    }

# ==================== LOGIC: FORMATTING ====================

def format_citation(metadata):
    """
    Constructs the Chicago Style citation:
    Format: Subject, interview by Interviewer, Location, Date.
    """
    subject = metadata.get('subject', 'Unknown')
    interviewer = metadata.get('interviewer', 'author')
    location = metadata.get('location', '')
    date = metadata.get('date', '')
    
    # Formatting Rule: "interview by author" vs "interview by John Doe"
    interviewer_str = "interview by author"
    if interviewer.lower() != 'author':
        interviewer_str = f"interview by {interviewer}"
    
    # Build the string parts
    parts = [subject, interviewer_str]
    
    if location: 
        parts.append(location)
    if date: 
        parts.append(date)
    
    return ", ".join(parts) + "."
