import requests
import re

# ==================== 1. API ENGINES ====================

class SemanticScholarAPI:
    SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    DETAILS_URL = "https://api.semanticscholar.org/graph/v1/paper/"
    
    # Mozilla Header (Keep this until you get your API Key)
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    @staticmethod
    def search_fuzzy(query):
        try:
            # STEP 1: SEARCH
            search_params = {
                'query': query,
                'limit': 1,
                'fields': 'paperId,title,authors,year,venue,publicationVenue,externalIds' 
            }
            
            response = requests.get(SemanticScholarAPI.SEARCH_URL, params=search_params, headers=SemanticScholarAPI.HEADERS, timeout=5)
            
            if response.status_code != 200:
                return {'error': f"Search Error: {response.status_code}"}
                
            data = response.json()
            if data.get('total', 0) == 0:
                return {'error': 'No results found'}
                
            # Found it, now get details
            paper_id = data['data'][0]['paperId']
            
            # STEP 2: GET DETAILS
            # We explicitly ask for 'publicationVenue' here
            details_params = {
                'fields': 'title,authors,venue,publicationVenue,year,volume,issue,pages,externalIds'
            }
            
            details_response = requests.get(f"{SemanticScholarAPI.DETAILS_URL}{paper_id}", params=details_params, headers=SemanticScholarAPI.HEADERS, timeout=5)
            
            if details_response.status_code == 200:
                return details_response.json()
            
            return data['data'][0]
            
        except Exception as e:
            return {'error': f"Connection Error: {str(e)}"}

# ==================== 2. DATA NORMALIZATION ====================

def _init_metadata(text):
    return {
        'type': 'journal', 'raw_source': text, 'title': 'Unknown Article',
        'journal': '', 'authors': [], 'year': '', 'volume': '', 'issue': '',
        'pages': '', 'doi': '', 'url': '', 'source_engine': 'None'
    }

def normalize_semantic_scholar(raw_data, original_text):
    metadata = _init_metadata(original_text)
    
    # IDs
    external_ids = raw_data.get('externalIds', {})
    metadata['doi'] = external_ids.get('DOI', '')
    metadata['url'] = f"https://doi.org/{metadata['doi']}" if metadata['doi'] else raw_data.get('url', '')

    # Basic Info
    metadata['title'] = raw_data.get('title', '')
    metadata['year'] = str(raw_data.get('year', ''))
    
    # --- JOURNAL NAME FIX ---
    # 1. Try 'venue' (Standard)
    # 2. Try 'publicationVenue.name' (Deep)
    # 3. Try 'journal.name' (Old style)
    venue = raw_data.get('venue', '')
    pub_venue = raw_data.get('publicationVenue', {})
    
    if pub_venue and isinstance(pub_venue, dict):
        venue = pub_venue.get('name', venue)
    
    metadata['journal'] = venue
    # ------------------------

    metadata['volume'] = raw_data.get('volume', '')
    metadata['issue'] = raw_data.get('issue', '')
    metadata['pages'] = raw_data.get('pages', '')
    
    for author in raw_data.get('authors', []):
        metadata['authors'].append(author.get('name', ''))
        
    metadata['source_engine'] = 'Semantic Scholar'
    return metadata

# ==================== 3. MAIN EXPORT ====================

def extract_metadata(text):
    # 1. CLEAN THE INPUT
    # Remove punctuation for better fuzzy matching
    clean_text = re.sub(r'[^\w\s]', '', text).strip()
    
    # 2. RUN SEARCH
    raw_semantic = SemanticScholarAPI.search_fuzzy(clean_text)
    
    if raw_semantic and 'error' not in raw_semantic:
        return normalize_semantic_scholar(raw_semantic, text)

    # 3. REPORT FAILURE
    error_msg = raw_semantic.get('error') if raw_semantic else "Unknown Error"
    
    failure_data = _init_metadata(text)
    failure_data['title'] = f"DEBUG: {error_msg} (Query: {clean_text})"
    failure_data['source_engine'] = 'Semantic Debugger'
    return failure_data
