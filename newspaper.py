"""
The Newspaper Engine (newspaper.py) - Extended Edition
- Includes 50+ Major US/Intl Sources.
- Includes 'Archive.org' Backdoor and 'JSON-LD' Parsing.
- Robust error handling for missing libraries.
"""

import re
import json
from datetime import datetime
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse 

# Check for requests library safely
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ==================== DATA: EXPANDED SOURCE MAP ====================

NEWSPAPER_MAP = {
    # --- Major US Newspapers ---
    'nytimes.com': 'The New York Times',
    'washingtonpost.com': 'The Washington Post',
    'wsj.com': 'The Wall Street Journal',
    'usatoday.com': 'USA Today',
    'latimes.com': 'Los Angeles Times',
    'chicagotribune.com': 'Chicago Tribune',
    'bostonglobe.com': 'The Boston Globe',
    'sfchronicle.com': 'San Francisco Chronicle',
    'houstonchronicle.com': 'Houston Chronicle',
    'dallasnews.com': 'The Dallas Morning News',
    'miamiherald.com': 'Miami Herald',
    'seattletimes.com': 'The Seattle Times',
    'denverpost.com': 'The Denver Post',
    'inquirer.com': 'The Philadelphia Inquirer',
    'ajc.com': 'The Atlanta Journal-Constitution',
    'startribune.com': 'Star Tribune',
    'nypost.com': 'New York Post',
    'nydailynews.com': 'New York Daily News',
    'csmonitor.com': 'The Christian Science Monitor',
    'baltimoresun.com': 'The Baltimore Sun',
    'detroitnews.com': 'The Detroit News',
    'freep.com': 'Detroit Free Press',
    
    # --- International & Wires ---
    'theguardian.com': 'The Guardian',
    'ft.com': 'Financial Times',
    'bbc.com': 'BBC News',
    'reuters.com': 'Reuters',
    'apnews.com': 'Associated Press',
    'aljazeera.com': 'Al Jazeera',
    'economist.com': 'The Economist',
    'independent.co.uk': 'The Independent',
    'telegraph.co.uk': 'The Telegraph',
    'thetimes.co.uk': 'The Times',
    'cbc.ca': 'CBC News',
    'scmp.com': 'South China Morning Post',

    # --- Magazines (News, Culture, Politics) ---
    'newyorker.com': 'The New Yorker',
    'theatlantic.com': 'The Atlantic',
    'time.com': 'Time',
    'newsweek.com': 'Newsweek',
    'vanityfair.com': 'Vanity Fair',
    'harpers.org': 'Harper\'s Magazine',
    'nymag.com': 'New York Magazine',
    'rollingstone.com': 'Rolling Stone',
    'slate.com': 'Slate',
    'salon.com': 'Salon',
    'vox.com': 'Vox',
    'vice.com': 'Vice',
    'politico.com': 'Politico',
    'thehill.com': 'The Hill',
    'motherjones.com': 'Mother Jones',
    'nationalreview.com': 'National Review',
    'newrepublic.com': 'The New Republic',
    'jacobin.com': 'Jacobin',
    'reason.com': 'Reason',

    # --- Science, Tech & Business ---
    'wired.com': 'Wired',
    'theverge.com': 'The Verge',
    'techcrunch.com': 'TechCrunch',
    'arstechnica.com': 'Ars Technica',
    'scientificamerican.com': 'Scientific American',
    'nationalgeographic.com': 'National Geographic',
    'popsci.com': 'Popular Science',
    'psychologytoday.com': 'Psychology Today',
    'nature.com': 'Nature',
    'science.org': 'Science',
    'forbes.com': 'Forbes',
    'fortune.com': 'Fortune',
    'businessinsider.com': 'Business Insider',
    'bloomberg.com': 'Bloomberg',
    'hbr.org': 'Harvard Business Review'
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
        'Nyt': 'NYT', 'Wsj': 'WSJ', 'Ceo': 'CEO', 'Cfo': 'CFO',
        'Mit': 'MIT', 'Usa': 'USA', 'Nasa': 'NASA'
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
        pass 

    # --- PARSING LAYER: JSON-LD & META TAGS ---
    if html_content:
        # 1. Try JSON-LD (Best Source)
        try:
            json_match = re.search(r'
