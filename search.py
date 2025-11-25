"""
The Search Router (search.py)
Acts as the 'Traffic Cop'.
- Analyzes input text.
- Decides which Engine (Government, Book, Newspaper, etc.) should handle it.
- Sends the raw extracted data to the Formatter.
"""

# === ENGINE IMPORTS ===
import government   # Extraction Engine 1
import citation     # Extraction Engine 2 (Books)
import formatter    # The Style Engine

def search_citation(text, style='chicago'):
    """
    Main Pipeline:
    1. Identify Source -> 2. Extract Data -> 3. Format Data
    """
    results = []
    metadata = None
    source_label = 'Unknown'
    confidence = 'low'

    # === STEP 1: ROUTING & EXTRACTION ===
    
    # Priority 1: Check Government Engine
    if government.is_gov_source(text):
        metadata = government.extract_metadata(text)
        confidence = 'high'
        source_label = 'U.S. Government'
        
    # Priority 2: Check Generic URL (if not gov)
    elif text.startswith(('http://', 'https://', 'www.')):
        results.append({
            'formatted': text, 
            'source': 'Web URL', 
            'confidence': 'medium'
        })
        return results

    # Priority 3: Fallback to Book Engine (Google Books)
    else:
        metadata = citation.extract_metadata(text)
        confidence = 'medium' if metadata.get('authors') else 'low'
        source_label = 'Google Books'

    # === STEP 2: FORMATTING ===
    
    if metadata:
        # Pass the raw data to the formatter to apply style rules
        formatted_text = formatter.CitationFormatter.format(metadata, style=style)
        
        results.append({
            'formatted': formatted_text,
            'source': source_label,
            'confidence': confidence,
            'debug_metadata': metadata
        })
    
    return results
Se
