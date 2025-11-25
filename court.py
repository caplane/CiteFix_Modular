"""
Legal Citation Engine (Regex Fix v4)
- Fixed "v" normalization (Crucial for 'Roe v wade')
- Expanded scan depth to 15
- Fallback logic to ensure results
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
    def search(query):
        if not query: return None
        
        # 1. Try Standard Search (Strict Mode: Must have citation)
        result = CourtListenerAPI._execute_search(query, require_citation=True)
        if result: return result
        
        # 2. Try Exact Phrase Search (Strict Mode)
        if '"' not in query:
            debug_log(f"Retrying with exact phrase: \"{query}\"")
            exact_query = f'"{query}"'
            result = CourtListenerAPI._execute_search(exact_query, require_citation=True)
            if result: return result

        # 3. Last Resort: Relax citation requirement (Just get the Case Name)
        # This prevents the "No Match" error, even if we can't find the volume/page.
        debug_log("Strict search failed. Relaxing requirements.")
        return CourtListenerAPI._execute_search(query, require_citation=False)

    @staticmethod
    def _execute_search(q, require_citation=True):
        params = {'q': q, 'type': 'o', 'order_by': 'score desc', 'format': 'json'}
        
        try:
            debug_log(f"Querying: {q} (Require Citation: {require_citation})")
            response = requests.get(CourtListenerAPI.BASE_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                debug_log(f"Hits: {len(results)}")
                
                # Check top 15 results
                for i, res in enumerate(results[:15]):
                    citations = res.get('citation') or res.get('citations') or []
                    court = res.get('court') or res.get('court_id') or ''
                    name = res.get('caseName') or res.get('case_name') or ''
                    
                    # VALIDATION LOGIC
                    has_citation = bool(citations)
                    is_scotus = 'scotus' in court.lower() or 'supreme court' in court.lower()
                    
                    # If we require a citation and this result doesn't have one, skip it.
                    if require_citation and not has_citation:
                        continue

                    # SCOTUS PRIORITY: If we find a SCOTUS case, take it immediately.
                    if is_scotus:
                        debug_log(f"Found SCOTUS match at #{i}: {name}")
                        return res
                    
                    # Otherwise, return the first valid result we find
                    debug_log(f"Found valid match at #{i}: {name}")
                    return res
                    
        except Exception as e:
            debug_log(f"API Error: {e}")
            
        return None

class OyezAPI:
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
    return bool(re.search(r'\s(v|vs)\.?\s', clean, re.IGNORECASE))

def extract_metadata(text):
    metadata = {
        'type': 'legal', 'case_name': text, 'citation': '', 
        'court': '', 'year': '', 'url': '', 'raw_source': text
    }
    clean = text.strip()

    # 1. URL Handler
    if 'http' in clean and 'oyez.org' in clean:
        data = OyezAPI.fetch(clean)
        if data:
            metadata['case_name'] = data.get('name', text)
            metadata['year'] = str(data.get('term', ''))[:4]
            cit = data.get('citation')
            if cit: metadata['citation'] = f"{cit.get('volume')} U.S. {cit.get('page')}"
            return metadata

    # 2. Search Handler
    # === CRITICAL FIX: Normalize 'v' OR 'vs' to 'v.' ===
    # This turns "Roe v wade" into "Roe v. wade", ensuring the API hit.
    search_q = re.sub(r'\b(vs?|v)\.?\b', 'v.', clean, flags=re.IGNORECASE)
    
    case_data = CourtListenerAPI.search(search_q)
    
    if case_data:
        metadata['case_name'] = case_data.get('caseName') or text
        metadata['court'] = case_data.get('court') or ''
        
        date_filed = case_data.get('dateFiled') or ''
        if date_filed: metadata['year'] = date_filed[:4]
        
        citations = case_data.get('citation') or case_data.get('citations') or []
        if isinstance(citations, list) and citations:
            metadata['citation'] = citations[0]
        elif isinstance(citations, str):
            metadata['citation'] = citations
            
    return metadata
