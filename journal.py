import requests
import re

# ==================== 1. API ENGINES ====================

class SemanticScholarAPI:
    # We now have TWO endpoints
    SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    DETAILS_URL = "https://api.semanticscholar.org/graph/v1/paper/"
    
    # Keep the Mozilla Header - It is working!
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        # If you get an API Key later, you can add it here:
        # 'x-api-key': 'YOUR_KEY_HERE' 
    }

    @staticmethod
    def search_fuzzy(query):
        try:
            # STEP 1: SEARCH (Ask only for safe fields to avoid 400 Error)
            # We removed 'volume', 'issue', 'pages' from here
            search_params = {
                'query': query,
                'limit': 1,
                'fields': 'paperId,title,authors,year,venue,externalIds' 
            }
            
            response = requests.get(SemanticScholarAPI.SEARCH_URL, params=search_params, headers=SemanticScholarAPI.HEADERS, timeout=5)
            
            if response.status_code != 200:
                return {'error': f"Search Error: {response.status_code}"}
                
            data = response.json()
            if data.get('total', 0) == 0:
                return {'error': 'No results found'}
                
            # We found a paper! Now get its ID.
            paper_id = data['data'][0]['paperId']
            
            # STEP 2: GET DETAILS (Ask for Volume, Issue, Pages here)
            details_params = {
                'fields': 'title,authors,venue,year,volume,issue,pages,externalIds'
            }
            
            details_response = requests.get(f"{SemanticScholarAPI.DETAILS_URL}{paper_id}", params=details_params, headers=SemanticScholarAPI.HEADERS, timeout=5)
            
            if details_response.status_code == 200:
                return details_response.json() # Return the full details
            
            # Fallback: If details fail, return what we found in search
            return data['data'][0]
            
        except Exception as e:
            return {'error': f"Connection Error: {str(e)}"}

# ==================== 2. DATA NORMALIZATION ====================

def _init_metadata(text):
    return {
        'type': 'journal', 
        'raw_source': text, 
        'title': 'Unknown Article',
        'journal': '', 
        'authors': [], 
        'year': '', 
        'volume': '', 'issue': '', 'pages': '', 'doi': '', 'url': '', 
        'source_engine': 'None'
    }

def normalize_semantic_scholar(raw_data, original_text):
    metadata = _init_metadata(original_text)
    
    # Extract IDs
    external_ids = raw_data.get('externalIds', {})
    metadata['doi'] = external_ids.get('DOI', '')
    metadata['url'] = f"https://doi.org/{metadata['doi']}" if metadata['doi'] else raw_data.get('url', '')

    # Basic Info
    metadata['title'] = raw_data.get('title', '')
    metadata['journal'] = raw_data.get('venue', '') or raw_data.get('journal', {}).get('name', '')
    metadata['year'] = str(raw_data.get('year', ''))
    
    # The "Deep" Info (Volume/Issue/Pages)
    metadata['volume'] = raw_data.get('volume', '')
    metadata['issue'] = raw_data.get('issue', '')
    metadata['pages'] = raw_data.get('pages', '')
    
    # Authors
    for author in raw_data.get('authors', []):
        metadata['authors'].append(author.get('name', ''))
        
    metadata['source_engine'] = 'Semantic Scholar'
    return metadata

# ==================== 3. MAIN EXPORT ====================

def extract_metadata(text):
    clean_text = text.strip()
    
    # 1. SMART SEARCH (Two-Step)
    raw_semantic = SemanticScholarAPI.search_fuzzy(clean_text)
    
    # If successful (and no error message)
    if raw_semantic and 'error' not in raw_semantic:
        return normalize_semantic_scholar(raw_semantic, text)

    # 2. REPORT FAILURE (For Debugging)
    error_msg = raw_semantic.get('error') if raw_semantic else "Unknown Error"
    
    # Create a dummy result so you can see the error in the UI
    failure_data = _init_metadata(text)
    failure_data['title'] = f"DEBUG: {error_msg}"
    failure_data['source_engine'] = 'Semantic Debugger'
    return failure_data
