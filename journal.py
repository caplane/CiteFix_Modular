import requests
import re
from datetime import datetime

# ==================== DATA: ABBREVIATION MAP ====================
# Maps common shorthand to the full, official CrossRef title.
# This significantly improves search accuracy.

JOURNAL_ABBREVIATIONS = {
    # --- MAJOR MEDICAL ---
    'ajp': 'American Journal of Psychiatry',
    'am j psychiatry': 'American Journal of Psychiatry',
    'nejm': 'New England Journal of Medicine',
    'n engl j med': 'New England Journal of Medicine',
    'jama': 'Journal of the American Medical Association',
    'bmj': 'British Medical Journal',
    'brit med j': 'British Medical Journal',
    'lancet': 'The Lancet',
    'pnas': 'Proceedings of the National Academy of Sciences',
    
    # --- PSYCHIATRY SPECIFIC ---
    'arch gen psychiatry': 'Archives of General Psychiatry',
    'arch gen psych': 'Archives of General Psychiatry',
    'jaacap': 'Journal of the American Academy of Child and Adolescent Psychiatry',
    'j clin psychiatry': 'Journal of Clinical Psychiatry',
    'j nerv ment dis': 'Journal of Nervous and Mental Disease',
    'brit j psychiatry': 'British Journal of Psychiatry',
    'psychol rev': 'Psychological Review',
    'psychol bull': 'Psychological Bulletin',
    'am psychol': 'American Psychologist',
    
    # --- HISTORY / SOCIAL SCIENCE ---
    'ahr': 'American Historical Review',
    'am hist rev': 'American Historical Review',
    'jah': 'Journal of American History',
    'j am hist': 'Journal of American History',
    'ajs': 'American Journal of Sociology',
    'am j sociol': 'American Journal of Sociology',
    'asr': 'American Sociological Review',
    'soc sci med': 'Social Science & Medicine',
    'wmq': 'William and Mary Quarterly',
}

# ==================== DATA: JOURNAL WHITELIST ====================
# High-priority targets. If these words appear, we FORCE a journal search.

JOURNAL_MAP = {
    # --- THE GIANTS ---
    'nature', 'science', 'cell', 'lancet', 'jama', 'bmj', 'mind', 
    'isis', 'osiris', 'past', 'history', 'psychology', 'pediatrics',
    'circulation', 'chest', 'brain', 'neuron', 'blood', 'cancer',
    'gut', 'spine', 'stroke', 'pain', 'sleep', 'epilepsia', 'addiction',

    # --- HISTORY OF PSYCHIATRY & MEDICINE ---
    'history of psychiatry',
    'history of the human sciences',
    'journal of the history of the behavioral sciences',
    'bulletin of the history of medicine',
    'journal of the history of medicine and allied sciences',
    'social history of medicine',
    'medical history',
    'history of psychology',
    'psychological medicine',
    'culture, medicine and psychiatry',
    'philosophy, psychiatry, & psychology',
    'history and philosophy of the life sciences',

    # --- PSYCHIATRY & PSYCHOLOGY ---
    'american journal of psychiatry',
    'british journal of psychiatry',
    'archives of general psychiatry',
    'molecular psychiatry',
    'biological psychiatry',
    'journal of clinical psychiatry',
    'schizophrenia bulletin',
    'journal of nervous and mental disease',
    'psychological review',
    'psychological bulletin',
    'american psychologist',
    'journal of consulting and clinical psychology',
    'journal of abnormal psychology',
    'psychosomatic medicine',

    # --- GENERAL HISTORY ---
    'american historical review',
    'past and present',
    'journal of american history',
    'english historical review',
    'william and mary quarterly',
    'journal of modern history',
    'comparative studies in society and history',
    'journal of interdisciplinary history',
    'historical journal',
    'history workshop journal',
    'social history',
    'economic history review',
    'journal of economic history',
    'environmental history',
    'journal of global history',
    'history and theory',

    # --- SOCIAL SCIENCE ---
    'social science & medicine',
    'american sociological review',
    'american journal of sociology',
    'annual review of sociology',
    'social forces',
    'public opinion quarterly',
    'american political science review',
    'journal of politics',
    'american anthropologist',
    'current anthropology',
    'journal of health and social behavior',
    'sociology of health and illness',

    # --- HUMANITIES ---
    'critical inquiry',
    'public culture',
    'social text',
    'differences',
    'modern language quarterly',
    'pmla',
    'modernism/modernity',
    'new literary history',
    'american quarterly',
    'grey room',
    'october'
}

# ==================== ENGINE: CROSSREF API ====================

