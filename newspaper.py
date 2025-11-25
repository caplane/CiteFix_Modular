import requests
import re
from datetime import datetime
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

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
    Visits the URL to scrape metadata tags for Author, Title, and Date.
    """
    # 1. Identify Newspaper Name
    domain = urlparse(url).netloc.lower().replace('www.', '')
    pub_name = "Unknown Newspaper"
    for key, val in NEWSPAPER_MAP.items():
        if key in domain:
            pub_name = val
            break

    # Default values (if scraping fails)
    metadata = {
        'type': 'newspaper',
        'author': '',
        'title': 'Article',
        'newspaper': pub_name,
        'date': datetime.now().strftime("%B %d, %Y"),
        'url': url,
        'access_date': datetime.now().strftime("%B %d, %Y")
    }

    # 2. Try Scraping if BeautifulSoup is available
    if BeautifulSoup:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; CiteFix/1.0)'}
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # --- AUTHOR EXTRACTION ---
                # NYT uses 'byl', others use 'author'
                author_tag = soup.find("meta", {"name": "byl"})
                if not author_tag:
                    author_tag = soup.find("meta", {"name": "author"})
                
                if author_tag and author_tag.get("content"):
                    clean_author = author_tag["content"]
                    # Remove "By " prefix if present
                    if clean_author.lower().startswith("by "):
                        clean_author = clean_author[3:]
                    metadata['author'] = clean_author

                # --- TITLE EXTRACTION ---
                title_tag = soup.find("meta", property="og:title")
                if title_tag and title_tag.get("content"):
                    metadata['title'] = title_tag["content"]
                
                # --- DATE EXTRACTION ---
                # Try meta tag first
                date_tag = soup.find("meta", property="article:published_time")
                if date_tag and date_tag.get("content"):
                    dt_str = date_tag["content"][:10] # Get YYYY-MM-DD
                    try:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d")
                        metadata['date'] = dt.strftime("%B %d, %Y")
                    except: pass
                else:
                    # Fallback to URL date parsing
                    date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
                    if date_match:
                        y, m, d = date_match.groups()
                        dt = datetime(int(y), int(m), int(d))
                        metadata['date'] = dt.strftime("%B %d, %Y")

        except Exception as e:
            print(f"Scraping failed for {url}: {e}")
    
    # If scraping failed, fallback to URL parsing for title
    if metadata['title'] == 'Article':
        path = urlparse(url).path
        if path.endswith('.html'): path = path[:-5]
        slug = path.split('/')[-1]
        metadata['title'] = slug.replace('-', ' ').title()

    return metadata
