"""
Legal Citation Engine (Robust v3)
- Exact Phrase Retry Strategy
- SCOTUS Prioritization
- Strict Citation Validation
"""

import requests
import re
import sys

# ==================== LOGGING ====================
def debug_log(message):
    print(f"[COURT.PY] {message}", file=sys.stderr, flush=True)

# ==================== API CLASSES ====================

class CourtListenerAPI:
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    
    @staticmethod
    def search(query, exact_retry=True):
        if not query: return None
        
        # 1. Try Standard Search
        result = CourtListenerAPI._execute_search(query)
        if result: return result
        
        # 2. Try Exact Phrase Search (if failed)
        if exact_retry and '"' not in query:
            debug_log(f"Standard search failed. Retrying with exact phrase: \"{query}\"")
            exact_query = f'"{query}"'
            result = CourtListenerAPI._execute_search(exact_query)
            if result: return result
            
        return None

    @staticmethod
    def _execute_search(q):
        # params: type='o' (Opinion), order_by='score desc'
        params = {'q': q, 'type': 'o', 'order_by': 'score desc', 'format': 'json'}
        
        try:
            debug_log(f"Querying: {q}")
            response = requests.get(CourtListenerAPI.BASE_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                debug_log(f"Hits: {len(results)}")
                
                # === SEARCH STRATEGY ===
                best_candidate = None
                
                # Check top 10 results (deep scan)
                for i, res in enumerate(results[:10]):
                    citations = res.get('citation') or res.get('citations') or []
                    court = res.get('court') or res.get('court_id') or ''
                    name = res.get('caseName') or res.get('case_name') or ''
                    
                    # CRITICAL: Must have a citation to be useful
                    if not citations:
                        continue
                        
                    # Rule A: SCOTUS Priority (If it's Supreme Court, grab it immediately)
                    if 'scotus' in court.lower() or 'supreme court' in court.lower():
                        debug_log(f"Found SCOTUS match at index {i}: {name}")
                        return res
                        
                    # Rule B: First valid result with a citation (Fallback)
                    if best_candidate is None:
                        best_candidate = res
                
                return best_candidate

        except Exception as e:
            debug_log(f"API Error: {e}")
            
        return None

class OyezAPI:
    """Fallback for Oyez URLs"""
    BASE_URL = "https://api.oyez.org/cases"
    @staticmethod
    def fetch(url):
        try:
            match = re.search(r'/cases/(\d{4})/([^/?#]+)', url)
            if match:
                api_url = f"{OyezAPI.BASE_URL}/{match.group(1)}/{match.group(2)}"
                res = requests.get(api_url, timeout=5)
                if res.status_code == 200: return res.json()
        except: pass
        return None

# ==================== MAIN LOGIC ====================

def is_legal_citation(text):
    if not text: return False
    clean = text.strip()
    if 'http' in clean:
        return any(x in clean for x in ['courtlistener', 'oyez', 'justia', 'case.law', 'supremecourt'])
    # Detect "v." or "vs."
    return bool(re.search(r'\s(v|vs)\.?\s', clean, re.IGNORECASE))

def extract_metadata(text):
    metadata = {
        'type': 'legal', 'case_name': text, 'citation': '', 
        'court': '', 'year': '', 'url': '', 'raw_source': text
    }
    clean = text.strip()

    # 1. URL Handlers (Oyez/Justia/CAP)
    if 'http' in clean:
        if 'oyez.org' in clean:
            data = OyezAPI.fetch(clean)
            if data:
                metadata['case_name'] = data.get('name', text)
                metadata['year'] = str(data.get('term', ''))[:4]
                cit = data.get('citation')
                if cit: metadata['citation'] = f"{cit.get('volume')} U.S. {cit.get('page')}"
                return metadata
        # (For brevity, basic URL logic handled by search fallback if complex)

    # 2. Search Handler (CourtListener)
    # Normalize "Roe v Wade" -> "Roe v. Wade" for cleaner search
    search_q = re.sub(r'\bvs\.?\b', 'v.', clean, flags=re.IGNORECASE)
    
    case_data = CourtListenerAPI.search(search_q)
    
    if case_data:
        metadata['case_name'] = case_data.get('caseName') or text
        metadata['court'] = case_data.get('court') or ''
        
        # Extract Year
        date_filed = case_data.get('dateFiled') or ''
        if date_filed: metadata['year'] = date_filed[:4]
        
        # Extract Citation
        citations = case_data.get('citation') or case_data.get('citations') or []
        if isinstance(citations, list) and citations:
            metadata['citation'] = citations[0]
        elif isinstance(citations, str):
            metadata['citation'] = citations
            
    return metadata
