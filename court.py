import requests
import re

class CourtListenerAPI:
    """
    Interface for the CourtListener API (Free Law Project).
    """
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    
    @staticmethod
    def search_case(query):
        """
        Search for a case by name (e.g., 'Brown v. Board').
        """
        if not query: return None
        
        params = {
            'q': query,
            'type': 'o', # 'o' = Opinion (Case Law)
            'order_by': 'score desc',
            'format': 'json'
        }
        
        try:
            # Note: In production, you should use an API Token for higher limits
            # For testing, we can try without one, but it might be rate-limited.
            response = requests.get(CourtListenerAPI.BASE_URL, params=params, timeout=5)
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    return results[0] # Return best match
        except Exception as e:
            print(f"CourtListener API Error: {e}")
            
        return None

def is_legal_citation(text):
    """
    Heuristic: Does it look like a legal case?
    Look for ' v. ' or ' V. '
    """
    if not text: return False
    # Basic check for adversarial party names
    if re.search(r'\s+v\.\s+', text, re.IGNORECASE):
        return True
    return False

def extract_metadata(text):
    """
    Extract metadata for a legal case.
    """
    # 1. Try to find the case via API
    case_data = CourtListenerAPI.search_case(text)
    
    if case_data:
        # Extract structured data
        case_name = case_data.get('caseName', text)
        
        # Try to find the citation (Volume Reporter Page)
        # CourtListener often puts this in 'citation' list
        citations = case_data.get('citation', [])
        cite_str = ""
        if citations:
            # Prefer the official reporter if available
            cite_str = citations[0] 
        
        # Date/Year
        date_filed = case_data.get('dateFiled', '')
        year = date_filed[:4] if date_filed else ''
        
        # Court
        court = case_data.get('court', '')
        
        return {
            'type': 'legal',
            'case_name': case_name, # "Brown v. Board of Education"
            'citation': cite_str,   # "347 U.S. 483"
            'court': court,         # "Supreme Court of the United States"
            'year': year,           # "1954"
            'raw_source': text
        }
    
    # Fallback if API fails
    return {
        'type': 'legal',
        'case_name': text,
        'citation': '',
        'court': '',
        'year': '',
        'raw_source': text
    }
