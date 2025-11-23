"""
The Search Router (search.py)
Acts as the 'Traffic Cop'.
- UPGRADE: Multi-Source Resolution using Semicolons (;).
- Splits text into segments and routes each one individually.
"""

import re
# === ENGINE IMPORTS ===
import government   # Extraction Engine 1
import citation     # Extraction Engine 2 (Books)
import formatter    # The Style Engine

def search_citation(text, style='chicago'):
    """
    Main Pipeline:
    1. Split text by semicolons (;).
    2. For each segment:
       a. Check if it has a URL -> Government Engine.
       b. If no URL -> Book Engine.
    3. Reassemble the segments into one formatted string.
    """
    
    # Step 1: Split by semicolon (Standard Chicago separator)
    # We assume distinct sources are separated by ";"
    # Example input: "Great Gatsby; http://epa.gov"
    segments = text.split(';')
    resolved_segments = []
    
    any_match_found = False
    
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
            
        # === ROUTE A: URL DETECTED ===
        # Check for URL in this specific segment
        urls = re.findall(r'(https?://[^\s]+)', segment)
        
        if urls:
            # We have a URL. Process it.
            processed_segment = segment
            
            for raw_url in urls:
                clean_url = raw_url.rstrip('.,;:)')
                
                # Check Government Engine
                if government.is_gov_source(clean_url):
                    metadata = government.extract_metadata(clean_url)
                    formatted = formatter.CitationFormatter.format(metadata, style)
                    # Replace the URL with the citation
                    processed_segment = processed_segment.replace(raw_url, formatted)
                    any_match_found = True
                
                # Future: Add Newspaper/Court checks here
                # elif newspaper.is_news(clean_url): ...
            
            resolved_segments.append(processed_segment)
            
        # === ROUTE B: NO URL (ASSUME BOOK) ===
        else:
            # If it's not a URL, we treat it as a potential Book title
            # But we don't want to process short common words (e.g. "See", "Ibid")
            if len(segment) > 3 and not segment.lower().startswith('see '):
                metadata = citation.extract_metadata(segment)
                
                # Only format if we actually found an author (Medium confidence)
                if metadata.get('authors'):
                    formatted = formatter.CitationFormatter.format(metadata, style)
                    resolved_segments.append(formatted)
                    any_match_found = True
                else:
                    # No book found, keep original text
                    resolved_segments.append(segment)
            else:
                # Too short or filler words, keep original
                resolved_segments.append(segment)

    # Step 3: Reassemble
    if any_match_found:
        # Stitch them back together with semicolons
        final_text = "; ".join(resolved_segments)
        
        # Return as a single high-confidence result
        return [{
            'formatted': final_text,
            'source': 'Multi-Source Resolver',
            'confidence': 'high'
        }]
    
    # Fallback: If absolutely nothing worked, return original text
    return [{
        'formatted': text,
        'source': 'No Match',
        'confidence': 'low'
    }]
