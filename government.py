
"""
The Government Engine (government.py)
Acts as a 'Specialist'.
- Knows the Agency Map.
- Knows how to identify a .gov URL.
- Extracts Agency Name and Title.
- DOES NOT Format.
"""

import re
from datetime import datetime
from urllib.parse import urlparse

# ==================== DATA: AGENCY MAP ====================
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

# ==================== LOGIC: IDENTIFICATION ====================

def is_gov_source(text):
    """
    Determines if the input text triggers the Government Module.
    """
    if not text:
        return False
        
    clean = text.rstrip('.,;:)')
    
    # Check 1: Regex for .gov ending
    if re.search(r'\.gov(/|$)', clean, re.IGNORECASE):
        return True
        
    # Check 2: Known domain lookup
    try:
        domain = urlparse(clean).netloc.lower().replace('www.', '')
        if domain in GOV_AGENCY_MAP:
            return True
        for known in GOV_AGENCY_MAP:
            if domain.endswith('.' + known):
                return True
    except:
        pass
    return False

# ==================== LOGIC: EXTRACTION ====================

def get_agency_name(domain):
    """Resolve specific agency name from domain"""
    domain = domain.lower().replace('www.', '')
    if domain in GOV_AGENCY_MAP:
        return GOV_AGENCY_MAP[domain]
    for known_domain, agency in GOV_AGENCY_MAP.items():
        if domain.endswith('.' + known_domain):
            return agency
    return "U.S. Government"

def extract_metadata(url):
    """
    Extracts RAW DATA from the URL. 
    Does NOT return a formatted string.
    """
    clean_url = url.rstrip('.,;:)')
    parsed = urlparse(clean_url)
    domain = parsed.netloc.lower().replace('www.', '')
    
    # 1. Identify Author (Agency)
    agency = get_agency_name(domain)
    
    # 2. Identify Title from URL path
    path = parsed.path.strip('/')
    if path:
        segments = [s for s in path.split('/') if s]
        if segments:
            raw_title = segments[-1]
            # Clean up file extensions and underscores
            clean_title = re.sub(r'\.[a-z]{2,4}$', '', raw_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'[_-]+', ' ', clean_title).title()
        else:
            clean_title = "Government Document"
    else:
        clean_title = "Homepage"
    
    # Return PURE DATA dictionary
    return {
        'type': 'government',
        'author': agency,
        'title': clean_title,
        'url': clean_url,
        'access_date': datetime.now().strftime("%B %d, %Y"),
        'raw_source': url
    }

