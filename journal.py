import requests
import re

# ==================== 1. API ENGINES ====================

class CrossRefAPI:
    BASE_URL = "https://api.crossref.org/works"
    # FIX: Use a standard Browser Header to avoid being blocked
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

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
            params = {
                'query.bibliographic': query,
                'rows': 1,
                'select': 'title,author,container-title,volume,issue,page,published-print,published-online,DOI'
            }
            response = requests.get(CrossRefAPI.BASE_URL, params=params, headers=CrossRefAPI.HEADERS, timeout=5)
            return response.json().get('message', {}).get('items', [])[0] if response.status_code == 200 else None
        except: return None

class SemanticScholarAPI:
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    # FIX: Use the same "Real Browser" header here
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    @staticmethod
    def search_fuzzy(query):
        try:
            params = {
                'query': query,
                'limit': 1,
                'fields': 'title,authors,venue,year,volume,issue,pages,externalIds'
            }
            response = requests.get(SemanticScholarAPI.BASE_URL, params=params, headers=SemanticScholarAPI.HEADERS, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('total', 0) > 0:
                    return data['data'][0]
            # Debug: If you want to verify failure, you could print(response.status_code) here locally
            return None
        except: return None

# ==================== 2. DATA NORMALIZATION ====================

def _init_metadata(text):
    return {
        'type': 'journal', 'raw_source': text, 'title': 'Unknown Article',
        'journal': '', 'authors': [], 'year': '', 'volume': '', 'issue': '',
        'pages': '', 'doi': '', 'url': '', 'source_engine': 'None'
    }

def normalize_crossref(raw_data, original_text):
    metadata = _init_metadata(original_text)
    metadata['doi'] = raw_data.get('DOI', '')
    metadata['url'] = f"https://doi.org/{metadata['doi']}" if metadata['doi'] else ''
    
    titles = raw_data.get('title', [])
    if titles: metadata['title'] = titles[0]
    
    journals = raw_data.get('container-title', [])
    if journals: metadata['journal'] = journals[0]
    
    if 'author' in raw_data:
        for auth in raw_data['author']:
            given = auth.get('given', '')
            family = auth.get('family', '')
            metadata['authors'].append(f"{given} {family}".strip())
            
    metadata['volume'] = raw_data.get('volume', '')
    metadata['issue'] = raw_data.get('issue', '')
    metadata['pages'] = raw_data.get('page', '')
    
    dp = raw_data.get('published-print', {}).get('date-parts')
    if not dp: dp = raw_data.get('published-online', {}).get('date-parts')
    if dp and len(dp) > 0: metadata['year'] = str(dp[0][0])
    
    metadata['source_engine'] = 'CrossRef'
    return metadata

def normalize_semantic_scholar(raw_data, original_text):
    metadata = _init_metadata(original_text)
    metadata['doi'] = raw_data.get('externalIds', {}).get('DOI', '')
    metadata['url'] = f"https://doi.org/{metadata['doi']}" if metadata['doi'] else ''
    metadata['title'] = raw_data.get('title', '')
    metadata['journal'] = raw_data.get('venue', '')
    metadata['year'] = str(raw_data.get('year', ''))
    metadata['volume'] = raw_data.get('volume', '')
    metadata['issue'] = raw_data.get('issue', '')
    metadata['pages'] = raw_data.get('pages', '')
    
    for author in raw_data.get('authors', []):
        metadata['authors'].append(author.get('name', ''))
        
    metadata['source_engine'] = 'Semantic Scholar'
    return metadata

# ==================== 3. MAIN EXPORT ====================

def extract_metadata(text):
    clean_text = text.strip()
    
    # 1. DOI Check
    doi_match = re.search(r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b', clean_text, re.IGNORECASE)
    if doi_match:
        raw = CrossRefAPI.get_by_doi(doi_match.group(1))
        if raw: return normalize_crossref(raw, text)

    # 2. Smart Search (Semantic Scholar) - Catches "Caplan trains"
    raw_semantic = SemanticScholarAPI.search_fuzzy(clean_text)
    if raw_semantic:
        return normalize_semantic_scholar(raw_semantic, text)

    # 3. Literal Search (CrossRef) - Fallback
    raw_crossref = CrossRefAPI.search_query(clean_text)
    if raw_crossref:
        return normalize_crossref(raw_crossref, text)

    return _init_metadata(text)
