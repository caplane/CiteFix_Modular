import requests
import re
from urllib.parse import urlparse

class CourtListenerAPI:
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    
    @staticmethod
    def search(query):
        if not query: return None
        params = {'q': query, 'type': 'o', 'order_by': 'score desc', 'format': 'json'}
        try:
            response = requests.get(CourtListenerAPI.BASE_URL, params=params, timeout=5)
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results: return results[0]
        except Exception: pass
        return None

def is_legal_citation(text):
    """
    Check for ' v. ', ' v ', or legal URLs.
    """
    if not text: return False
    clean = text.strip()
    
    # 1. Check URLs
    if 'http' in clean:
        # Add specific legal domains here if needed
        if 'justia.com' in clean or 'oyez.org' in clean:
            return True
        return False
        
    # 2. Check for " v. " or " v " pattern (Case Law)
    # Matches: "Plessy v. Ferguson", "Roe v Wade", "State V. Jones"
    if re.search(r'\s+v\.?\s+', clean, re.IGNORECASE):
        return True
        
    # 3. Check for standard citation format (e.g., "347 U.S. 483")
    if re.search(r'\d+\s+[A-Za-z\.]+\s+\d+', clean):
        return True
        
    return False

def extract_metadata(text):
    metadata = {
        'type': 'legal',
        'case_name': text,
        'citation': '',
        'court': '',
        'year': '',
        'raw_source': text
    }
    
    # Strip URL to get search query if needed, or use text as is
    search_query = text
    
    case_data = CourtListenerAPI.search(search_query)
    
    if case_data:
        metadata['case_name'] = case_data.get('caseName', text)
        metadata['court'] = case_data.get('court', '')
        
        date_filed = case_data.get('dateFiled', '')
        if date_filed: metadata['year'] = date_filed[:4]
            
        citations = case_data.get('citation', [])
        if citations:
            metadata['citation'] = citations[0]
            
    return metadata
