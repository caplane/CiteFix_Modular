import os
import zipfile
import shutil
import tempfile
import re
import json
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'production-key-v19-style-preservation'

# Directory settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'docx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_docx_structure(file_path):
    """Extract content structure from DOCX with preserved paragraph and character styles"""
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Parse document.xml
        doc_path = os.path.join(temp_dir, 'word', 'document.xml')
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse endnotes.xml if exists
        endnotes_path = os.path.join(temp_dir, 'word', 'endnotes.xml')
        endnotes_content = ""
        if os.path.exists(endnotes_path):
            with open(endnotes_path, 'r', encoding='utf-8') as f:
                endnotes_content = f.read()
        
        # Parse styles.xml if exists  
        styles_path = os.path.join(temp_dir, 'word', 'styles.xml')
        styles_content = ""
        if os.path.exists(styles_path):
            with open(styles_path, 'r', encoding='utf-8') as f:
                styles_content = f.read()
        
        return {
            'document': content,
            'endnotes': endnotes_content,
            'styles': styles_content,
            'temp_dir': temp_dir
        }
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e

def parse_citations(endnotes_xml):
    """Parse citations from endnotes.xml"""
    if not endnotes_xml:
        return []
    
    endnotes = []
    # Find all endnote entries
    endnote_pattern = r'<w:endnote[^>]*w:id="(\d+)"[^>]*>(.*?)</w:endnote>'
    matches = re.finditer(endnote_pattern, endnotes_xml, re.DOTALL)
    
    for match in matches:
        note_id = match.group(1)
        note_content = match.group(2)
        
        # Skip separator and continuation notes
        if note_id in ['-1', '0']:
            continue
        
        # Extract text from the note
        text_pattern = r'<w:t[^>]*>([^<]+)</w:t>'
        texts = re.findall(text_pattern, note_content)
        full_text = ''.join(texts)
        
        if full_text.strip():
            endnotes.append({
                'id': note_id,
                'text': full_text.strip(),
                'original_xml': note_content
            })
    
    return endnotes

def identify_citation_type(citation_text):
    """Identify the type and structure of a citation"""
    result = {
        'type': 'unknown',
        'components': {},
        'confidence': 0
    }
    
    # Book pattern (Author. Title. City: Publisher, Year)
    book_pattern = r'^([^.]+)\.\s+([^.]+)\.\s+([^:]+):\s+([^,]+),\s+(\d{4})'
    if re.match(book_pattern, citation_text):
        match = re.match(book_pattern, citation_text)
        result['type'] = 'book'
        result['components'] = {
            'author': match.group(1),
            'title': match.group(2),
            'city': match.group(3),
            'publisher': match.group(4),
            'year': match.group(5)
        }
        result['confidence'] = 0.9
        return result
    
    # Journal article pattern
    journal_pattern = r'^([^.]+)\.\s+"([^"]+)"\s+([^,]+),?\s+(?:vol\.\s+)?(\d+)'
    if re.search(journal_pattern, citation_text):
        match = re.search(journal_pattern, citation_text)
        result['type'] = 'journal'
        result['components'] = {
            'author': match.group(1),
            'title': match.group(2),
            'journal': match.group(3),
            'volume': match.group(4)
        }
        result['confidence'] = 0.85
        return result
    
    # Website pattern
    if 'http' in citation_text.lower() or 'www.' in citation_text:
        result['type'] = 'website'
        result['confidence'] = 0.8
        
        # Try to extract URL
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
        url_match = re.search(url_pattern, citation_text)
        if url_match:
            # FIX 1: Strip trailing punctuation from extraction
            raw_url = url_match.group(1)
            result['components']['url'] = raw_url.rstrip('.,;:)')
        
        # Try to extract access date
        date_pattern = r'[Aa]ccessed\s+([^.]+)'
        date_match = re.search(date_pattern, citation_text)
        if date_match:
            result['components']['access_date'] = date_match.group(1)
        
        return result
    
    # Legal citation pattern
    if ' v. ' in citation_text or ' v ' in citation_text:
        result['type'] = 'legal'
        result['confidence'] = 0.75
        return result
    
    # Interview/personal communication
    if any(word in citation_text.lower() for word in ['interview', 'personal communication', 'email', 'conversation']):
        result['type'] = 'personal'
        result['confidence'] = 0.7
        return result
    
    return result

def format_citation_cms(citation_data, citation_type='note'):
    """Format citation according to Chicago Manual of Style"""
    components = citation_data.get('components', {})
    cit_type = citation_data.get('type', 'unknown')
    
    if cit_type == 'book':
        author = components.get('author', '')
        title = components.get('title', '')
        city = components.get('city', '')
        publisher = components.get('publisher', '')
        year = components.get('year', '')
        
        if citation_type == 'note':
            return f"{author}, {title} ({city}: {publisher}, {year})"
        else:
            return f"{author}. {title}. {city}: {publisher}, {year}."
    
    elif cit_type == 'journal':
        author = components.get('author', '')
        title = components.get('title', '')
        journal = components.get('journal', '')
        volume = components.get('volume', '')
        
        if citation_type == 'note':
            return f"{author}, \"{title},\" {journal} {volume}"
        else:
            return f"{author}. \"{title}.\" {journal} {volume}."
    
    elif cit_type == 'website':
        clean_url = components.get('url', '')
        access_date = components.get('access_date', '')
        formatted = citation_data.get('text', '')
        
        # FIX 2: Replace dirty URL in text with clean URL
        if clean_url:
            formatted = re.sub(r'(https?://[^\s]+|www\.[^\s]+)', clean_url, formatted)
            
        if access_date and 'accessed' not in formatted.lower():
            formatted += f" Accessed {access_date}."
        
        return formatted
    
    return citation_data.get('text', '')

def apply_citation_style(citations, style='chicago'):
    """Apply formatting style to all citations"""
    formatted_citations = []
    
    for citation in citations:
        citation_info = identify_citation_type(citation['text'])
        citation_info['text'] = citation['text']
        citation_info['id'] = citation['id']
        
        if style == 'chicago':
