"""
The Search Router (search.py)
- Supports returning MULTIPLE candidates.
- Handles Semicolon splitting for the UI.
"""

import re
import government
import citation
import formatter

def search_citation(text, style='chicago'):
    """
    Returns a list of candidate results.
    Each result has: { formatted, source, confidence, type }
    """
    results = []
    clean_text = text.strip()
    
    # 1. Government / URL Check (Deterministic = 1 Result)
    urls = re.findall(r'(https?://[^\s]+)', clean_text)
    if urls:
        for raw_url in urls:
            clean_url = raw_url.rstrip('.,;:)')
            if government.is_gov_source(clean_url):
                metadata = government.extract_metadata(clean_url)
                formatted = formatter.CitationFormatter.format(metadata, style)
                results.append({
                    'formatted': formatted,
                    'source': 'U.S. Government',
                    'confidence': 'high',
                    'type': 'government'
                })
                return results # Return immediately for Gov docs
            
            # Generic URL fallback
            results.append({
                'formatted': clean_text,
                'source': 'Web URL',
                'confidence': 'medium',
                'type': 'website'
            })
            return results

    # 2. Book Search (Returns 3 Candidates)
    candidates = citation.extract_metadata(clean_text)
    
    for cand in candidates:
        formatted = formatter.CitationFormatter.format(cand, style)
        results.append({
            'formatted': formatted,
            'source': 'Google Books',
            'confidence': 'medium' if cand.get('authors') else 'low',
            'type': 'book',
            'details': f"{cand.get('title')} ({cand.get('year')})"
        })
        
    if not results:
        results.append({'formatted': text, 'source': 'No Match', 'confidence': 'low', 'type': 'unknown'})
        
    return results
