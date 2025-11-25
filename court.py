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
from urllib.parse import urlparse

# ==================== API CLASSES ====================

class CourtListenerAPI:
    """
    Free Law Project's CourtListener - Primary search API.
    https://www.courtlistener.com/help/api/
    
    Coverage: Federal and state courts, millions of opinions.
    """
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


class OyezAPI:
    """
    Oyez.org API - Supreme Court oral arguments and case data.
    
    URL patterns:
        Website: https://www.oyez.org/cases/1966/395
        API:     https://api.oyez.org/cases/1966/395
    """
    BASE_URL = "https://api.oyez.org/cases"
    
    @staticmethod
    def extract_case_path(url):
        """Extract term and docket from Oyez URL."""
        match = re.search(r'/cases/(\d{4})/([^/?#]+)', url)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        return None
    
    @staticmethod
    def fetch(url):
        """Fetch case data from Oyez API."""
        case_path = OyezAPI.extract_case_path(url)
        if not case_path:
            return None
            
        api_url = f"{OyezAPI.BASE_URL}/{case_path}"
        
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None


class HarvardCAPAPI:
    """
    Harvard Caselaw Access Project (case.law) - URL handling.
    
    Note: Native search was disabled September 2024.
    CourtListener is now recommended for searching CAP data.
    This class handles direct case.law URLs only.
    
    URL patterns:
        https://case.law/caselaw/?reporter=us&volume=388&case=0001-01
        https://cite.case.law/us/388/1/
    """
    
    @staticmethod
    def is_cap_url(url):
        """Check if URL is from case.law"""
        return 'case.law' in url
    
    @staticmethod
    def extract_citation_from_url(url):
        """
        Extract citation info from case.law URL.
        
        Examples:
            https://cite.case.law/us/388/1/ -> 388 U.S. 1
            https://cite.case.law/f2d/478/750/ -> 478 F.2d 750
        """
        # Pattern: /reporter/volume/page/
        match = re.search(r'cite\.case\.law/([^/]+)/(\d+)/(\d+)', url)
        if match:
            reporter = match.group(1).upper()
            volume = match.group(2)
            page = match.group(3)
            
            # Map common reporter abbreviations
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
        """
        Fetch case data from case.law.
        Returns metadata dict or None.
        """
        citation = HarvardCAPAPI.extract_citation_from_url(url)
        if not citation:
            return None
            
        # Use CourtListener to look up the case by citation
        return CourtListenerAPI.search(citation)


class JustiaAPI:
    """
    Justia - URL parsing only (no public API).
    
    URL patterns:
        Supreme Court: https://supreme.justia.com/cases/federal/us/388/1/
        Federal Appeals: https://law.justia.com/cases/federal/appellate-courts/F2/478/750/
        State Courts: https://law.justia.com/cases/california/supreme-court/2d/1/100/
    """
    
    @staticmethod
    def is_justia_url(url):
        """Check if URL is from Justia"""
        return 'justia.com' in url
    
    @staticmethod
    def extract_from_url(url):
        """
        Extract case info from Justia URL.
        
        Returns dict with case_name, citation, etc.
        """
        metadata = {
            'case_name': '',
            'citation': '',
            'court': '',
            'year': '',
        }
        
        # Supreme Court pattern: /us/VOLUME/PAGE/
        match = re.search(r'/us/(\d+)/(\d+)', url)
        if match:
            volume, page = match.groups()
            metadata['citation'] = f"{volume} U.S. {page}"
            metadata['court'] = 'Supreme Court of the United States'
            return metadata
        
        # Federal Appeals pattern: /F2/VOLUME/PAGE/ or /F3d/VOLUME/PAGE/
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
        """
        Fetch case data using Justia URL.
        Extracts citation from URL, then searches CourtListener.
        """
        extracted = JustiaAPI.extract_from_url(url)
        if not extracted or not extracted.get('citation'):
            return None
            
        # Look up full case details via CourtListener
        cl_data = CourtListenerAPI.search(extracted['citation'])
        if cl_data:
            return cl_data
            
        # Return what we extracted from URL as fallback
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
    'scholar.google.com',  # Can detect, but can't scrape
]


