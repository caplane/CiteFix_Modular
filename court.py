import requests
import re
import difflib
import time
import os
from .base import BaseParser
from .models import CitationData

# ==================== LAYER 1: LOCAL CACHE ====================
# Your curated list of "Instant Matches"
FAMOUS_CASES = {
    'palsgraf lirr': {'case_name': 'Palsgraf v. Long Island R.R. Co.', 'citation': '248 N.Y. 339', 'year': '1928', 'court': 'N.Y.'},
    'macpherson v buick': {'case_name': 'MacPherson v. Buick Motor Co.', 'citation': '217 N.Y. 382', 'year': '1916', 'court': 'N.Y.'},
    'people v goetz': {'case_name': 'People v. Goetz', 'citation': '68 N.Y.2d 96', 'year': '1986', 'court': 'N.Y.'},
    'roe v wade': {'case_name': 'Roe v. Wade', 'citation': '410 U.S. 113', 'year': '1973', 'court': 'Supreme Court of the United States'},
    'brown v board': {'case_name': 'Brown v. Board of Education', 'citation': '347 U.S. 483', 'year': '1954', 'court': 'Supreme Court of the United States'},
    'loving v virginia': {'case_name': 'Loving v. Virginia', 'citation': '388 U.S. 1', 'year': '1967', 'court': 'Supreme Court of the United States'},
    'miranda v arizona': {'case_name': 'Miranda v. Arizona', 'citation': '384 U.S. 436', 'year': '1966', 'court': 'Supreme Court of the United States'},
    'gideon v wainwright': {'case_name': 'Gideon v. Wainwright', 'citation': '372 U.S. 335', 'year': '1963', 'court': 'Supreme Court of the United States'},
    'citizens united v fec': {'case_name': 'Citizens United v. FEC', 'citation': '558 U.S. 310', 'year': '2010', 'court': 'Supreme Court of the United States'},
    'dobbs v jackson': {'case_name': 'Dobbs v. Jackson Women\'s Health Organization', 'citation': '597 U.S. 215', 'year': '2022', 'court': 'Supreme Court of the United States'},
    'united states v nixon': {'case_name': 'United States v. Nixon', 'citation': '418 U.S. 683', 'year': '1974', 'court': 'Supreme Court of the United States'},
    'marbury v madison': {'case_name': 'Marbury v. Madison', 'citation': '5 U.S. 137', 'year': '1803', 'court': 'Supreme Court of the United States'}
}

# ==================== LAYER 2: ZOTERO / JURIS-M ====================
class ZoteroBridge:
    """
    Connects to Zotero/Juris-M API to find personally curated cases.
    Requires ZOTERO_USER_ID and ZOTERO_API_KEY env vars.
    """
    BASE_URL = "https://api.zotero.org"
    
    @staticmethod
    def search(query):
        user_id = os.environ.get('ZOTERO_USER_ID')
        api_key = os.environ.get('ZOTERO_API_KEY')
        
        # Fail gracefully if not configured
        if not user_id or not api_key:
            return None
            
        try:
            # Search specifically for items of type 'case' matching the query
            url = f"{ZoteroBridge.BASE_URL}/users/{user_id}/items"
            params = {
                'q': query,
                'itemType': 'case',
                'limit': 1,
                'format': 'json'
            }
            headers = {'Zotero-API-Key': api_key}
            
            response = requests.get(url, params=params, headers=headers, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    item = data[0].get('data', {})
                    return {
                        'caseName': item.get('caseName') or item.get('title'),
                        'citation': f"{item.get('volume', '')} {item.get('reporter', '')} {item.get('firstPage', '')}".strip(),
                        'court': item.get('court', ''),
                        'dateFiled': item.get('dateDecided', '')
                    }
        except Exception:
            pass # Fail silently to Layer 3
        return None

# ==================== LAYER 3: PUBLIC WEB API ====================
class CourtListenerAPI:
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    HEADERS = {'User-Agent': 'IncipitGenie/2.0 (Academic Research)'}
    
    @staticmethod
    def search(query):
        if not query: return None
        try:
            time.sleep(0.1) # Be polite to the API
            response = requests.get(
                CourtListenerAPI.BASE_URL, 
                params={'q': query, 'type': 'o', 'order_by': 'score desc'}, 
                headers=CourtListenerAPI.HEADERS, 
                timeout=5
            )
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results: return results[0]
        except: pass
        return None

# ==================== MAIN PARSER ====================
class CourtParser(BaseParser):
    def is_match(self, text):
        # 1. Check Fuzzy Cache
        clean = text.lower().replace('.', '').replace(',', '')
        if difflib.get_close_matches(clean, FAMOUS_CASES.keys(), n=1, cutoff=0.8): 
            return True
        # 2. Check Regex Patterns
        return ' v. ' in text or ' vs ' in text or 'In re ' in text

    def parse(self, text):
        clean = text.lower().replace('.', '').replace(',', '')
        
        # --- STEP 1: CHECK CACHE (Fastest) ---
        match = difflib.get_close_matches(clean, FAMOUS_CASES.keys(), n=1, cutoff=0.8)
        if match:
            d = FAMOUS_CASES[match[0]]
            return CitationData(
                raw=text, type='court', title=d['case_name'], year=d['year'], 
                extra={'citation': d['citation'], 'court': d['court']}
            )
        
        # --- STEP 2: CHECK ZOTERO (Most Trusted) ---
        zotero_data = ZoteroBridge.search(text)
        if zotero_data:
            year = str(zotero_data.get('dateFiled', ''))[:4]
            return CitationData(
                raw=text, type='court', 
                title=zotero_data.get('caseName'), 
                year=year, 
                extra={'citation': zotero_data.get('citation'), 'court': zotero_data.get('court')}
            )

        # --- STEP 3: CHECK COURTLISTENER (Broadest) ---
        api_data = CourtListenerAPI.search(text)
        if api_data:
            citation = ""
            # Handle CourtListener's complex citation list
            if api_data.get('citation') and isinstance(api_data['citation'], list):
                citation = api_data['citation'][0]
            elif api_data.get('citation'):
                citation = api_data['citation']
                
            return CitationData(
                raw=text, type='court', 
                title=api_data.get('caseName', text), 
                year=str(api_data.get('dateFiled', ''))[:4],
                extra={'citation': citation, 'court': api_data.get('court', '')}
            )
        
        # --- FALLBACK ---
        return CitationData(
            raw=text, type='court', 
            title=text.split(' v. ')[0], 
            year='2025', 
            extra={'citation': '', 'court': ''}
        )
