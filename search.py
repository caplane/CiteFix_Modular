import requests
import re

# ==================== 1. API ENGINES ====================

class SemanticScholarAPI:
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    # We use the Mozilla header to try and bypass the block
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
            # Print status to logs if you could see them, but we rely on the return value
            response = requests.get(SemanticScholarAPI.BASE_URL, params=params, headers=SemanticScholarAPI.HEADERS, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('total', 0) > 0:
                    return data['data'][0]
                return {'error': 'API returned 0 results'}
            
            # Return the specific error code (e.g., 403 Forbidden)
            return {'error': f"API Status: {response.status_code}"}
            
        except Exception as e:
            return {'error': f"Connection Error: {str(e)}"}

# ==================== 2. DATA NORMALIZATION ====================

def _init_metadata(text):
    # This acts as our "Blank/Error" template
    return {
        'type': 'journal', 
        'raw_source': text, 
        'title': 'STRICT MODE: No Result Found',
        'journal': 'Debug Log', 
        'authors': [], 
        'year': '0000', 
        'volume': '', 
        'issue': '',
        'pages': '', 
        'doi': '', 
        'url': '', 
        'source_engine': 'None'
    }

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
        
    metadata['source_engine'] = 'Semantic Scholar (Strict)'
    return metadata

# ==================== 3. MAIN EXPORT ====================

def extract_metadata(text):
    clean_text = text.strip()
    
    # 1. SEMANTIC SCHOLAR ONLY
    # We removed CrossRef entirely for this test.
    raw_semantic = SemanticScholarAPI.search_fuzzy(clean_text)
    
    # If we got a real result (and it's not an error object)
    if raw_semantic and 'error' not in raw_semantic:
        return normalize_semantic_scholar(raw_semantic, text)

    # 2. REPORT FAILURE
    # If we are here, Semantic Scholar failed. We return the specific error.
    error_msg = raw_semantic.get('error') if raw_semantic else "Unknown Error"
    
    failure_data = _init_metadata(text)
    failure_data['title'] = f"FAILURE: {error_msg}"
    failure_data['source_engine'] = 'Semantic Debugger'
    return failure_data
