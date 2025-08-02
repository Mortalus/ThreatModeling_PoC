import os
import sys
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path):
    """Extract text content from various file formats."""
    file_ext = file_path.lower().split('.')[-1]
    text_content = ""
    try:
        if file_ext == 'txt':
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
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
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
        elif file_ext == 'docx' and DOCX_AVAILABLE:
            doc = DocxDocument(file_path)
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text_content += cell.text + "\t"
                    text_content += "\n"
        elif file_ext in ['doc', 'docx'] and not DOCX_AVAILABLE:
            return None, "DOCX format not supported. Please install python-docx or convert to TXT."
        elif file_ext == 'pdf' and not PDF_AVAILABLE:
            return None, "PDF format not supported. Please install PyPDF2 or convert to TXT."
    except Exception as e:
        return None, str(e)
    return text_content, None

def save_step_data(step, data, output_folder):
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