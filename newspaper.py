"""
The Newspaper Engine (newspaper.py)
- Hybrid Strategy:
  1. Tries to fetch the page and regex-search for Author metadata.
  2. CRITICAL UPDATE: Always falls back to URL parsing if fetching fails.
  3. Ensures a valid result is returned even for 404s or blocked sites.
"""

import requests
import re
from datetime import datetime
from urllib.parse import urlparse

NEWSPAPER_MAP = {
    'nytimes.com': 'The New York Times',
    'washingtonpost.com': 'The Washington Post',
    'wsj.com': 'The Wall Street Journal',
    'theguardian.com': 'The Guardian',
    'ft.com': 'Financial Times',
    'latimes.com': 'Los Angeles Times',
    'chicagotribune.com': 'Chicago Tribune',
    'newyorker.com': 'The New Yorker',
    'theatlantic.com': 'The Atlantic',
}

def is_newspaper_url(text):
    """Check if URL matches a known newspaper domain"""
    if not text: return False
    try:
        domain = urlparse(text).netloc.lower().replace('www.', '')
        for news_domain in NEWSPAPER_MAP:
            if news_domain in domain:
                return True
    except: pass
    return False

def extract_metadata(url):
    """
    Extracts metadata using lightweight regex scraping with strong fallbacks.
    """
    domain = urlparse(url).netloc.lower().replace('www.', '')
    
    # 1. Identify Newspaper
    pub_name = "Unknown Newspaper"
    for key, val in NEWSPAPER_MAP.items():
        if key in domain:
            pub_name = val
            break
            
    # Initialize with default/fallback data derived purely from URL
    metadata = {
        'type': 'newspaper',
        'author': '',
        'title': 'Article',
        'newspaper': pub_name,
        'date': datetime.now().strftime("%B %d, %Y"),
        'url': url,
        'access_date': datetime.now().strftime("%B %d, %Y")
    }

    # 2. Extract Date & Title from URL (The Robust Fallback)
    # Date logic: Look for /YYYY/MM/DD/ or /YYYY/MM/
    date_match = re.search(r'/(\d{4})/(\d{2})/', url) # Matches /2026/01/
    if date_match:
        y, m = date_match.groups()
        # Default to 1st of month if day is missing
        day_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        d = 1
        if day_match:
            d = int(day_match.group(3))
            
        try:
            dt = datetime(int(y), int(m), int(d))
            metadata['date'] = dt.strftime("%B %d, %Y")
        except: pass
    
    # Title from URL Slug
    path = urlparse(url).path
    if path.endswith('/'): path = path[:-1] # Remove trailing slash
    if path.endswith('.html'): path = path[:-5]
    
    slug = path.split('/')[-1]
    # Convert "sam-shepard-coyote-biography" -> "Sam Shepard Coyote Biography"
    # Filter out numeric IDs at end of slug if present
    if slug.isdigit():
        slug = path.split('/')[-2] # Go up one level if it ends in ID
        
    clean_slug = slug.replace('-', ' ').title()
    if clean_slug:
        metadata['title'] = clean_slug

    # 3. Attempt Lightweight Scraping for Author (Bonus Step)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; CiteFix/1.0)'}
        response = requests.get(url, headers=headers, timeout=3)
        
        if response.status_code == 200:
            html = response.text
            
            # Regex search for meta author tag
            author_match = re.search(r'<meta\s+name=["\'](?:byl|author)["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            
            if author_match:
                author_text = author_match.group(1)
                if author_text.lower().startswith("by "):
                    author_text = author_text[3:]
                metadata['author'] = author_text
                
            # If we got the page, try to get the real title too
            og_title = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if og_title:
                metadata['title'] = og_title.group(1)

    except Exception as e:
        # If scraping fails, we just silently stick with the URL-derived data
        print(f"Scraping failed for {url}: {e}")

    return metadata
