"""
Legal Citation Engine (Production V14 - Zotero Integrated)
Features:
- Auto-Correct: Fixes typos ("Row v Wade" -> "Roe v Wade") using Fuzzy Matching.
- Universal URL Logic: Reads any URL containing 'court', 'opinion', 'case'.
- Layer 1: Massive Local Cache (State, Federal, SCOTUS).
- Layer 2: Zotero/Juris-M Personal Library (NEW).
- Layer 3: Stealth API (CourtListener).
"""

import requests
import re
import sys
import time
import os
import difflib
from urllib.parse import urlparse, unquote

# ==================== HELPER: AGGRESSIVE NORMALIZER ====================
def normalize_key(text):
    text = text.lower()
    text = text.replace('.', '').replace(',', '').replace(':', '').replace(';', '')
    text = re.sub(r'\b(vs|versus)\b', 'v', text)
    return " ".join(text.split())

# ==================== HELPER: DEBUG LOGGING ====================
def debug_log(message):
    print(f"[COURT.PY] {message}", file=sys.stderr, flush=True)

# ==================== HELPER: FUZZY MATCHING (The Spell Checker) ====================
def find_best_cache_match(text):
    clean_key = normalize_key(text)
    if clean_key in FAMOUS_CASES: return clean_key
    matches = difflib.get_close_matches(clean_key, FAMOUS_CASES.keys(), n=1, cutoff=0.8)
    if matches:
        suggestion = matches[0]
        debug_log(f"Auto-Corrected: '{text}' -> '{suggestion}'")
        return suggestion
    return None

