"""
Legal Citation Engine (Smart Iteration v2)
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
    """Print debug info to stderr (visible in Railway/Terminal logs)"""
    print(f"[COURT.PY DEBUG] {message}", file=sys.stderr, flush=True)

# ==================== API CLASSES ====================

class CourtListenerAPI:
    """
    Free Law Project's CourtListener - Primary search API.
    """
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    
    @staticmethod
    def search(query):
        if not query: 
            return None
            
        params = {'q': query, 'type': 'o', 'order_by': 'score desc', 'format': 'json'}
        debug_log(f"Searching CourtListener for: {query}")
        
        try:
            response = requests.get(CourtListenerAPI.BASE_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                debug_log(f"CourtListener returned {len(results)} results")
                
                # === SMART FIX: Iterate to find the best match ===
                # Don't just take the first result. Take the first one 
                # that actually has a citation.
                for result in results[:5]:  # Check top 5 candidates
                    citations = result.get('citation') or result.get('citations') or []
                    case_name = result.get('caseName') or result.get('case_name') or ""
                    
                    # If we have citations, this is a "real" case (not a docket entry)
                    if citations:
                        debug_log(f"Found valid candidate: {case_name} with citations: {citations}")
                        return result
                    else:
                        debug_log(f"Skipping candidate {case_name} (No citations found)")
                
                # Fallback: If no citations found in top 5, return the first one anyway
                if results:
                    return results[0]

            else:
                debug_log(f"CourtListener error response: {response.status_code}")
                
        except Exception as e:
            debug_log(f"CourtListener connection error: {str(e)}")
            
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
            return None
        try:
            response = requests.get(f"{OyezAPI.BASE_URL}/{case_path}", timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            debug_log(f"Oyez error: {str(e)}")
        return None


class HarvardCAPAPI:
    """
    Harvard Caselaw Access Project (case.law) - URL handling.
    """
    @staticmethod
    def extract_citation_from_url(url):
        match = re.search(r'cite\.case\.law/([^/]+)/(\d+)/(\d+)', url)
        if match:
            reporter = match.group(1).upper()
            # Normalize reporter names
            reporter_map = {
                'US': 'U.S.', 'F2D': 'F.2d', 'F3D': 'F.3d', 
                'F': 'F.', 'FSUPP': 'F. Supp.'
            }
            reporter = reporter_map.get(reporter, reporter)
            return f"{match.group(2)} {reporter} {match.group(3)}"
        return None


class JustiaAPI:
    """
    Justia - URL parsing.
    """
    @staticmethod
    def extract_from_url(url):
        metadata = {'case_name': '', 'citation': '', 'court': '', 'year': ''}
        
        # Pattern: /us/410/113/
        match = re.search(r'/us/(\d+)/(\d+)', url)
        if match:
            metadata['citation'] = f"{match.group(1)} U.S. {match.group(2)}"
            metadata['court'] = 'Supreme Court of the United States'
            return metadata
            
        # Pattern: /federal/appellate-courts/ca5/19-10011/
        match = re.search(r'/(F\d?d?)/(\d+)/(\d+)', url, re.IGNORECASE)
        if match:
            metadata['citation'] = f"{match.group(2)} {match.group(1).upper()} {match.group(3)}"
            return metadata
        return None


# ==================== EXTRACTION LOGIC ====================

LEGAL_DOMAINS = [
    'courtlistener.com', 'oyez.org', 'case.law', 'cite.case.law', 
    'justia.com', 'supremecourt.gov', 'law.cornell.edu', 'scholar.google.com'
]

def is_legal_citation(text):
    if not text: return False
    clean = text.strip()
    
    if 'http' in clean:
        for domain in LEGAL_DOMAINS:
            if domain in clean: return True
        return False
        
    if re.search(r'\s(v|vs)\.?\s', clean, re.IGNORECASE):
        return True
        
    if re.search(r'\d+\s+[A-Za-z\.]+\s+\d+', clean):
        return True
        
    return False

def extract_metadata(text):
    """
    Extract legal citation metadata.
    """
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
    
    # URL Routes
    if 'oyez.org' in clean:
        case_data = OyezAPI.fetch(clean)
        if case_data:
            metadata['case_name'] = case_data.get('name', text)
            cit = case_data.get('citation')
            if cit: metadata['citation'] = f"{cit.get('volume')} U.S. {cit.get('page')}"
            metadata['year'] = case_data.get('decided', '')[:4]
            return metadata

    if 'case.law' in clean:
        cit = HarvardCAPAPI.extract_citation_from_url(clean)
        if cit:
            metadata['citation'] = cit
            # Enrich with CourtListener
            cl_data = CourtListenerAPI.search(cit)
            if cl_data:
                metadata['case_name'] = cl_data.get('caseName', text)
                metadata['year'] = str(cl_data.get('dateFiled', ''))[:4]
            return metadata

    if 'justia.com' in clean:
        ext = JustiaAPI.extract_from_url(clean)
        if ext:
            metadata.update({k:v for k,v in ext.items() if v})
            # Enrich
            if metadata['citation']:
                cl_data = CourtListenerAPI.search(metadata['citation'])
                if cl_data:
                    metadata['case_name'] = cl_data.get('caseName', text)
                    metadata['year'] = str(cl_data.get('dateFiled', ''))[:4]
            return metadata

    # Text Search Route
    # Normalize 'vs' to 'v.' for better API hits
    search_query = re.sub(r'\bvs\.?\b', 'v.', clean, flags=re.IGNORECASE)
    
    case_data = CourtListenerAPI.search(search_query)
    
    if case_data:
        metadata['case_name'] = case_data.get('caseName') or case_data.get('case_name') or text
        metadata['court'] = case_data.get('court') or case_data.get('court_id') or ''
        
        date_filed = case_data.get('dateFiled') or case_data.get('date_filed')
        if date_filed: 
            metadata['year'] = str(date_filed)[:4]
            
        citations = case_data.get('citation') or case_data.get('citations') or []
        if isinstance(citations, list) and citations:
            metadata['citation'] = citations[0]
        elif isinstance(citations, str) and citations:
            metadata['citation'] = citations
            
    return metadata
