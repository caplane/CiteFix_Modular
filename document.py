import os
import zipfile
import shutil
import tempfile
import re
import uuid
import xml.dom.minidom as minidom

class RelationshipManager:
    """Manage Word document relationships with UUIDs"""
    
    def __init__(self, rels_path):
        self.rels_path = rels_path
        self.relationships = {}
        self._load()
    
    def _load(self):
        if not os.path.exists(self.rels_path): return
        try:
            dom = minidom.parse(self.rels_path)
            rels = dom.getElementsByTagName("Relationship")
            for rel in rels:
                rid = rel.getAttribute("Id")
                self.relationships[rid] = {
                    'target': rel.getAttribute("Target"),
                    'type': rel.getAttribute("Type"),
                    'external': (rel.getAttribute("TargetMode") == "External")
                }
        except Exception: self.relationships = {}

    def add_hyperlink(self, url):
        unique_suffix = uuid.uuid4().hex[:8]
        rel_id = f"rId{unique_suffix}"
        self.relationships[rel_id] = {
            'target': url,
            'type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',
            'external': True
        }
        return rel_id
    
    def _save(self):
        impl = minidom.getDOMImplementation()
        doc = impl.createDocument(None, "Relationships", None)
        root = doc.documentElement
        root.setAttribute("xmlns", "http://schemas.openxmlformats.org/package/2006/relationships")
        
        for rel_id, rel_data in self.relationships.items():
            rel_elem = doc.createElement("Relationship")
            rel_elem.setAttribute("Id", rel_id)
            rel_elem.setAttribute("Type", rel_data['type'])
            rel_elem.setAttribute("Target", rel_data['target'])
            if rel_data.get('external'): rel_elem.setAttribute("TargetMode", "External")
            root.appendChild(rel_elem)
        
        with open(self.rels_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n')
            xml_str = root.toxml()
            if xml_str.startswith('<?xml'): xml_str = xml_str.split('?>', 1)[1].strip()
            f.write(xml_str)

class WordDocumentProcessor:
    def __init__(self, docx_path):
        self.docx_path = docx_path
        self.temp_dir = tempfile.mkdtemp()
        self.extract_dir = os.path.join(self.temp_dir, 'extracted')
        self._extract()
    
    def _extract(self):
        with zipfile.ZipFile(self.docx_path, 'r') as z:
            z.extractall(self.extract_dir)
    
    def get_endnotes(self):
        endnotes_path = os.path.join(self.extract_dir, 'word', 'endnotes.xml')
        if not os.path.exists(endnotes_path): return []
        
        with open(endnotes_path, 'r', encoding='utf-8') as f: content = f.read()
        
        endnotes = []
        for match in re.finditer(r'<w:endnote[^>]*w:id="(\d+)"[^>]*>(.*?)</w:endnote>', content, re.DOTALL):
            note_id = match.group(1)
            if note_id in ['0', '-1']: continue
            
            text_parts = []
            for text_match in re.finditer(r'<w:t[^>]*>([^<]+)</w:t>', match.group(2)):
                text_parts.append(text_match.group(1))
            
            text = ''.join(text_parts).strip()
            if text: endnotes.append({'id': note_id, 'text': text, 'original': text})
        return endnotes
    
    def write_endnote(self, note_id, new_html):
        endnotes_path = os.path.join(self.extract_dir, 'word', 'endnotes.xml')
        rels_dir = os.path.join(self.extract_dir, 'word', '_rels')
        os.makedirs(rels_dir, exist_ok=True)
        rel_manager = RelationshipManager(os.path.join(rels_dir, 'endnotes.xml.rels'))
        
        with open(endnotes_path, 'r', encoding='utf-8') as f: content = f.read()
        
        pattern = rf'(<w:endnote[^>]*w:id="{note_id}"[^>]*>)(.*?)(</w:endnote>)'
        match = re.search(pattern, content, re.DOTALL)
        if not match: return False
        
        word_xml = self._html_to_word_xml(new_html, rel_manager)
        new_endnote = match.group(1) + word_xml + match.group(3)
        content = content[:match.start()] + new_endnote + content[match.end():]
        
        with open(endnotes_path, 'w', encoding='utf-8') as f: f.write(content)
        rel_manager._save()
        return True
    
    def _html_to_word_xml(self, html, rel_manager):
        xml_parts = ['<w:p>']
        parts = re.split(r'(https?://[^\s<]+)', html)
        
        for i, part in enumerate(parts):
            if i % 2 == 0:
                if part:
                    in_italic = False
                    for subpart in re.split(r'(</?i>)', part):
                        if subpart == '<i>': in_italic = True
                        elif subpart == '</i>': in_italic = False
                        elif subpart:
                            xml_parts.append('<w:r>')
                            if in_italic: xml_parts.append('<w:rPr><w:i/></w:rPr>')
                            xml_parts.append(f'<w:t xml:space="preserve">{self._escape_xml(subpart)}</w:t>')
                            xml_parts.append('</w:r>')
            else:
                clean_url = part
                trailing = ''
                while clean_url and clean_url[-1] in '.,;:)':
                    trailing = clean_url[-1] + trailing
                    clean_url = clean_url[:-1]
                
                if clean_url:
                    rel_id = rel_manager.add_hyperlink(clean_url)
                    xml_parts.append(f'<w:hyperlink r:id="{rel_id}"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr><w:t>{self._escape_xml(clean_url)}</w:t></w:r></w:hyperlink>')
                if trailing:
                    xml_parts.append(f'<w:r><w:t>{self._escape_xml(trailing)}</w:t></w:r>')
                    
        xml_parts.append('</w:p>')
        return ''.join(xml_parts)
    
    def _escape_xml(self, text):
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
    
    def save_as(self, output_path):
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(self.extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    z.write(file_path, os.path.relpath(file_path, self.extract_dir))
    
    def cleanup(self):
        if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir)
