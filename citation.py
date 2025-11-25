"""
The Book Engine (citation.py)
- Now extracts MULTIPLE candidates (Top 3) from Google Books.
"""

import requests
import re

# ... (PUBLISHER_PLACE_MAP remains the same) ...
PUBLISHER_PLACE_MAP = {
    'Harvard University Press': 'Cambridge, MA',
    'MIT Press': 'Cambridge, MA',
    'Yale University Press': 'New Haven',
    'Princeton University Press': 'Princeton',
    'Stanford University Press': 'Stanford',
    'University of California Press': 'Berkeley',
    'University of Chicago Press': 'Chicago',
    'Columbia University Press': 'New York',
    'Oxford University Press': 'Oxford',
    'Cambridge University Press': 'Cambridge',
    'Penguin': 'New York',
    'Random House': 'New York',
    'HarperCollins': 'New York',
    'Simon & Schuster': 'New York',
    'Farrar, Straus and Giroux': 'New York',
    'W. W. Norton': 'New York',
    'Knopf': 'New York'
}

class GoogleBooksAPI:
    BASE_URL = "https://www.googleapis.com/books/v1/volumes"
    
    @staticmethod
    def clean_search_term(text):
        if text.startswith(('http://', 'https://', 'www.')):
            return text
        text = re.sub(r'^\s*\d+\.?\s*', '', text)
        text = re.sub(r',?\s*pp?\.?\s*\d+(-\d+)?\.?$', '', text)
        text = re.sub(r',?\s*\d+\.?$', '', text)
        return text.strip()

    @staticmethod
    def search(query):
        if not query: return []
        try:
            cleaned_query = GoogleBooksAPI.clean_search_term(query)
            # FETCH 3 RESULTS INSTEAD OF 1
            params = {'q': cleaned_query, 'maxResults': 3, 'printType': 'books', 'orderBy': 'relevance'}
            response = requests.get(GoogleBooksAPI.BASE_URL, params=params, timeout=5)
            if response.status_code == 200:
                return response.json().get('items', [])
        except Exception:
            pass
        return []

def extract_metadata(text):
    """
    Returns a LIST of metadata dictionaries (Candidates).
    """
    items = GoogleBooksAPI.search(text)
    candidates = []
    
    if not items:
        return []

    for item in items:
        info = item.get('volumeInfo', {})
        
        authors = info.get('authors', [])
        title = info.get('title', '')
        if info.get('subtitle'):
            title = f"{title}: {info.get('subtitle')}"
            
        publisher = info.get('publisher', '')
        date_str = info.get('publishedDate', '')
        year = date_str.split('-')[0] if date_str else ''
        
        place = ''
        for pub_name, pub_place in PUBLISHER_PLACE_MAP.items():
            if pub_name.lower() in publisher.lower():
                place = pub_place
                break

        candidates.append({
            'type': 'book',
            'authors': authors,
            'title': title,
            'publisher': publisher,
            'place': place,
            'year': year,
            'raw_source': text
        })

    return candidates
