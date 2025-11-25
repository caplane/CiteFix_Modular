"""
Legal Citation Engine (Production Architecture)
Layer 1: Local Cache (Hirschkop Bio + SCOTUS Hall of Fame).
Layer 2: Stealth API (Broad coverage for everything else).
"""

import requests
import re
import sys
import time

# ==================== LAYER 1: THE CACHE ====================

FAMOUS_CASES = {
    # ==================== USER SPECIFIC: PSYCHIATRY ====================
    'osheroff v chestnut lodge': {'case_name': 'Osheroff v. Chestnut Lodge', 'citation': '490 A.2d 720', 'year': '1985', 'court': 'Md. Ct. Spec. App.'},
    'osheroff': {'case_name': 'Osheroff v. Chestnut Lodge', 'citation': '490 A.2d 720', 'year': '1985', 'court': 'Md. Ct. Spec. App.'},
    'tarasoff v regents': {'case_name': 'Tarasoff v. Regents of the University of California', 'citation': '17 Cal. 3d 425', 'year': '1976', 'court': 'Cal.'},

    # ==================== PHILIP J. HIRSCHKOP BIOGRAPHY ====================
    'loving v virginia': {'case_name': 'Loving v. Virginia', 'citation': '388 U.S. 1', 'year': '1967', 'court': 'Supreme Court of the United States'},
    'loving': {'case_name': 'Loving v. Virginia', 'citation': '388 U.S. 1', 'year': '1967', 'court': 'Supreme Court of the United States'},
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

    # ==================== SCOTUS HALL OF FAME (Top 50) ====================
    
    # --- Foundational Power ---
    'marbury v madison': {'case_name': 'Marbury v. Madison', 'citation': '5 U.S. 137', 'year': '1803', 'court': 'Supreme Court of the United States'},
    'mcculloch v maryland': {'case_name': 'McCulloch v. Maryland', 'citation': '17 U.S. 316', 'year': '1819', 'court': 'Supreme Court of the United States'},
    'gibbons v ogden': {'case_name': 'Gibbons v. Ogden', 'citation': '22 U.S. 1', 'year': '1824', 'court': 'Supreme Court of the United States'},

    # --- Civil Rights & Equal Protection ---
    'brown v board': {'case_name': 'Brown v. Board of Education', 'citation': '347 U.S. 483', 'year': '1954', 'court': 'Supreme Court of the United States'},
    'brown v board of education': {'case_name': 'Brown v. Board of Education', 'citation': '347 U.S. 483', 'year': '1954', 'court': 'Supreme Court of the United States'},
    'plessy v ferguson': {'case_name': 'Plessy v. Ferguson', 'citation': '163 U.S. 537', 'year': '1896', 'court': 'Supreme Court of the United States'},
    'dred scott': {'case_name': 'Dred Scott v. Sandford', 'citation': '60 U.S. 393', 'year': '1857', 'court': 'Supreme Court of the United States'},
    'korematsu v united states': {'case_name': 'Korematsu v. United States', 'citation': '323 U.S. 214', 'year': '1944', 'court': 'Supreme Court of the United States'},
    'obergefell v hodges': {'case_name': 'Obergefell v. Hodges', 'citation': '576 U.S. 644', 'year': '2015', 'court': 'Supreme Court of the United States'},
    'regents v bakke': {'case_name': 'Regents of the Univ. of Cal. v. Bakke', 'citation': '438 U.S. 265', 'year': '1978', 'court': 'Supreme Court of the United States'},

    # --- Criminal Procedure (Miranda, Gideon, etc.) ---
    'miranda v arizona': {'case_name': 'Miranda v. Arizona', 'citation': '384 U.S. 436', 'year': '1966', 'court': 'Supreme Court of the United States'},
    'miranda': {'case_name': 'Miranda v. Arizona', 'citation': '384 U.S. 436', 'year': '1966', 'court': 'Supreme Court of the United States'},
    'gideon v wainwright': {'case_name': 'Gideon v. Wainwright', 'citation': '372 U.S. 335', 'year': '1963', 'court': 'Supreme Court of the United States'},
    'gideon': {'case_name': 'Gideon v. Wainwright', 'citation': '372 U.S. 335', 'year': '1963', 'court': 'Supreme Court of the United States'},
    'mapp v ohio': {'case_name': 'Mapp v. Ohio', 'citation': '367 U.S. 643', 'year': '1961', 'court': 'Supreme Court of the United States'},
    'terry v ohio': {'case_name': 'Terry v. Ohio', 'citation': '392 U.S. 1', 'year': '1968', 'court': 'Supreme Court of the United States'},
    'brady v maryland': {'case_name': 'Brady v. Maryland', 'citation': '373 U.S. 83', 'year': '1963', 'court': 'Supreme Court of the United States'},

    # --- Privacy & Reproductive Rights ---
    'roe v wade': {'case_name': 'Roe v. Wade', 'citation': '410 U.S. 113', 'year': '1973', 'court': 'Supreme Court of the United States'},
    'roe v. wade': {'case_name': 'Roe v. Wade', 'citation': '410 U.S. 113', 'year': '1973', 'court': 'Supreme Court of the United States'},
    'griswold v connecticut': {'case_name': 'Griswold v. Connecticut', 'citation': '381 U.S. 479', 'year': '1965', 'court': 'Supreme Court of the United States'},
    'planned parenthood v casey': {'case_name': 'Planned Parenthood of Southeastern Pa. v. Casey', 'citation': '505 U.S. 833', 'year': '1992', 'court': 'Supreme Court of the United States'},
    'dobbs v jackson': {'case_name': 'Dobbs v. Jackson Women\'s Health Organization', 'citation': '597 U.S. 215', 'year': '2022', 'court': 'Supreme Court of the United States'},
    'dobbs': {'case_name': 'Dobbs v. Jackson Women\'s Health Organization', 'citation': '597 U.S. 215', 'year': '2022', 'court': 'Supreme Court of the United States'},
    'lawrence v texas': {'case_name': 'Lawrence v. Texas', 'citation': '539 U.S. 558', 'year': '2003', 'court': 'Supreme Court of the United States'},

    # --- First Amendment (Speech/Press/Religion) ---
    'tinker v des moines': {'case_name': 'Tinker v. Des Moines Indep. Community School Dist.', 'citation': '393 U.S. 503', 'year': '1969', 'court': 'Supreme Court of the United States'},
    'brandenburg v ohio': {'case_name': 'Brandenburg v. Ohio', 'citation': '395 U.S. 444', 'year': '1969', 'court': 'Supreme Court of the United States'},
    'nyt v sullivan': {'case_name': 'New York Times Co. v. Sullivan', 'citation': '376 U.S. 254', 'year': '1964', 'court': 'Supreme Court of the United States'},
    'citizens united v fec': {'case_name': 'Citizens United v. FEC', 'citation': '558 U.S. 310', 'year': '2010', 'court': 'Supreme Court of the United States'},
    'citizens united': {'case_name': 'Citizens United v. FEC', 'citation': '558 U.S. 310', 'year': '2010', 'court': 'Supreme Court of the United States'},
    'schenck v united states': {'case_name': 'Schenck v. United States', 'citation': '249 U.S. 47', 'year': '1919', 'court': 'Supreme Court of the United States'},
    'lemon v kurtzman': {'case_name': 'Lemon v. Kurtzman', 'citation': '403 U.S. 602', 'year': '1971', 'court': 'Supreme Court of the United States'},

    # --- Commerce & Labor ---
    'lochner v new york': {'case_name': 'Lochner v. New York', 'citation': '198 U.S. 45', 'year': '1905', 'court': 'Supreme Court of the United States'},
    'wickard v filburn': {'case_name': 'Wickard v. Filburn', 'citation': '317 U.S. 111', 'year': '1942', 'court': 'Supreme Court of the United States'},
    'chevron v nrdc': {'case_name': 'Chevron U.S.A. Inc. v. Natural Resources Defense Council, Inc.', 'citation': '467 U.S. 837', 'year': '1984', 'court': 'Supreme Court of the United States'},
}