class CrossRefAPI:
    BASE_URL = "https://api.crossref.org/works"
    HEADERS = {'User-Agent': 'CiteFix-Pro/2.1 (mailto:admin@example.com)'}

    @staticmethod
    def get_by_doi(doi):
        try:
            clean_doi = doi.strip()
            if clean_doi.lower().startswith('https://doi.org/'): clean_doi = clean_doi[16:]
            elif clean_doi.lower().startswith('doi:'): clean_doi = clean_doi[4:]
            
            url = f"{CrossRefAPI.BASE_URL}/{clean_doi}"
            response = requests.get(url, headers=CrossRefAPI.HEADERS, timeout=5)
            return response.json().get('message', {}) if response.status_code == 200 else None
        except: return None

    @staticmethod
    def search_query(query):
        try:
            # NORMALIZATION STEP: Expand abbreviations before searching
            # This turns "AJP 156" into "American Journal of Psychiatry 156"
            refined_query = query
            lower_query = query.lower()
            
            for abbrev, full_title in JOURNAL_ABBREVIATIONS.items():
                # Match whole words only (avoid replacing 'ahr' inside 'fahrenheit')
                if re.search(r'\b' + re.escape(abbrev) + r'\b', lower_query):
                    refined_query = re.sub(r'\b' + re.escape(abbrev) + r'\b', full_title, refined_query, flags=re.IGNORECASE)
                    break # Stop after first major replacement to avoid conflicts

            params = {
                'query.bibliographic': refined_query,
                'rows': 1,
                'select': 'title,author,container-title,volume,issue,page,published-print,published-online,DOI'
            }
            response = requests.get(CrossRefAPI.BASE_URL, params=params, headers=CrossRefAPI.HEADERS, timeout=5)
            return response.json().get('message', {}).get('items', [])[0] if response.status_code == 200 else None
        except: return None

# ==================== LOGIC: IDENTIFICATION ====================

def is_journal_citation(text):
    """
    Detects if the text looks like an academic article.
    """
    if not text: return False
    lower = text.lower()
    
    # 1. The Smoking Gun: DOI
    if re.search(r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b', text, re.IGNORECASE):
        return True

    # 2. Whitelist Check (Full Names)
    for journal in JOURNAL_MAP:
        if re.search(r'\b' + re.escape(journal) + r'\b', lower):
            return True
            
    # 3. Abbreviation Check (AJP, JAMA)
    for abbrev in JOURNAL_ABBREVIATIONS:
        if re.search(r'\b' + re.escape(abbrev) + r'\b', lower):
            return True
        
    # 4. Generic Keywords
    indicators = ['journal of', 'review of', 'quarterly', 'archives of', 'annals of', 'doi.org', 'vol.', 'no.']
    if any(i in lower for i in indicators):
        return True
        
    # 5. Volume/Issue Pattern (e.g., "34, no. 2" or "34:2")
    if re.search(r'\d+\s*,\s*no\.?\s*\d+', text) or re.search(r'\d+:\d+', text):
        return True
        
    return False

# ==================== LOGIC: EXTRACTION ====================

def extract_metadata(text):
    clean_text = text.strip()
    raw_data = None
    
    # Try DOI first
    doi_match = re.search(r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b', clean_text, re.IGNORECASE)
    if doi_match:
        raw_data = CrossRefAPI.get_by_doi(doi_match.group(1))
    
    # Fallback to Text Search (with normalization)
    if not raw_data:
        raw_data = CrossRefAPI.search_query(clean_text)

    metadata = {
        'type': 'journal',
        'raw_source': text,
        'authors': [],
        'title': '',
        'journal': '',
        'volume': '',
        'issue': '',
        'year': '',
        'pages': '',
        'doi': '',
        'url': ''
    }

    if raw_data:
        # Authors
        if 'author' in raw_data:
            for auth in raw_data['author']:
                if 'family' in auth:
                    given = auth.get('given', '')
                    family = auth.get('family', '')
                    name = f"{given} {family}".strip()
                    metadata['authors'].append(name)
        
        # Title
        titles = raw_data.get('title', [])
        if titles: metadata['title'] = titles[0]
            
        # Journal Name
        journals = raw_data.get('container-title', [])
        if journals: metadata['journal'] = journals[0]
            
        # Details
        metadata['volume'] = raw_data.get('volume', '')
        metadata['issue'] = raw_data.get('issue', '')
        metadata['pages'] = raw_data.get('page', '')
        metadata['doi'] = raw_data.get('DOI', '')
        
        # Year (Try Print first, then Online)
        dp = raw_data.get('published-print', {}).get('date-parts')
        if not dp: dp = raw_data.get('published-online', {}).get('date-parts')
        
        if dp and len(dp) > 0:
            metadata['year'] = str(dp[0][0])

    if not metadata['title']: 
        metadata['title'] = "Unknown Article" 

    return metadata
