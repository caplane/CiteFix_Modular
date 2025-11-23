"""
The Book Engine (citation.py)
Acts as a 'Specialist'.
- Knows the Publisher Map.
- Knows how to talk to Google Books.
- Extracts Author, Title, Publisher, Year.
- DOES NOT Format.
"""

import requests
import re

# ==================== DATA: PUBLISHER MAP ====================
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
        if not query: return None
        try:
            cleaned_query = GoogleBooksAPI.clean_search_term(query)
            params = {'q': cleaned_query, 'maxResults': 1, 'printType': 'books', 'orderBy': 'relevance'}
            response = requests.get(GoogleBooksAPI.BASE_URL, params=params, timeout=5)
            if response.status_code == 200:
                items = response.json().get('items', [])
                if items:
                    return items[0] # Return best match
        except Exception:
            pass
        return None

def extract_metadata(text):
    """
    Extracts RAW DATA for a Book.
    """
    book_data = GoogleBooksAPI.search(text)
    
    if not book_data:
        return {
            'type': 'unknown',
            'raw_source': text
        }

    info = book_data.get('volumeInfo', {})
    
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

    # Return PURE DATA dictionary
    return {
        'type': 'book',
        'authors': authors,
        'title': title,
        'publisher': publisher,
        'place': place,
        'year': year,
        'raw_source': text
    }