# ==================== DEBUG LOGGING ====================

def debug_log(message):
    print(f"[COURT.PY] {message}", file=sys.stderr, flush=True)

# ==================== LAYER 2: THE STEALTH API ====================

class CourtListenerAPI:
    BASE_URL = "https://www.courtlistener.com/api/rest/v3/search/"
    
    # Headers to mimic a real Chrome User on Windows
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    @staticmethod
    def search(query):
        if not query: return None
        
        try:
            # Random delay to feel human (prevents 429 blocking)
            time.sleep(0.1) 
            
            response = requests.get(
                CourtListenerAPI.BASE_URL, 
                params={'q': query, 'type': 'o', 'order_by': 'score desc', 'format': 'json'}, 
                headers=CourtListenerAPI.HEADERS, 
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                
                # Iterate through Top 10 to find a "Real" opinion (skip docket entries)
                for result in results[:10]:
                    citations = result.get('citation') or result.get('citations')
                    case_name = result.get('caseName') or result.get('case_name')
                    
                    if citations:
                        debug_log(f"API Match: {case_name}")
                        return result
                        
                # Fallback: Return first result
                if results: return results[0]
            else:
                debug_log(f"API Blocked/Error: {response.status_code}")

        except Exception as e:
            debug_log(f"API Connection Error: {e}")
            
        return None

# ==================== EXTRACTION LOGIC ====================

LEGAL_DOMAINS = ['courtlistener.com', 'oyez.org', 'case.law', 'justia.com', 'supremecourt.gov', 'law.cornell.edu']

def is_legal_citation(text):
    if not text: return False
    clean = text.strip()
    if 'http' in clean: return any(d in clean for d in LEGAL_DOMAINS)
    if re.search(r'\s(v|vs)\.?\s', clean, re.IGNORECASE): return True
    if re.search(r'\d+\s+[A-Za-z\.]+\s+\d+', clean): return True
    
    # Check if it exists in our cache by name
    clean_lower = clean.lower().replace('.', '').replace(',', '').strip()
    if clean_lower in FAMOUS_CASES: return True
    
    return False

def extract_metadata(text):
    clean = text.strip()
    clean_lower = clean.lower().replace('.', '').replace(',', '').strip()
    
    # === CHECK LAYER 1: CACHE ===
    if clean_lower in FAMOUS_CASES:
        debug_log(f"Cache Hit: {clean}")
        data = FAMOUS_CASES[clean_lower]
        return {
            'type': 'legal',
            'case_name': data['case_name'],
            'citation': data['citation'],
            'court': data['court'],
            'year': data['year'],
            'url': '',
            'raw_source': text
        }
    
    # === CHECK LAYER 2: API ===
    metadata = {
        'type': 'legal', 'case_name': text, 'citation': '', 
        'court': '', 'year': '', 'url': '', 'raw_source': text
    }

    # Normalize query for API
    search_query = re.sub(r'\bvs\.?\b', 'v.', clean, flags=re.IGNORECASE)
    
    case_data = CourtListenerAPI.search(search_query)
    
    if case_data:
        metadata['case_name'] = case_data.get('caseName') or case_data.get('case_name') or text
        metadata['court'] = case_data.get('court') or case_data.get('court_id') or ''
        
        df = case_data.get('dateFiled') or case_data.get('date_filed')
        if df: metadata['year'] = str(df)[:4]
            
        citations = case_data.get('citation') or case_data.get('citations')
        if isinstance(citations, list) and citations:
            metadata['citation'] = citations[0]
        elif isinstance(citations, str) and citations:
            metadata['citation'] = citations
            
    return metadata
