"""
The Newspaper Engine (newspaper.py) - Safe Deployment Version
- Includes 'Archive.org' Backdoor and 'JSON-LD' Parsing.
- Robust error handling for missing libraries.
- Strict indentation to prevent syntax errors.
"""

import re
import json
from datetime import datetime
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse # Python 2 fallback

# Check for requests library safely
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

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
            
    # Initialize with Robust Fallback (URL Parsing)
    metadata = {
        'type': 'newspaper',
        'author': '', 
        'title': 'Article',
        'newspaper': pub_name,
        'date': datetime.now().strftime("%B %d, %Y"),
        'url': url,
        'access_date': datetime.now().strftime("%B %d, %Y")
    }

    # --- FALLBACK 1: URL PARSING (Always runs first) ---
    
    # Date from URL
    date_match = re.search(r'/(\d{4})/(\d{2})/', url) 
    if date_match:
        y, m = date_match.groups()
        day_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        d = 1
        if day_match: d = int(day_match.group(3))
        try:
            dt = datetime(int(y), int(m), int(d))
            metadata['date'] = dt.strftime("%B %d, %Y")
        except: pass
    
    # Title from URL Slug
    path = urlparse(url).path
    if path.endswith('/'): path = path[:-1]
    if path.endswith('.html'): path = path[:-5]
    slug = path.split('/')[-1]
    
    if slug.isdigit() or (len(slug) < 4 and len(path.split('/')) > 1):
        slug = path.split('/')[-2] 
        
    clean_slug = slug.replace('-', ' ').title()
    
    # Fix Acronyms
    replacements = {
        'Ssri': 'SSRI', 'Fda': 'FDA', 'Us': 'US', 'Uk': 'UK', 
        'Ai': 'AI', 'Llm': 'LLM', 'Gpt': 'GPT', 'Dna': 'DNA',
        'Nyt': 'NYT', 'Wsj': 'WSJ', 'Ceo': 'CEO', 'Cfo': 'CFO'
    }
    for wrong, right in replacements.items():
        clean_slug = re.sub(r'\b' + wrong + r'\b', right, clean_slug)
        
    if clean_slug:
        metadata['title'] = clean_slug

    # --- ACTIVE LAYER: SCRAPING (Only if requests is installed) ---
    if not REQUESTS_AVAILABLE:
        return metadata

    html_content = None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    try:
        # A. Try Direct Access
        response = requests.get(url, headers=headers, timeout=5)
        
        # B. If Blocked (403/429), Try Archive.org (The Backdoor)
        if response.status_code in [403, 429, 451]:
            archive_api = "http://archive.org/wayback/available?url=" + url
            arch_res = requests.get(archive_api, timeout=3).json()
            
            if arch_res.get('archived_snapshots', {}).get('closest'):
                snapshot_url = arch_res['archived_snapshots']['closest']['url']
                response = requests.get(snapshot_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            html_content = response.text

    except Exception:
        pass # Silently fail back to URL data

    # --- PARSING LAYER: JSON-LD & META TAGS ---
    if html_content:
        # 1. Try JSON-LD (Best Source)
        try:
            json_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html_content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                if isinstance(data, list): 
                    if len(data) > 0: data = data[0]
                    else: data = {}
                
                # Extract Author
                if 'author' in data:
                    authors = data['author']
                    if isinstance(authors, list):
                        names = [p.get('name') for p in authors if isinstance(p, dict) and 'name' in p]
                        if names: metadata['author'] = " and ".join(names)
                    elif isinstance(authors, dict):
                        if 'name' in authors: metadata['author'] = authors['name']
                
                # Extract Title
                if 'headline' in data:
                    metadata['title'] = data['headline']
                    
                # Extract Date
                if 'datePublished' in data and data['datePublished']:
                    dp = str(data['datePublished'])[:10]
                    try:
                        dt = datetime.strptime(dp, "%Y-%m-%d")
                        metadata['date'] = dt.strftime("%B %d, %Y")
                    except: pass
        except: pass

        # 2. Fallback to Meta Tags
        if not metadata['author']:
            try:
                author_match = re.search(r'<meta\s+name=["\'](?:byl|author|dc.creator|bylines)["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
                if not author_match:
                    author_match = re.search(r'<meta\s+property=["\']article:author["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)

                if author_match:
                    author_text = author_match.group(1)
                    if author_text.lower().startswith("by "):
                        author_text = author_text[3:]
                    metadata['author'] = author_text.strip()
                    
                og_title = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
                if og_title:
                    real_title = og_title.group(1).split('|')[0].strip()
                    metadata['title'] = real_title
            except: pass

    return metadata
