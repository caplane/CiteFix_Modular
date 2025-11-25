"""
The Newspaper Engine (newspaper.py)
- Strategy:
  1. Direct Access: Tries to fetch the live page.
  2. JSON-LD Parsing: Looks for hidden Google/SEO data blocks (high success rate).
  3. ARCHIVE BACKDOOR: If live site fails, checks the Wayback Machine.
  4. Robust Fallback: URL parsing if all else fails.
"""

import requests
import re
import json
from datetime import datetime
from urllib.parse import urlparse

# ==================== DATA: NEWSPAPER MAP ====================

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
    'bloomberg.com': 'Bloomberg',
    'apnews.com': 'Associated Press',
    'reuters.com': 'Reuters',
    'bbc.com': 'BBC News'
}

# ==================== LOGIC: IDENTIFICATION ====================

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

# ==================== LOGIC: EXTRACTION ====================

def extract_metadata(url):
    """
    Extracts metadata using Direct Access, JSON-LD, and Archive.org Fallbacks.
    """
    domain = urlparse(url).netloc.lower().replace('www.', '')
    
    # 1. Identify Newspaper
    pub_name = "Unknown Newspaper"
    for key, val in NEWSPAPER_MAP.items():
        if key in domain:
            pub_name = val
            break
            
    # Initialize with Robust Fallback (URL Parsing) as safety net
    metadata = {
        'type': 'newspaper',
        'author': '', 
        'title': 'Article',
        'newspaper': pub_name,
        'date': datetime.now().strftime("%B %d, %Y"),
        'url': url,
        'access_date': datetime.now().strftime("%B %d, %Y")
    }

    # --- FALLBACK LAYER: URL PARSING (Always runs first) ---
    
    # Date from URL
    date_match = re.search(r'/(\d{4})/(\d{2})/', url) 
    if date_match:
        y, m = date_match.groups()
        day_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        d = 1
        if day_match: d = int(day_
