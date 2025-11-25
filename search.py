import re
import government
import citation
import formatter
import newspaper
import court  # <--- NEW IMPORT

def search_citation(text, style='chicago'):
    clean_text = text.strip()
    
    # === STRATEGY: MULTI-SOURCE SPLIT ===
    if ';' in clean_text:
        segments = clean_text.split(';')
        resolved_segments = []
        any_match = False
        
        for segment in segments:
            segment = segment.strip()
            if not segment: continue
            
            seg_results = resolve_single_segment(segment, style)
            if seg_results and seg_results[0]['confidence'] != 'low':
                resolved_segments.append(seg_results[0]['formatted'])
                any_match = True
            else:
                resolved_segments.append(segment)
        
        if any_match:
            return [{'formatted': "; ".join(resolved_segments), 'source': 'Composite Result', 'confidence': 'high', 'type': 'composite', 'details': 'Multiple Sources Detected'}]

    return resolve_single_segment(clean_text, style)

def resolve_single_segment(text, style):
    results = []
    
    # 1. LEGAL CHECK (Highest Priority for "v." strings)
    if court.is_legal_citation(text):
        metadata = court.extract_metadata(text)
        formatted = formatter.CitationFormatter.format(metadata, style)
        # Only return if we found a real case match
        if metadata.get('citation'):
             results.append({'formatted': formatted, 'source': 'Court Case', 'confidence': 'high', 'type': 'legal'})
             return results

    # 2. URL CHECK
    urls = re.findall(r'(https?://[^\s]+)', text)
    if urls:
        for raw_url in urls:
            clean_url = raw_url.rstrip('.,;:)')
            
            if government.is_gov_source(clean_url):
                metadata = government.extract_metadata(clean_url)
                formatted = formatter.CitationFormatter.format(metadata, style)
                results.append({'formatted': formatted, 'source': 'U.S. Government', 'confidence': 'high', 'type': 'government'})
                return results
            
            if newspaper.is_newspaper_url(clean_url):
                metadata = newspaper.extract_metadata(clean_url)
                formatted = formatter.CitationFormatter.format(metadata, style)
                results.append({'formatted': formatted, 'source': metadata.get('newspaper', 'Newspaper'), 'confidence': 'high', 'type': 'newspaper'})
                return results
            
            if court.is_legal_citation(clean_url): 
                 metadata = court.extract_metadata(clean_url)
                 formatted = formatter.CitationFormatter.format(metadata, style)
                 results.append({'formatted': formatted, 'source': 'Court Case', 'confidence': 'high', 'type': 'legal'})
                 return results
            
            results.append({'formatted': text, 'source': 'Web URL', 'confidence': 'medium', 'type': 'website'})
            return results

    # 3. BOOK SEARCH
    candidates = citation.extract_metadata(text)
    for cand in candidates:
        formatted = formatter.CitationFormatter.format(cand, style)
        results.append({'formatted': formatted, 'source': 'Google Books', 'confidence': 'medium', 'type': 'book', 'details': f"{cand.get('title')} ({cand.get('year')})"})
        
    if not results:
        results.append({'formatted': text, 'source': 'No Match', 'confidence': 'low', 'type': 'unknown'})
        
    return results
