#!/usr/bin/env python3
"""
The Web Controller (app.py)
Acts as the 'General Contractor'.
- Handles the web server (Flask).
- Manages user sessions.
- Coordinates the file upload and download.
- Uses Thread Locking to prevent file corruption.
"""

import os
import shutil
import tempfile
import uuid
import threading
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename

# === MODULAR ENGINE IMPORTS ===
from document import WordDocumentProcessor
from search import search_citation
# NEW: Import the tool that fixes the links
from formatter import LinkActivator 

# ==================== INITIALIZATION ====================
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'modular-key-v2-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ==================== STORAGE & LOCKING ====================
USER_DATA_STORE = {}
# CRITICAL: Thread lock prevents two users from writing to the same file simultaneously
FILE_LOCK = threading.Lock()

# ==================== HELPERS ====================

def get_user_data():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return USER_DATA_STORE.get(session['user_id'])

def set_user_data(data):
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    USER_DATA_STORE[session['user_id']] = data

def process_uploaded_file(file):
    """
    Saves the file and runs the Document Engine to extract endnotes.
    """
    temp_dir = tempfile.mkdtemp()
    filename = secure_filename(file.filename)
    filepath = os.path.join(temp_dir, filename)
    file.save(filepath)
    
    # Delegate to Document Engine
    processor = WordDocumentProcessor(filepath)
    endnotes = processor.get_endnotes()
    
    user_data = {
        'temp_dir': temp_dir,
        'original_filename': filename,
        'original_filepath': filepath,
        'extract_dir': processor.extract_dir,
        'endnotes': endnotes
    }
    set_user_data(user_data)
    return endnotes

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        endnotes = process_uploaded_file(file)
        return jsonify({'success': True, 'endnotes': endnotes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['POST'])
def search():
    """
    Search Endpoint
    Delegates strictly to the Search Router (search.py).
    """
    data = request.json
    text = data.get('text', '')
    # Future: We can accept a 'style' parameter here (e.g., 'apa')
    
    try:
        results = search_citation(text)
        return jsonify({'results': results})
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'results': []})

@app.route('/update', methods=['POST'])
def update():
    """
    Update Endpoint
    Uses File Locking to safely write changes to the Word XML.
    """
    user_data = get_user_data()
    if not user_data:
        return jsonify({'error': 'Session expired'}), 400
    
    data = request.json
    note_id = data.get('id')
    html_content = data.get('html')
    
    if not note_id or not html_content:
        return jsonify({'error': 'Missing data'}), 400
    
    try:
        # THREAD SAFETY: Lock the file before writing
        with FILE_LOCK:
            processor = WordDocumentProcessor(user_data['original_filepath'])
            # Point processor to the existing extracted folder
            processor.extract_dir = user_data['extract_dir']
            success = processor.write_endnote(note_id, html_content)
            return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download():
    user_data = get_user_data()
    if not user_data:
        return "Session expired", 400
    
    try:
        output_filename = f"Resolved_{user_data['original_filename']}"
        output_path = os.path.join(user_data['temp_dir'], output_filename)
        
        # 1. Delegate to Document Engine to zip files back up
        processor = WordDocumentProcessor(user_data['original_filepath'])
        processor.extract_dir = user_data['extract_dir']
        processor.save_as(output_path)
        
        # 2. CRITICAL FIX: Run the LinkActivator on the final file
        # This converts plain text URLs into clickable MS Word Field Codes
        try:
            LinkActivator.process(output_path)
            print(f"  ✓ Links Activated for {output_filename}")
        except Exception as e:
            print(f"  ! Link Activation failed: {e}")
        
        return send_file(output_path, as_attachment=True, download_name=output_filename)
    except Exception as e:
        return f"Error creating download: {str(e)}", 500

@app.route('/reset', methods=['POST'])
def reset():
    user_data = get_user_data()
    if user_data and os.path.exists(user_data['temp_dir']):
        shutil.rmtree(user_data['temp_dir'])
    session.clear()
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("=" * 60)
    print("CITEFIX PRO - MODULAR ARCHITECTURE")
    print("=" * 60)
    print("  ✓ Search Router Active")
    print("  ✓ Engines: Government, Books/Citation, Document")
    print(f"  ✓ Listening on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
