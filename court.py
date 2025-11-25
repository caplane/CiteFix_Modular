"""
Legal Citation Engine
Supports multiple legal case repositories:
    - CourtListener (Free Law Project) - Primary search API
    - Oyez.org - Supreme Court oral arguments
    - Harvard Caselaw Access Project (case.law) - URL handling
    - Justia - URL parsing
"""

import requests
import re
import datetime
import sys
from urllib.parse import urlparse

# ==================== DEBUG LOGGING ====================

def debug_log(message):
    """Print debug info to stderr (visible in Railway logs)"""
    print(f"[COURT.PY DEBUG] {message}", file=sys.stderr, flush=True)

# ==================== API CLASSES ====================

class CourtListenerAPI:
    """
    Free Law Project's CourtListener - Primary search API.
    https://www.courtlistener.com/help/api/rest/v3/case-law/
    """
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    
    @staticmethod
    def search(query):
        if not query: 
            debug_log("Empty query, skipping search")
            return None
            
        params = {'q': query, 'type': 'o', 'order_by': 'score desc', 'format': 'json'}
        debug_log(f"Searching CourtListener for: {query}")
        
        try:
            response = requests.get(CourtListenerAPI.BASE_URL, params=params, timeout=10)
            debug_log(f"CourtListener response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                debug_log(f"CourtListener returned {len(results)} results")
                
                if results:
                    first_result = results[0]
                    # Log the actual field names we receive
                    debug_log(f"First result keys: {list(first_result.keys())}")
                    debug_log(f"First result data: {first_result}")
                    return first_result
            else:
                debug_log(f"CourtListener error response: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            debug_log("CourtListener request timed out")
        except requests.exceptions.RequestException as e:
            debug_log(f"CourtListener request error: {str(e)}")
        except Exception as e:
            debug_log(f"CourtListener unexpected error: {str(e)}")
            
        return None


class OyezAPI:
    """
    Oyez.org API - Supreme Court oral arguments and case data.
    """
    BASE_URL = "https://api.oyez.org/cases"
    
    @staticmethod
    def extract_case_path(url):
        match = re.search(r'/cases/(\d{4})/([^/?#]+)', url)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        return None
    
    @staticmethod
    def fetch(url):
        case_path = OyezAPI.extract_case_path(url)
        if not case_path:
            debug_log(f"Could not extract case path from Oyez URL: {url}")
            return None
            
        api_url = f"{OyezAPI.BASE_URL}/{case_path}"
        debug_log(f"Fetching Oyez API: {api_url}")
        
        try:
            response = requests.get(api_url, timeout=10)
            debug_log(f"Oyez response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                debug_log(f"Oyez result keys: {list(data.keys())}")
                return data
        except Exception as e:
            debug_log(f"Oyez error: {str(e)}")
            
        return None


class HarvardCAPAPI:
    """
    Harvard Caselaw Access Project (case.law) - URL handling.
    """
    
    @staticmethod
    def is_cap_url(url):
        return 'case.law' in url
    
    @staticmethod
    def extract_citation_from_url(url):
        match = re.search(r'cite\.case\.law/([^/]+)/(\d+)/(\d+)', url)
        if match:
            reporter = match.group(1).upper()
            volume = match.group(2)
            page = match.group(3)
            
            reporter_map = {
                'US': 'U.S.',
                'F2D': 'F.2d',
                'F3D': 'F.3d',
                'F': 'F.',
                'FSUPP': 'F. Supp.',
                'FSUPP2D': 'F. Supp. 2d',
                'FSUPP3D': 'F. Supp. 3d',
            }
            reporter = reporter_map.get(reporter, reporter)
            
            return f"{volume} {reporter} {page}"
        return None
    
    @staticmethod
    def fetch(url):
        citation = HarvardCAPAPI.extract_citation_from_url(url)
        if not citation:
            return None
        return CourtListenerAPI.search(citation)


class JustiaAPI:
    """
    Justia - URL parsing only (no public API).
    """
    
    @staticmethod
    def is_justia_url(url):
        return 'justia.com' in url
    
    @staticmethod
    def extract_from_url(url):
        metadata = {
            'case_name': '',
            'citation': '',
            'court': '',
            'year': '',
        }
        
        match = re.search(r'/us/(\d+)/(\d+)', url)
        if match:
            volume, page = match.groups()
            metadata['citation'] = f"{volume} U.S. {page}"
            metadata['court'] = 'Supreme Court of the United States'
            return metadata
        
        match = re.search(r'/(F\d?d?)/(\d+)/(\d+)', url, re.IGNORECASE)
        if match:
            reporter, volume, page = match.groups()
            reporter_clean = reporter.upper()
            if reporter_clean == 'F2' or reporter_clean == 'F2D':
                reporter_clean = 'F.2d'
            elif reporter_clean == 'F3' or reporter_clean == 'F3D':
                reporter_clean = 'F.3d'
            metadata['citation'] = f"{volume} {reporter_clean} {page}"
            return metadata
        
        return None
    
    @staticmethod
    def fetch(url):
        extracted = JustiaAPI.extract_from_url(url)
        if not extracted or not extracted.get('citation'):
            return None
        cl_data = CourtListenerAPI.search(extracted['citation'])
        if cl_data:
            return cl_data
        return extracted


# ==================== LEGAL DOMAIN REGISTRY ====================

LEGAL_DOMAINS = [
    'courtlistener.com',
    'oyez.org',
    'case.law',
    'cite.case.law',
    'justia.com',
    'law.justia.com',
    'supreme.justia.com',
    'supremecourt.gov',
    'uscourts.gov',
    'law.cornell.edu',
    'scholar.google.com',
]


# ==================== DETECTION ====================

def is_legal_citation(text):
    """
    Check for legal citations or legal website URLs.
    """
    if not text: return False
    clean = text.strip()
    
    # 1. Check URLs
    if 'http' in clean:
        for domain in LEGAL_DOMAINS:
            if domain in clean:
                debug_log(f"Detected legal URL domain: {domain}")
                return True
        return False
        
    # 2. Check for " v. " or " v " pattern
    if re.search(r'\s(v|vs)\.?\s', clean, re.IGNORECASE):
        debug_log(f"Detected 'v.' pattern in: {clean}")
        return True
        
    # 3. Check for standard citation format (e.g., "347 U.S. 483")
    if re.search(r'\d+\s+[A-Za-z\.]+\s+\d+', clean):
        debug_log(f"Detected reporter citation format in: {clean}")
        return True
        
    return False


# ==================== EXTRACTION ====================

def extract_metadata(text):
    """
    Extract legal citation metadata from text or URL.
    """
    debug_log(f"extract_metadata called with: {text}")
    
    metadata = {
        'type': 'legal',
        'case_name': text,
        'citation': '',
        'court': '',
        'year': '',
        'url': '',
        'raw_source': text
    }
    
    clean = text.strip()
    
    # === ROUTE 1: Oyez URL ===
    if 'oyez.org' in clean:
        debug_log("Routing to Oyez API")
        case_data = OyezAPI.fetch(clean)
        if case_data:
            metadata['case_name'] = case_data.get('name', text)
            metadata['url'] = clean
            
            citation_obj = case_data.get('citation')
            if citation_obj:
                volume = citation_obj.get('volume', '')
                page = citation_obj.get('page', '')
                if volume and page:
                    metadata['citation'] = f"{volume} U.S. {page}"
                    
            timeline = case_data.get('timeline', [])
            for event in timeline:
                if event.get('event') == 'Decided':
                    dates = event.get('dates', [])
                    if dates:
                        ts = dates[0]
                        if ts:
                            dt = datetime.datetime.fromtimestamp(ts)
                            metadata['year'] = str(dt.year)
                    break
                    
            if not metadata['year']:
                decided = case_data.get('decided', '')
                if decided:
                    metadata['year'] = decided[:4]
                    
            metadata['court'] = 'Supreme Court of the United States'
            debug_log(f"Oyez metadata: {metadata}")
            return metadata
    
    # === ROUTE 2: Harvard CAP (case.law) URL ===
    if 'case.law' in clean:
        debug_log("Routing to Harvard CAP")
        citation = HarvardCAPAPI.extract_citation_from_url(clean)
        if citation:
            metadata['citation'] = citation
            metadata['url'] = clean
            
            cl_data = CourtListenerAPI.search(citation)
            if cl_data:
                metadata['case_name'] = cl_data.get('caseName', text)
                metadata['court'] = cl_data.get('court', '')
                date_filed = cl_data.get('dateFiled', '')
                if date_filed:
                    metadata['year'] = date_filed[:4]
            debug_log(f"CAP metadata: {metadata}")
            return metadata
    
    # === ROUTE 3: Justia URL ===
    if 'justia.com' in clean:
        debug_log("Routing to Justia")
        extracted = JustiaAPI.extract_from_url(clean)
        if extracted:
            metadata['citation'] = extracted.get('citation', '')
            metadata['court'] = extracted.get('court', '')
            metadata['url'] = clean
            
            if metadata['citation']:
                cl_data = CourtListenerAPI.search(metadata['citation'])
                if cl_data:
                    metadata['case_name'] = cl_data.get('caseName', text)
                    date_filed = cl_data.get('dateFiled', '')
                    if date_filed:
                        metadata['year'] = date_filed[:4]
            debug_log(f"Justia metadata: {metadata}")
            return metadata
    
    # === ROUTE 4: Text Query -> CourtListener ===
    debug_log("Routing to CourtListener search")
    
    # Normalize "v" variations
    search_query = re.sub(r'\bvs\.?\b', 'v.', clean, flags=re.IGNORECASE)
    
    case_data = CourtListenerAPI.search(search_query)
    
    if case_data:
        # Log what we're trying to extract
        debug_log(f"Extracting from case_data...")
        
        # Try both caseName and case_name (API might use either)
        case_name = case_data.get('caseName') or case_data.get('case_name') or text
        metadata['case_name'] = case_name
        debug_log(f"  case_name: {case_name}")
        
        # Try both court and court_id
        court = case_data.get('court') or case_data.get('court_id') or ''
        metadata['court'] = court
        debug_log(f"  court: {court}")
        
        # Try dateFiled and date_filed
        date_filed = case_data.get('dateFiled') or case_data.get('date_filed') or ''
        if date_filed: 
            metadata['year'] = str(date_filed)[:4]
        debug_log(f"  dateFiled: {date_filed}")
        
        # Citation might be a list or a string
        citations = case_data.get('citation') or case_data.get('citations') or []
        debug_log(f"  raw citations field: {citations} (type: {type(citations)})")
        
        if isinstance(citations, list) and citations:
            metadata['citation'] = citations[0]
        elif isinstance(citations, str) and citations:
            metadata['citation'] = citations
        debug_log(f"  extracted citation: {metadata['citation']}")
    else:
        debug_log("CourtListener returned no data")
    
    debug_log(f"Final metadata: {metadata}")
    return metadata
