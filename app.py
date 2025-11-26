import os
import zipfile
import shutil
import tempfile
import re
import json
import requests
import uuid
import xml.dom.minidom as minidom
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, unquote

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
    endnote_pattern = r'<w:endnote[^>]*w:id="(\d+)"[^>]*>(.*?)</w:endnote>'
    matches = re.finditer(endnote_pattern, endnotes_xml, re.DOTALL)
    
    for match in matches:
        note_id = match.group(1)
        note_content = match.group(2)
        if note_id in ['-1', '0']: continue
        
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
    
    # Book pattern
    book_pattern = r'^([^.]+)\.\s+([^.]+)\.\s+([^:]+):\s+([^,]+),\s+(\d{4})'
    if re.match(book_pattern, citation_text):
        match = re.match(book_pattern, citation_text)
        result['type'] = 'book'
        result['components'] = {
            'author': match.group(1), 'title': match.group(2),
            'city': match.group(3), 'publisher': match.group(4),
            'year': match.group(5)
        }
        result['confidence'] = 0.9
        return result
    
    # Journal pattern
    journal_pattern = r'^([^.]+)\.\s+"([^"]+)"\s+([^,]+),?\s+(?:vol\.\s+)?(\d+)'
    if re.search(journal_pattern, citation_text):
        match = re.search(journal_pattern, citation_text)
        result['type'] = 'journal'
        result['components'] = {
            'author': match.group(1), 'title': match.group(2),
            'journal': match.group(3), 'volume': match.group(4)
        }
        result['confidence'] = 0.85
        return result
    
    # Website pattern
    if 'http' in citation_text.lower() or 'www.' in citation_text:
        result['type'] = 'website'
        result['confidence'] = 0.8
        
        # FIX PART 1: Extract and CLEAN the URL
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
        url_match = re.search(url_pattern, citation_text)
        if url_match:
            # Strip trailing punctuation (.,;:) so the component is clean
            raw_url = url_match.group(1)
            result['components']['url'] = raw_url.rstrip('.,;:)')
        
        date_pattern = r'[Aa]ccessed\s+([^.]+)'
        date_match = re.search(date_pattern, citation_text)
        if date_match:
            result['components']['access_date'] = date_match.group(1)
        
        return result
    
    # Legal pattern
    if ' v. ' in citation_text or ' v ' in citation_text:
        result['type'] = 'legal'
        result['confidence'] = 0.75
        return result
    
    # Interview pattern
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
        if citation_type == 'note': return f"{author}, {title} ({city}: {publisher}, {year})"
        else: return f"{author}. {title}. {city}: {publisher}, {year}."
    
    elif cit_type == 'journal':
        author = components.get('author', '')
        title = components.get('title', '')
        journal = components.get('journal', '')
        volume = components.get('volume', '')
        if citation_type == 'note': return f"{author}, \"{title},\" {journal} {volume}"
        else: return f"{author}. \"{title}.\" {journal} {volume}."
    
    elif cit_type == 'website':
        clean_url = components.get('url', '')
        access_date = components.get('access_date', '')
        formatted = citation_data.get('text', '')
        
        # FIX PART 2: VISUAL REPLACEMENT
        # If we extracted a clean URL, use it to overwrite the dirty URL in the text
        if clean_url:
            # Find the URL in the text (including the trailing dot) and replace it with clean_url
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
            formatted_text = format_citation_cms(citation_info, 'note')
        else:
            formatted_text = citation['text']
        
        formatted_citations.append({
            'id': citation['id'],
            'original': citation['text'],
            'formatted': formatted_text,
            'type': citation_info['type'],
            'confidence': citation_info.get('confidence', 0)
        })
    return formatted_citations

def create_formatted_docx(original_path, formatted_citations, output_path, docx_structure):
    temp_output = tempfile.mkdtemp()
    try:
        shutil.copytree(docx_structure['temp_dir'], temp_output, dirs_exist_ok=True)
        endnotes_path = os.path.join(temp_output, 'word', 'endnotes.xml')
        
        if os.path.exists(endnotes_path) and formatted_citations:
            with open(endnotes_path, 'r', encoding='utf-8') as f:
                endnotes_content = f.read()
            
            for citation in formatted_citations:
                pattern = f'<w:endnote[^>]*w:id="{citation["id"]}"[^>]*>(.*?)</w:endnote>'
                match = re.search(pattern, endnotes_content, re.DOTALL)
                if match:
                    note_xml = match.group(1)
                    text_pattern = r'(<w:t[^>]*>)([^<]+)(</w:t>)'
                    text_matches = list(re.finditer(text_pattern, note_xml))
                    if text_matches:
                        formatted_text = citation['formatted']
                        first_match = text_matches[0]
                        new_xml = note_xml[:first_match.start()] + \
                                 first_match.group(1) + formatted_text + first_match.group(3)
                        for match in reversed(text_matches[1:]):
                            new_xml = new_xml[:match.start()] + new_xml[match.end():]
                        full_note = f'<w:endnote w:id="{citation["id"]}">{new_xml}</w:endnote>'
                        endnotes_content = endnotes_content.replace(match.group(0), full_note)
            
            with open(endnotes_path, 'w', encoding='utf-8') as f:
                f.write(endnotes_content)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_output):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_output)
                    zipf.write(file_path, arcname)
        return True
    finally:
        shutil.rmtree(temp_output, ignore_errors=True)
        if docx_structure.get('temp_dir'):
            shutil.rmtree(docx_structure['temp_dir'], ignore_errors=True)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename): return jsonify({'error': 'Invalid file type'}), 400
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    try:
        docx_structure = extract_docx_structure(file_path)
        citations = parse_citations(docx_structure['endnotes'])
        session['current_file'] = file_path
        session['original_filename'] = file.filename
        session['docx_structure'] = {
            'document': docx_structure['document'][:1000],
            'endnotes': docx_structure['endnotes'][:1000],
            'has_endnotes': bool(citations)
        }
        if docx_structure.get('temp_dir'): shutil.rmtree(docx_structure['temp_dir'], ignore_errors=True)
        
        citation_analysis = []
        for citation in citations[:10]:
            analysis = identify_citation_type(citation['text'])
            citation_analysis.append({
                'id': citation['id'],
                'text': citation['text'][:200] + '...' if len(citation['text']) > 200 else citation['text'],
                'type': analysis['type'],
                'confidence': analysis['confidence']
            })
        return jsonify({'success': True, 'filename': file.filename, 'total_citations': len(citations), 'preview': citation_analysis})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/format', methods=['POST'])
def format_citations():
    data = request.json
    style = data.get('style', 'chicago')
    if 'current_file' not in session: return jsonify({'error': 'No file uploaded'}), 400
    file_path = session['current_file']
