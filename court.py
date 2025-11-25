"""
Legal Citation Engine (Stealth Mode)
Mimics a real browser to bypass Data Center IP blocking.
"""

import requests
import re
import sys
import time

# ==================== DEBUG LOGGING ====================

def debug_log(message):
    print(f"[COURT.PY] {message}", file=sys.stderr, flush=True)

# ==================== API CLASSES ====================

class CourtListenerAPI:
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    
    # STEALTH HEADERS: Mimic a standard Chrome browser to bypass IP blocking
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    }
    
    @staticmethod
    def search(query):
        if not query: return None
            
        params = {'q': query, 'type': 'o', 'order_by': 'score desc', 'format': 'json'}
        debug_log(f"Searching (Stealth Mode): {query}")
        
        try:
            # Add a tiny random delay to feel human (optional but helpful)
            time.sleep(0.2)
            
            response = requests.get(
                CourtListenerAPI.BASE_URL, 
                params=params, 
                headers=CourtListenerAPI.HEADERS, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # Iterate top 10 to find first valid citation (skip docket entries)
                for result in results[:10]:
                    citations = result.get('citation') or result.get('citations')
                    case_name = result.get('caseName') or result.get('case_name')
                    
                    if citations:
                        debug_log(f"Match found: {case_name}")
                        return result
                        
                # Fallback: Return first result even if empty (better than nothing)
                if results: return results[0]
            else:
                debug_log(f"API Blocked: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            debug_log(f"Connection Failed: {e}")
            
        return None

class OyezAPI:
    BASE_URL = "https://api.oyez.org/cases"
    
    @staticmethod
    def fetch(url):
        match = re.search(r'/cases/(\d{4})/([^/?#]+)', url)
        if match:
            path = f"{match.group(1)}/{match.group(2)}"
            try:
                # Use simple headers for Oyez too
                return requests.get(
                    f"{OyezAPI.BASE_URL}/{path}", 
                    headers={'User-Agent': 'CiteFix-Pro/2.0'}, 
                    timeout=10
                ).json()
            except: pass
        return None

class JustiaAPI:
    @staticmethod
    def extract_from_url(url):
        # Supreme Court Pattern
        match = re.search(r'/us/(\d+)/(\d+)', url)
        if match:
            return {'citation': f"{match.group(1)} U.S. {match.group(2)}", 'court': 'Supreme Court of the United States'}
        # Circuit Pattern
        match = re.search(r'/(F\d?d?)/(\d+)/(\d+)', url, re.IGNORECASE)
        if match:
            return {'citation': f"{match.group(2)} {match.group(1).upper()} {match.group(3)}"}
        return None

# ==================== EXTRACTION LOGIC ====================

LEGAL_DOMAINS = ['courtlistener.com', 'oyez.org', 'case.law', 'justia.com', 'supremecourt.gov', 'law.cornell.edu']

def is_legal_citation(text):
    if not text: return False
    clean = text.strip()
    if 'http' in clean: return any(d in clean for d in LEGAL_DOMAINS)
    if re.search(r'\s(v|vs)\.?\s', clean, re.IGNORECASE): return True
    if re.search(r'\d+\s+[A-Za-z\.]+\s+\d+', clean): return True
    return False

def extract_metadata(text):
    metadata = {
        'type': 'legal', 'case_name': text, 'citation': '', 
        'court': '', 'year': '', 'url': '', 'raw_source': text
    }
    clean = text.strip()
    
    # 1. URL Handlers
    if 'oyez.org' in clean:
        data = OyezAPI.fetch(clean)
        if data:
            metadata['case_name'] = data.get('name', text)
            if data.get('citation'):
                c = data['citation']
                metadata['citation'] = f"{c.get('volume')} U.S. {c.get('page')}"
            metadata['year'] = data.get('decided', '')[:4]
            return metadata

    if 'justia.com' in clean:
        ext = JustiaAPI.extract_from_url(clean)
        if ext:
            metadata.update(ext)
            if metadata['citation']:
                cl_data = CourtListenerAPI.search(metadata['citation'])
                if cl_data:
                    metadata['case_name'] = cl_data.get('caseName', text)
                    metadata['year'] = str(cl_data.get('dateFiled', ''))[:4]
            return metadata

    # 2. Text Search
    search_query = re.sub(r'\bvs\.?\b', 'v.', clean, flags=re.IGNORECASE)
    case_data = CourtListenerAPI.search(search_query)
    
    if case_data:
        metadata['case_name'] = case_data.get('caseName') or case_data.get('case_name') or text
        metadata['court'] = case_data.get('court') or case_data.get('court_id') or ''
        df = case_data.get('dateFiled') or case_data.get('date_filed')
        if df: metadata['year'] = str(df)[:4]
        
        citations = case_data.get('citation') or case_data.get('citations')
        if isinstance(citations, list) and citations:
            metadata['citation'] = citations[0]
        elif isinstance(citations, str) and citations:
            metadata['citation'] = citations
            
    return metadata
