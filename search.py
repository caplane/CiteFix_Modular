import re
import government
import citation
import formatter
import newspaper
import court
import journal 

def search_citation(text, style='chicago'):
    clean_text = text.strip()
    
    # === COMPOSITE CHECK (Handling ";") ===
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
            return [{
                'formatted': "; ".join(resolved_segments), 
                'source': 'Composite Result', 
                'confidence': 'high', 
                'type': 'composite', 
                'details': 'Multiple Sources Detected'
            }]

    return resolve_single_segment(clean_text, style)

def resolve_single_segment(text, style):
    results = []
    
    # 1. LEGAL CHECK (Priority)
    if court.is_legal_citation(text):
        metadata = court.extract_metadata(text)
        formatted = formatter.CitationFormatter.format(metadata, style)
        has_citation = bool(metadata.get('citation'))
        confidence = 'high' if has_citation else 'medium'
        
        results.append({
            'formatted': formatted, 
            'source': 'Court Case', 
            'confidence': confidence, 
            'type': 'legal',
            'details': f"{metadata.get('case_name')} - {metadata.get('citation')}"
        })
        if confidence == 'high': return results

    # 2. JOURNAL CHECK (The Smart Logic)
    journal_data = journal.extract_metadata(text)
    
    if journal_data.get('title') and journal_data.get('title') != 'Unknown Article':
        formatted = formatter.CitationFormatter.format(journal_data, style)
        is_solid = bool(journal_data.get('doi') or journal_data.get('url'))
        
        results.append({
            'formatted': formatted, 
            'source': journal_data.get('source_engine', 'Journal API'), 
            'confidence': 'high' if is_solid else 'medium', 
            'type': 'journal',
            'details': f"{journal_data.get('journal')} ({journal_data.get('year')})"
        })
        if is_solid: return results

    # 3. URL CHECK
    urls = re.findall(r'(https?://[^\s]+)', text)
    if urls:
        for raw_url in urls:
            clean_url = raw_url.rstrip('.,;:)')
            if government.is_gov_source(clean_url):
                metadata = government.extract_metadata(clean_url)
                formatted = formatter.CitationFormatter.format(metadata, style)
                results.insert(0, {'formatted': formatted, 'source': 'U.S. Government', 'confidence': 'high', 'type': 'government'})
                return results
            if newspaper.is_newspaper_url(clean_url):
                metadata = newspaper.extract_metadata(clean_url)
                formatted = formatter.CitationFormatter.format(metadata, style)
                results.insert(0, {'formatted': formatted, 'source': metadata.get('newspaper', 'Newspaper'), 'confidence': 'high', 'type': 'newspaper'})
                return results

    # 4. BOOK SEARCH (Fallback)
    candidates = citation.extract_metadata(text)
    for cand in candidates:
        formatted = formatter.CitationFormatter.format(cand, style)
        results.append({
            'formatted': formatted, 'source': 'Google Books', 'confidence': 'medium', 
            'type': 'book', 'details': f"{cand.get('title')} ({cand.get('year')})"
        })
        
    if not results:
        results.append({'formatted': text, 'source': 'No Match', 'confidence': 'low', 'type': 'unknown'})
        
    return results
