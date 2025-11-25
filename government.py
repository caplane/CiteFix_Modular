import re
import difflib  # <--- NEW: Fuzzy Matching Library
from datetime import datetime
from urllib.parse import urlparse

# ==================== DATA: AGENCY MAPS ====================

# 1. DOMAIN MAP (Fast Lookup)
GOV_AGENCY_MAP = {
    'state.gov': 'U.S. Department of State',
    'treasury.gov': 'U.S. Department of the Treasury',
    'defense.gov': 'U.S. Department of Defense',
    'justice.gov': 'U.S. Department of Justice',
    'doi.gov': 'U.S. Department of the Interior',
    'usda.gov': 'U.S. Department of Agriculture',
    'commerce.gov': 'U.S. Department of Commerce',
    'labor.gov': 'U.S. Department of Labor',
    'hhs.gov': 'U.S. Department of Health and Human Services',
    'hud.gov': 'U.S. Department of Housing and Urban Development',
    'transportation.gov': 'U.S. Department of Transportation',
    'energy.gov': 'U.S. Department of Energy',
    'doe.gov': 'U.S. Department of Energy',
    'education.gov': 'U.S. Department of Education',
    'va.gov': 'U.S. Department of Veterans Affairs',
    'dhs.gov': 'U.S. Department of Homeland Security',
    'fda.gov': 'U.S. Food and Drug Administration',
    'cdc.gov': 'Centers for Disease Control and Prevention',
    'nih.gov': 'National Institutes of Health',
    'epa.gov': 'Environmental Protection Agency',
    'ferc.gov': 'Federal Energy Regulatory Commission',
    'whitehouse.gov': 'The White House',
    'congress.gov': 'U.S. Congress',
    'regulations.gov': 'U.S. Government', 
    'supremecourt.gov': 'Supreme Court of the United States',
    'uscourts.gov': 'Administrative Office of the U.S. Courts',
    'archives.gov': 'National Archives and Records Administration',
}

# 2. AGENCY NAME LIBRARY (For Fuzzy Matching)
AGENCY_NAMES = list(GOV_AGENCY_MAP.values()) + [
    'U.S. Citizenship and Immigration Services',
    'Federal Aviation Administration',
    'National Oceanic and Atmospheric Administration',
    'Centers for Medicare & Medicaid Services',
    'Federal Bureau of Investigation',
    'Central Intelligence Agency',
    'National Security Agency'
]

# ==================== LOGIC: IDENTIFICATION ====================

def is_gov_source(text):
    """
    Determines if the input text triggers the Government Module.
    """
    if not text: return False
    clean = text.rstrip('.,;:)').lower()
    
    # Check 1: Regex for .gov ending
    if re.search(r'\.gov(/|$)', clean):
        return True
        
    # Check 2: Known domain lookup
    try:
        domain = urlparse(clean).netloc.replace('www.', '')
        if any(key in domain for key in GOV_AGENCY_MAP):
            return True
    except: pass
    
    return False

# ==================== LOGIC: EXTRACTION ====================

def get_agency_name(text):
    """
    Resolve specific agency name from domain OR text using Fuzzy Matching.
    """
    clean = text.lower().replace('www.', '')
    
    # 1. Domain Match
    if clean in GOV_AGENCY_MAP:
        return GOV_AGENCY_MAP[clean]
    for known_domain, agency in GOV_AGENCY_MAP.items():
        if clean.endswith('.' + known_domain):
            return agency
            
    # 2. Fuzzy Text Match (The "Smart" Fix)
    # Matches "dept of state" -> "U.S. Department of State"
    matches = difflib.get_close_matches(text, AGENCY_NAMES, n=1, cutoff=0.6)
    if matches:
        return matches[0]
        
    return "U.S. Government"

def extract_metadata(url):
    """
    Extracts RAW DATA from the URL. 
    Includes SMART LOGIC for acronym detection.
    """
    clean_url = url.rstrip('.,;:)')
    parsed = urlparse(clean_url)
    domain = parsed.netloc.lower().replace('www.', '')
    
    # 1. Identify Author (Agency)
    agency = get_agency_name(domain)
    
    # 2. Identify Title from URL path
    clean_title = "Government Document"
    path = parsed.path.strip('/')
    
    if path:
        segments = [s for s in path.split('/') if s]
        if segments:
            raw_title = segments[-1]
            
            # Clean up file extensions
            clean_title = re.sub(r'\.[a-z]{2,4}$', '', raw_title, flags=re.IGNORECASE)
            
            # SMART TITLE LOGIC:
            if not any(char.isdigit() for char in clean_title):
                # Words (clean-power-plan) -> Clean Power Plan
                clean_title = re.sub(r'[_-]+', ' ', clean_title).title()

            # SMART AGENCY LOGIC (For generic platforms like regulations.gov)
            if 'regulations.gov' in domain:
                parts = clean_title.split('-')
                # Try to guess agency from the document ID prefix (e.g. FDA-2023)
                possible_acronym = parts[0].upper()
                fuzzy_agency = get_agency_name(possible_acronym) 
                if fuzzy_agency != "U.S. Government":
                    agency = fuzzy_agency

    return {
        'type': 'government',
        'author': agency,
        'title': clean_title,
        'url': clean_url,
        'access_date': datetime.now().strftime("%B %d, %Y"),
        'raw_source': url
    }
