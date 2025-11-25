"""
The Search Router (search.py)
- Acts as the 'Traffic Cop' for the CiteFix application.
- Routes queries to Government, Newspaper, Legal, or Book engines.
- Handles Multi-Source Splitting via Semicolons (;).
"""

import re
import government
import citation
import formatter
import newspaper
import court

def search_citation(text, style='chicago'):
    """
    Returns a list of candidate results.
    Handles Multi-Source Splitting via Semicolons (;).
    """
    clean_text = text.strip()
    
    # === STRATEGY: MULTI-SOURCE SPLIT ===
    if ';' in clean_text:
        segments = clean_text.split(';')
        resolved_segments = []
        any_match = False
        
        for segment in segments:
            segment = segment.strip()
            if not segment: continue
            
            # Resolve each segment individually
            seg_results = resolve_single_segment(segment, style)
            
            if seg_results and seg_results[0]['confidence'] != 'low':
                resolved_segments.append(seg_results[0]['formatted'])
                any_match = True
            else:
                resolved_segments.append(segment)
        
        if any_match:
            composite_string = "; ".join(resolved_segments)
            return [{
                'formatted': composite_string,
                'source': 'Composite Result',
                'confidence': 'high',
                'type': 'composite',
                'details': 'Multiple Sources Detected'
            }]

    # === STRATEGY: SINGLE SEGMENT ===
    return resolve_single_segment(clean_text, style)

def resolve_single_segment(text, style):
    results = []
    
    # 1. LEGAL CHECK (Highest Priority for "v." strings)
    # Checks for "Brown v. Board" pattern
    if court.is_legal_citation(text):
        metadata = court.extract_metadata(text)
        formatted = formatter.CitationFormatter.format(metadata, style)
        
        # Only return if we found a real case match
        if metadata.get('citation') or metadata.get('case_name') != text:
             results.append({
                 'formatted': formatted,
                 'source': 'Court Case',
                 'confidence': 'high',
                 'type': 'legal'
             })
             return results

    # 2. URL CHECK
    urls = re.findall(r'(https?://[^\s]+)', text)
    if urls:
        for raw_url in urls:
            clean_url = raw_url.rstrip('.,;:)')
            
            # A. Check Government Engine
            if government.is_gov_source(clean_url):
                metadata = government.extract_metadata(clean_url)
                formatted = formatter.CitationFormatter.format(metadata, style)
                results.append({
                    'formatted': formatted,
                    'source': 'U.S. Government',
                    'confidence': 'high',
                    'type': 'government'
                })
                return results
            
            # B. Check Newspaper Engine
            if newspaper.is_newspaper_url(clean_url):
                metadata = newspaper.extract_metadata(clean_url)
                formatted = formatter.CitationFormatter.format(metadata, style)
                results.append({
                    'formatted': formatted,
                    'source': metadata.get('newspaper', 'Newspaper'),
                    'confidence': 'high',
                    'type': 'newspaper'
                })
                return results
            
            # C. Check Legal URLs (Justia, Oyez)
            if court.is_legal_citation(clean_url):
                 metadata = court.extract_metadata(clean_url)
                 formatted = formatter.CitationFormatter.format(metadata, style)
                 results.append({
                     'formatted': formatted,
                     'source': 'Court Case',
                     'confidence': 'high',
                     'type': 'legal'
                 })
                 return results
            
            # D. Generic URL fallback
            results.append({
                'formatted': text,
                'source': 'Web URL',
                'confidence': 'medium',
                'type': 'website'
            })
            return results

    # 3. BOOK SEARCH (Default Fallback)
    candidates = citation.extract_metadata(text)
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
