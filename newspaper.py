"""
The Newspaper Engine (newspaper.py)
- Hybrid Strategy:
  1. Tries to fetch the page and regex-search for Author metadata.
  2. FALLBACK: Always parses URL if fetching fails (anti-bot blocks).
  3. CLEANUP: Fixes capitalization for common acronyms (FDA, SSRI, etc).
"""

import requests
import re
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

    # 2. Extract Date from URL (Robust Fallback)
    # Look for patterns like /2025/07/21/ or /2025/07/
    date_match = re.search(r'/(\d{4})/(\d{2})/', url) 
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
    
    # 3. Extract Title from URL Slug (Robust Fallback)
    path = urlparse(url).path
    if path.endswith('/'): path = path[:-1]
    if path.endswith('.html'): path = path[:-5]
    
    slug = path.split('/')[-1]
    # Filter out numeric IDs at end of slug (common in CMS)
    if slug.isdigit() or (len(slug) < 4 and len(path.split('/')) > 1):
        slug = path.split('/')[-2] 
        
    clean_slug = slug.replace('-', ' ').title()
    
    # --- PATCH: Fix Acronyms in Slug Title ---
    replacements = {
        'Ssri': 'SSRI', 'Fda': 'FDA', 'Us': 'US', 'Uk': 'UK', 
        'Ai': 'AI', 'Llm': 'LLM', 'Gpt': 'GPT', 'Dna': 'DNA',
        'Nyt': 'NYT', 'Wsj': 'WSJ', 'Ceo': 'CEO', 'Cfo': 'CFO'
    }
    for wrong, right in replacements.items():
        # Replace whole words only
        clean_slug = re.sub(r'\b' + wrong + r'\b', right, clean_slug)
        
    if clean_slug:
        metadata['title'] = clean_slug

    # 4. Attempt Lightweight Scraping for Author (The "Bonus Step")
    try:
        # Use a real browser User-Agent to bypass basic anti-bot screens
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.google.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            html = response.text
            
            # Regex search for meta author tags (byl, author, dc.creator)
            author_match = re.search(r'<meta\s+name=["\'](?:byl|author|dc.creator|bylines)["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            
            # Check OpenGraph author as backup
            if not author_match:
                author_match = re.search(r'<meta\s+property=["\']article:author["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)

            if author_match:
                author_text = author_match.group(1)
                # Clean up "By John Doe" -> "John Doe"
                if author_text.lower().startswith("by "):
                    author_text = author_text[3:]
                metadata['author'] = author_text.strip()
                
            # If we got the page, try to improve the title using OpenGraph
            og_title = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if og_title:
                real_title = og_title.group(1).split('|')[0].strip() # Remove "| NYT" suffix
                metadata['title'] = real_title

    except Exception as e:
        # Silently fail back to the URL-derived data
        print(f"Scraping skipped for {url}: {e}")

    return metadata