# ==================== DETECTION ====================

def is_legal_citation(text):
    """
    Check for legal citations or legal website URLs.
    
    Matches:
        - "Plessy v. Ferguson"  (v with period)
        - "Plessy v Ferguson"   (v without period)  
        - "Roe vs Wade"         (vs without period)
        - "State vs. Jones"     (vs with period)
        - "347 U.S. 483"        (reporter citation)
        - URLs from legal domains
    """
    if not text: return False
    clean = text.strip()
    
    # 1. Check URLs
    if 'http' in clean:
        for domain in LEGAL_DOMAINS:
            if domain in clean:
                return True
        return False
        
    # 2. Check for " v. " or " v " pattern (Case Law)
    # Uses \s (whitespace) to correctly match both "v." and "v" followed by space
    if re.search(r'\s(v|vs)\.?\s', clean, re.IGNORECASE):
        return True
        
    # 3. Check for standard citation format (e.g., "347 U.S. 483")
    if re.search(r'\d+\s+[A-Za-z\.]+\s+\d+', clean):
        return True
        
    return False


# ==================== EXTRACTION ====================

def extract_metadata(text):
    """
    Extract legal citation metadata from text or URL.
    
    Routing:
        1. Oyez URLs -> OyezAPI
        2. case.law URLs -> HarvardCAPAPI  
        3. Justia URLs -> JustiaAPI
        4. Text queries -> CourtListenerAPI
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
    
    # === ROUTE 1: Oyez URL ===
    if 'oyez.org' in clean:
        case_data = OyezAPI.fetch(clean)
        if case_data:
            metadata['case_name'] = case_data.get('name', text)
            metadata['url'] = clean
            
            # Extract citation from Oyez response
            citation_obj = case_data.get('citation')
            if citation_obj:
                volume = citation_obj.get('volume', '')
                page = citation_obj.get('page', '')
                if volume and page:
                    metadata['citation'] = f"{volume} U.S. {page}"
                    
            # Extract year from timeline
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
            return metadata
    
    # === ROUTE 2: Harvard CAP (case.law) URL ===
    if 'case.law' in clean:
        citation = HarvardCAPAPI.extract_citation_from_url(clean)
        if citation:
            metadata['citation'] = citation
            metadata['url'] = clean
            
            # Try to get full details from CourtListener
            cl_data = CourtListenerAPI.search(citation)
            if cl_data:
                metadata['case_name'] = cl_data.get('caseName', text)
                metadata['court'] = cl_data.get('court', '')
                date_filed = cl_data.get('dateFiled', '')
                if date_filed:
                    metadata['year'] = date_filed[:4]
            return metadata
    
    # === ROUTE 3: Justia URL ===
    if 'justia.com' in clean:
        extracted = JustiaAPI.extract_from_url(clean)
        if extracted:
            metadata['citation'] = extracted.get('citation', '')
            metadata['court'] = extracted.get('court', '')
            metadata['url'] = clean
            
            # Enrich via CourtListener
            if metadata['citation']:
                cl_data = CourtListenerAPI.search(metadata['citation'])
                if cl_data:
                    metadata['case_name'] = cl_data.get('caseName', text)
                    date_filed = cl_data.get('dateFiled', '')
                    if date_filed:
                        metadata['year'] = date_filed[:4]
            return metadata
    
    # === ROUTE 4: Text Query -> CourtListener ===
    
    # Normalize "v" variations for better API search
    search_query = re.sub(r'\bvs\.?\b', 'v.', clean, flags=re.IGNORECASE)
    
    case_data = CourtListenerAPI.search(search_query)
    
    if case_data:
        metadata['case_name'] = case_data.get('caseName', text)
        metadata['court'] = case_data.get('court', '')
        
        date_filed = case_data.get('dateFiled', '')
        if date_filed: 
            metadata['year'] = date_filed[:4]
            
        citations = case_data.get('citation', [])
        if citations:
            metadata['citation'] = citations[0]
            
    return metadata
