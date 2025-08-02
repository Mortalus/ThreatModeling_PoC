"""
File handling utilities for the threat modeling pipeline.
"""
import os
import json
import logging
from typing import Tuple, Optional, Any

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract text content from various file formats."""
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    file_ext = file_path.lower().split('.')[-1]
    text_content = ""
    
    try:
        if file_ext == 'txt':
            # Try different encodings for text files
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                        text_content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
                    
        elif file_ext == 'pdf' and PDF_AVAILABLE:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text_content += page.extract_text()
                        
        elif file_ext in ['doc', 'docx'] and DOCX_AVAILABLE:
            doc = DocxDocument(file_path)
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
                
        elif file_ext == 'pdf' and not PDF_AVAILABLE:
            return None, "PDF support not available. Please install PyPDF2."
            
        elif file_ext in ['doc', 'docx'] and not DOCX_AVAILABLE:
            return None, "DOCX support not available. Please install python-docx."
            
        else:
            return None, f"Unsupported file format: {file_ext}"
    
    except Exception as e:
        return None, str(e)
    
    return text_content, None

def save_step_data(step: int, data: Any, output_folder: str):
    """Save step data to file."""
    files = {
        2: 'dfd_components.json',
        3: 'identified_threats.json',
        4: 'refined_threats.json',
        5: 'attack_paths.json'
    }
    
    if step in files:
        file_path = os.path.join(output_folder, files[step])
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)