# ==================== HELPER: SMART SLUG EXTRACTION ====================
def extract_query_from_url(url):
    try:
        decoded_url = unquote(url)
        parsed = urlparse(decoded_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        if not path_parts: return ""
        slug = path_parts[-1]
        slug = re.sub(r'\.(htm|html|pdf|aspx|php|jsp)$', '', slug, flags=re.IGNORECASE)
        slug = slug.replace('_', ' ').replace('-', ' ').replace('+', ' ')
        slug = re.sub(r'(?<!^)(?=[A-Z])', ' ', slug)
        return slug.strip()
    except:
        return ""

# ==================== LAYER 1: THE MASSIVE CACHE ====================

FAMOUS_CASES = {
    # --- ALIASES FOR URL MATCHING ---
    'palsgraf lirr': {'case_name': 'Palsgraf v. Long Island R.R. Co.', 'citation': '248 N.Y. 339', 'year': '1928', 'court': 'N.Y.'},

    # --- STATE COURT CLASSICS ---
    'palsgraf v long island railroad': {'case_name': 'Palsgraf v. Long Island R.R. Co.', 'citation': '248 N.Y. 339', 'year': '1928', 'court': 'N.Y.'},
    'macpherson v buick': {'case_name': 'MacPherson v. Buick Motor Co.', 'citation': '217 N.Y. 382', 'year': '1916', 'court': 'N.Y.'},
    'people v goetz': {'case_name': 'People v. Goetz', 'citation': '68 N.Y.2d 96', 'year': '1986', 'court': 'N.Y.'},
    'jacob and youngs v kent': {'case_name': 'Jacob & Youngs, Inc. v. Kent', 'citation': '230 N.Y. 239', 'year': '1921', 'court': 'N.Y.'},
    'tarasoff v regents': {'case_name': 'Tarasoff v. Regents of the University of California', 'citation': '17 Cal. 3d 425', 'year': '1976', 'court': 'Cal.'},
    'grimshaw v ford motor co': {'case_name': 'Grimshaw v. Ford Motor Co.', 'citation': '119 Cal. App. 3d 757', 'year': '1981', 'court': 'Cal. Ct. App.'},
    'people v turner': {'case_name': 'People v. Turner', 'citation': 'No. 15014799', 'year': '2016', 'court': 'Cal. Super. Ct.'},
    'hawkins v mcgee': {'case_name': 'Hawkins v. McGee', 'citation': '84 N.H. 114', 'year': '1929', 'court': 'N.H.'},
    'lucy v zehmer': {'case_name': 'Lucy v. Zehmer', 'citation': '196 Va. 493', 'year': '1954', 'court': 'Va.'},
    'sherwood v walker': {'case_name': 'Sherwood v. Walker', 'citation': '66 Mich. 568', 'year': '1887', 'court': 'Mich.'},
    'in re quinlan': {'case_name': 'In re Quinlan', 'citation': '355 A.2d 647', 'year': '1976', 'court': 'N.J.'},
    'in re baby m': {'case_name': 'In re Baby M', 'citation': '537 A.2d 1227', 'year': '1988', 'court': 'N.J.'},
    'commonwealth v hunt': {'case_name': 'Commonwealth v. Hunt', 'citation': '45 Mass. 111', 'year': '1842', 'court': 'Mass.'},

    # --- FEDERAL DISTRICT COURTS ---
    'a&m records v napster': {'case_name': 'A&M Records, Inc. v. Napster, Inc.', 'citation': '114 F. Supp. 2d 896', 'year': '2000', 'court': 'N.D. Cal.'},
    'kitzmiller v dover': {'case_name': 'Kitzmiller v. Dover Area School Dist.', 'citation': '400 F. Supp. 2d 707', 'year': '2005', 'court': 'M.D. Pa.'},
    'kitzmiller': {'case_name': 'Kitzmiller v. Dover Area School Dist.', 'citation': '400 F. Supp. 2d 707', 'year': '2005', 'court': 'M.D. Pa.'},
    'floyd v city of new york': {'case_name': 'Floyd v. City of New York', 'citation': '959 F. Supp. 2d 540', 'year': '2013', 'court': 'S.D.N.Y.'},
    'jones v clinton': {'case_name': 'Jones v. Clinton', 'citation': '990 F. Supp. 657', 'year': '1998', 'court': 'E.D. Ark.'},
    'united states v oliver north': {'case_name': 'United States v. North', 'citation': '708 F. Supp. 380', 'year': '1988', 'court': 'D.D.C.'},

    # --- FEDERAL CIRCUITS (With Corporate Aliases) ---
    'united states v microsoft': {'case_name': 'United States v. Microsoft Corp.', 'citation': '253 F.3d 34', 'year': '2001', 'court': 'D.C. Cir.'},
    'united states v microsoft corp': {'case_name': 'United States v. Microsoft Corp.', 'citation': '253 F.3d 34', 'year': '2001', 'court': 'D.C. Cir.'},
    'buckley v valeo': {'case_name': 'Buckley v. Valeo', 'citation': '519 F.2d 821', 'year': '1975', 'court': 'D.C. Cir.'},
    'massachusetts v epa': {'case_name': 'Massachusetts v. EPA', 'citation': '415 F.3d 50', 'year': '2005', 'court': 'D.C. Cir.'},
    'united states v carroll towing': {'case_name': 'United States v. Carroll Towing Co.', 'citation': '159 F.2d 169', 'year': '1947', 'court': '2d Cir.'},
    'authors guild v google': {'case_name': 'Authors Guild v. Google, Inc.', 'citation': '804 F.3d 202', 'year': '2015', 'court': '2d Cir.'},
    'viacom v youtube': {'case_name': 'Viacom Int\'l, Inc. v. YouTube, Inc.', 'citation': '676 F.3d 19', 'year': '2012', 'court': '2d Cir.'},
    'newdow v us congress': {'case_name': 'Newdow v. U.S. Congress', 'citation': '292 F.3d 597', 'year': '2002', 'court': '9th Cir.'},
    'lenz v universal music': {'case_name': 'Lenz v. Universal Music Corp.', 'citation': '815 F.3d 1145', 'year': '2016', 'court': '9th Cir.'},
    'lenz v universal music corp': {'case_name': 'Lenz v. Universal Music Corp.', 'citation': '815 F.3d 1145', 'year': '2016', 'court': '9th Cir.'},
    'state street bank v signature financial': {'case_name': 'State St. Bank & Trust Co. v. Signature Fin. Group', 'citation': '149 F.3d 1368', 'year': '1998', 'court': 'Fed. Cir.'},

    # --- HIRSCHKOP / SCOTUS / PROCEDURAL ---
    'roe v wade': {'case_name': 'Roe v. Wade', 'citation': '410 U.S. 113', 'year': '1973', 'court': 'Supreme Court of the United States'},
    'brown v board': {'case_name': 'Brown v. Board of Education', 'citation': '347 U.S. 483', 'year': '1954', 'court': 'Supreme Court of the United States'},
    'loving v virginia': {'case_name': 'Loving v. Virginia', 'citation': '388 U.S. 1', 'year': '1967', 'court': 'Supreme Court of the United States'},
    'osheroff v chestnut lodge': {'case_name': 'Osheroff v. Chestnut Lodge', 'citation': '490 A.2d 720', 'year': '1985', 'court': 'Md. Ct. Spec. App.'},
    'in re gault': {'case_name': 'In re Gault', 'citation': '387 U.S. 1', 'year': '1967', 'court': 'Supreme Court of the United States'},
    'in re winship': {'case_name': 'In re Winship', 'citation': '397 U.S. 358', 'year': '1970', 'court': 'Supreme Court of the United States'},
    'in re yamashita': {'case_name': 'In re Yamashita', 'citation': '327 U.S. 1', 'year': '1946', 'court': 'Supreme Court of the United States'},
    'ex parte milligan': {'case_name': 'Ex parte Milligan', 'citation': '71 U.S. 2', 'year': '1866', 'court': 'Supreme Court of the United States'},
    'ex parte young': {'case_name': 'Ex parte Young', 'citation': '209 U.S. 123', 'year': '1908', 'court': 'Supreme Court of the United States'},
    'cohen v chesterfield': {'case_name': 'Cleveland Bd. of Educ. v. LaFleur', 'citation': '414 U.S. 632', 'year': '1974', 'court': 'Supreme Court of the United States'},
    'landman v royster': {'case_name': 'Landman v. Royster', 'citation': '333 F. Supp. 621', 'year': '1971', 'court': 'E.D. Va.'},
    'kirstein v rector': {'case_name': 'Kirstein v. Rector and Visitors of Univ. of Va.', 'citation': '309 F. Supp. 184', 'year': '1970', 'court': 'E.D. Va.'},
    'koehl v resor': {'case_name': 'Koehl v. Resor', 'citation': '296 F. Supp. 558', 'year': '1969', 'court': 'E.D. Va.'},
    'hirschkop v snead': {'case_name': 'Hirschkop v. Snead', 'citation': '594 F.2d 356', 'year': '1979', 'court': '4th Cir.'},
    'jeannette rankin brigade v chief': {'case_name': 'Jeannette Rankin Brigade v. Chief of Capitol Police', 'citation': '342 F. Supp. 575', 'year': '1972', 'court': 'D.D.C.'},
    'washington mobilization committee v cullinane': {'case_name': 'Washington Mobilization Comm. v. Cullinane', 'citation': '566 F.2d 107', 'year': '1977', 'court': 'D.C. Cir.'},
    'patler v slayton': {'case_name': 'Patler v. Slayton', 'citation': '503 F.2d 472', 'year': '1974', 'court': '4th Cir.'},
    'scarborough v united states': {'case_name': 'Scarborough v. United States', 'citation': '431 U.S. 563', 'year': '1977', 'court': 'Supreme Court of the United States'},
    'johnson v branch': {'case_name': 'Johnson v. Branch', 'citation': '364 F.2d 177', 'year': '1966', 'court': '4th Cir.'},
    'united states v digirlomo': {'case_name': 'United States v. DiGirlomo', 'citation': '548 F.2d 252', 'year': '1977', 'court': '8th Cir.'},
    'marbury v madison': {'case_name': 'Marbury v. Madison', 'citation': '5 U.S. 137', 'year': '1803', 'court': 'Supreme Court of the United States'},
    'mcculloch v maryland': {'case_name': 'McCulloch v. Maryland', 'citation': '17 U.S. 316', 'year': '1819', 'court': 'Supreme Court of the United States'},
    'gibbons v ogden': {'case_name': 'Gibbons v. Ogden', 'citation': '22 U.S. 1', 'year': '1824', 'court': 'Supreme Court of the United States'},
    'dred scott v sandford': {'case_name': 'Dred Scott v. Sandford', 'citation': '60 U.S. 393', 'year': '1857', 'court': 'Supreme Court of the United States'},
    'plessy v ferguson': {'case_name': 'Plessy v. Ferguson', 'citation': '163 U.S. 537', 'year': '1896', 'court': 'Supreme Court of the United States'},
    'miranda v arizona': {'case_name': 'Miranda v. Arizona', 'citation': '384 U.S. 436', 'year': '1966', 'court': 'Supreme Court of the United States'},
    'gideon v wainwright': {'case_name': 'Gideon v. Wainwright', 'citation': '372 U.S. 335', 'year': '1963', 'court': 'Supreme Court of the United States'},
    'mapp v ohio': {'case_name': 'Mapp v. Ohio', 'citation': '367 U.S. 643', 'year': '1961', 'court': 'Supreme Court of the United States'},
    'griswold v connecticut': {'case_name': 'Griswold v. Connecticut', 'citation': '381 U.S. 479', 'year': '1965', 'court': 'Supreme Court of the United States'},
    'obergefell v hodges': {'case_name': 'Obergefell v. Hodges', 'citation': '576 U.S. 644', 'year': '2015', 'court': 'Supreme Court of the United States'},
    'dobbs v jackson': {'case_name': 'Dobbs v. Jackson Women\'s Health Organization', 'citation': '597 U.S. 215', 'year': '2022', 'court': 'Supreme Court of the United States'},
    'citizens united v fec': {'case_name': 'Citizens United v. FEC', 'citation': '558 U.S. 310', 'year': '2010', 'court': 'Supreme Court of the United States'},
    'tinker v des moines': {'case_name': 'Tinker v. Des Moines Indep. Community School Dist.', 'citation': '393 U.S. 503', 'year': '1969', 'court': 'Supreme Court of the United States'},
    'brandenburg v ohio': {'case_name': 'Brandenburg v. Ohio', 'citation': '395 U.S. 444', 'year': '1969', 'court': 'Supreme Court of the United States'},
    'nyt v sullivan': {'case_name': 'New York Times Co. v. Sullivan', 'citation': '376 U.S. 254', 'year': '1964', 'court': 'Supreme Court of the United States'},
    'united states v nixon': {'case_name': 'United States v. Nixon', 'citation': '418 U.S. 683', 'year': '1974', 'court': 'Supreme Court of the United States'},
    'chevron v nrdc': {'case_name': 'Chevron U.S.A. Inc. v. Natural Resources Defense Council, Inc.', 'citation': '467 U.S. 837', 'year': '1984', 'court': 'Supreme Court of the United States'},
    'lochner v new york': {'case_name': 'Lochner v. New York', 'citation': '198 U.S. 45', 'year': '1905', 'court': 'Supreme Court of the United States'},
    'wickard v filburn': {'case_name': 'Wickard v. Filburn', 'citation': '317 U.S. 111', 'year': '1942', 'court': 'Supreme Court of the United States'},
    'bush v gore': {'case_name': 'Bush v. Gore', 'citation': '531 U.S. 98', 'year': '2000', 'court': 'Supreme Court of the United States'},
    'dc v heller': {'case_name': 'District of Columbia v. Heller', 'citation': '554 U.S. 570', 'year': '2008', 'court': 'Supreme Court of the United States'},
}

# ==================== LAYER 2: ZOTERO / JURIS-M BRIDGE ====================
class ZoteroBridge:
    """
    Connects to Zotero/Juris-M API to find personally curated cases.
    Requires ZOTERO_USER_ID and ZOTERO_API_KEY env vars.
    """
    BASE_URL = "https://api.zotero.org"
    
    @staticmethod
    def search(query):
        user_id = os.environ.get('ZOTERO_USER_ID')
        api_key = os.environ.get('ZOTERO_API_KEY')
        
        if not user_id or not api_key: return None
            
        try:
            debug_log(f"Querying Zotero for: {query}")
            url = f"{ZoteroBridge.BASE_URL}/users/{user_id}/items"
            params = {'q': query, 'itemType': 'case', 'limit': 1, 'format': 'json'}
            headers = {'Zotero-API-Key': api_key}
            
            response = requests.get(url, params=params, headers=headers, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    item = data[0].get('data', {})
                    citation = item.get('shortTitle') 
                    if not citation:
                        vol = item.get('volume', '')
                        rep = item.get('reporter', '')
                        page = item.get('firstPage', '')
                        citation = f"{vol} {rep} {page}".strip()
                        
                    return {
                        'caseName': item.get('caseName') or item.get('title'),
                        'citation': citation,
                        'court': item.get('court', ''),
                        'dateFiled': item.get('dateDecided', '')
                    }
        except Exception as e:
            debug_log(f"Zotero Error: {str(e)}")
            pass 
        return None

# ==================== LAYER 3: PUBLIC API ====================
class CourtListenerAPI:
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    HEADERS = {'User-Agent': 'Mozilla/5.0'}
    
    @staticmethod
    def search(query):
        if not query: return None
        try:
            time.sleep(0.1)
            response = requests.get(
                CourtListenerAPI.BASE_URL, 
                params={'q': query, 'type': 'o', 'order_by': 'score desc', 'format': 'json'}, 
                headers=CourtListenerAPI.HEADERS, 
                timeout=5
            )
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results: return results[0]
        except: pass
        return None

# ==================== EXTRACTION LOGIC ====================

KNOWN_LEGAL_DOMAINS = [
    'courtlistener.com', 'oyez.org', 'case.law', 'justia.com', 
    'supremecourt.gov', 'law.cornell.edu', 'nycourts.gov', 
    'scholar.google.com', 'findlaw.com', 'leagle.com', 'casetext.com'
]

def is_legal_citation(text):
    if not text: return False
    clean = text.strip()
    
    # 1. Check Cache
    if find_best_cache_match(clean): return True

    # 2. URL Patterns
    if 'http' in clean:
        if any(d in clean for d in KNOWN_LEGAL_DOMAINS): return True
        lower_url = clean.lower()
        if any(w in lower_url for w in ['/opinion/', '/decision/', '/case/', '.gov/courts/']):
            return True

    # 3. Text Patterns
    if re.search(r'\s(v|vs|versus)\.?\s', clean, re.IGNORECASE): return True
    if re.search(r'\b(in re|ex parte)\b', clean, re.IGNORECASE): return True
    return False

def extract_metadata(text):
    clean = text.strip()
    
    # === PRE-PROCESSING ===
    if 'http' in clean:
        search_query = extract_query_from_url(clean)
        if not search_query: search_query = clean
        raw_for_api = search_query
    else:
        search_query = clean
        raw_for_api = re.sub(r'\b(vs|versus)\.?\b', 'v.', clean, flags=re.IGNORECASE)

    # === LAYER 1: CACHE ===
    cache_key = find_best_cache_match(search_query)
    
    if cache_key:
        debug_log(f"Cache Hit: {cache_key}")
        data = FAMOUS_CASES[cache_key]
        return {
            'type': 'legal',
            'case_name': data['case_name'],
            'citation': data['citation'],
            'court': data['court'],
            'year': data['year'],
            'url': clean if 'http' in clean else '',
            'raw_source': text
        }
    
    # === LAYER 2: ZOTERO (Personal) ===
    zotero_data = ZoteroBridge.search(raw_for_api)
    if zotero_data:
        debug_log(f"Zotero Hit: {zotero_data.get('caseName')}")
        return {
            'type': 'legal',
            'case_name': zotero_data.get('caseName'),
            'citation': zotero_data.get('citation'),
            'court': zotero_data.get('court'),
            'year': str(zotero_data.get('dateFiled', ''))[:4],
            'url': clean if 'http' in clean else '',
            'raw_source': text
        }

    # === LAYER 3: PUBLIC API ===
    metadata = {
        'type': 'legal', 'case_name': raw_for_api, 'citation': '', 
        'court': '', 'year': '', 'url': clean if 'http' in clean else '', 'raw_source': text
    }

    debug_log(f"Searching API for: {raw_for_api}")
    case_data = CourtListenerAPI.search(raw_for_api)
    
    if case_data:
        metadata['case_name'] = case_data.get('caseName') or case_data.get('case_name') or raw_for_api
        metadata['court'] = case_data.get('court') or case_data.get('court_id') or ''
        df = case_data.get('dateFiled') or case_data.get('date_filed')
        if df: metadata['year'] = str(df)[:4]
        citations = case_data.get('citation') or case_data.get('citations')
        if isinstance(citations, list) and citations:
            metadata['citation'] = citations[0]
        elif isinstance(citations, str) and citations:
            metadata['citation'] = citations
            
    return metadata
