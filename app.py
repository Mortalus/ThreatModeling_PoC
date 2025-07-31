#!/usr/bin/env python3
"""
Fixed Flask Backend for Threat Modeling Pipeline
This version properly preserves environment variables when calling scripts
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import logging
import traceback
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# IMPORTANT: Load .env BEFORE anything else
load_dotenv()

# Document processing imports
try:
    import PyPDF2
    from docx import Document
    import chardet
except ImportError as e:
    print(f"Warning: Missing document processing library: {e}")
    print("Install with: pip install PyPDF2 python-docx chardet")

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './output'
INPUT_FOLDER = './input_documents'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

# Ensure directories exist
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, INPUT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Verify environment on startup
print("\n" + "="*60)
print("THREAT MODELING PIPELINE BACKEND")
print("="*60)
api_key = os.getenv('SCW_API_KEY') or os.getenv('SCALEWAY_API_KEY')
if api_key:
    print(f"✓ API Key loaded: ***{api_key[-4:]}")
else:
    print("⚠️  WARNING: No API key found in environment!")
    print("  Please ensure your .env file contains SCW_API_KEY=your_key_here")
print(f"Working directory: {os.getcwd()}")
print(f"Python: {sys.executable}")

# Check for required scripts
scripts = ['info_to_dfds.py', 'dfd_to_threats.py', 'improve_threat_quality.py', 'attack_path_analyzer.py']
for script in scripts:
    if os.path.exists(script):
        print(f"✓ Found: {script}")
    else:
        print(f"✗ Missing: {script}")
print("="*60 + "\n")

# Global state for pipeline
pipeline_state = {
    'current_session': None,
    'logs': []
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path):
    """Extract text content from various file formats."""
    file_ext = file_path.lower().split('.')[-1]
    text_content = ""
    
    try:
        if file_ext == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text_content = f.read()
                
        elif file_ext == 'pdf':
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                        
        elif file_ext == 'docx':
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text_content += cell.text + "\t"
                    text_content += "\n"
                    
        elif file_ext == 'doc':
            return None, "DOC format not supported. Please convert to DOCX."
            
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        return None, str(e)
    
    return text_content, None

def add_log(message, log_type='info'):
    """Add a log entry to the pipeline state."""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': log_type,
        'message': message
    }
    pipeline_state['logs'].append(log_entry)
    logger.info(f"[{log_type}] {message}")

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Handle document upload and text extraction."""
    try:
        if 'document' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['document']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            # Save uploaded file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            add_log(f"File uploaded: {filename}", 'success')
            
            # Extract text content
            text_content, error = extract_text_from_file(file_path)
            
            if error:
                add_log(f"Text extraction failed: {error}", 'error')
                return jsonify({'error': f'Failed to extract text: {error}'}), 500
            
            # Save extracted text for the pipeline
            text_file_path = os.path.join(INPUT_FOLDER, f"{timestamp}_extracted.txt")
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            add_log(f"Text extracted: {len(text_content)} characters", 'success')
            
            # Create session
            session_id = timestamp
            pipeline_state['current_session'] = session_id
            
            return jsonify({
                'status': 'success',
                'session_id': session_id,
                'filename': filename,
                'file_path': file_path,
                'text_file_path': text_file_path,
                'text_preview': text_content[:500] + '...' if len(text_content) > 500 else text_content,
                'text_length': len(text_content),
                'count': 1
            })
        
        return jsonify({'error': 'File type not allowed'}), 400
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        add_log(f"Upload error: {str(e)}", 'error')
        return jsonify({'error': str(e)}), 500

@app.route('/api/run-step', methods=['POST'])
def run_step():
    """Run a specific pipeline step."""
    try:
        data = request.json
        step = data['step']
        input_data = data.get('input', {})
        
        add_log(f"Running step {step}", 'info')
        
        # CRITICAL: Start with a copy of the current environment
        # This preserves API keys and other variables from .env
        env = os.environ.copy()
        
        # Add/override specific variables for the scripts
        env.update({
            'INPUT_DIR': INPUT_FOLDER,
            'OUTPUT_DIR': OUTPUT_FOLDER,
            'LOG_LEVEL': 'INFO'
        })
        
        if step == 1:
            # Document already uploaded and processed
            return jsonify(input_data)
            
        elif step == 2:
            # Run info_to_dfds.py
            add_log("Extracting DFD components...", 'info')
            
            env['DFD_OUTPUT_PATH'] = os.path.join(OUTPUT_FOLDER, 'dfd_components.json')
            
            result = subprocess.run(
                [sys.executable, 'info_to_dfds.py'],
                capture_output=True,
                text=True,
                env=env,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode != 0:
                add_log(f"DFD extraction failed: {result.stderr}", 'error')
                return jsonify({'error': result.stderr or 'Script failed'}), 500
            
            # Load and return the output
            output_file = os.path.join(OUTPUT_FOLDER, 'dfd_components.json')
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    dfd_data = json.load(f)
                
                component_count = (len(dfd_data.get('dfd', {}).get('processes', [])) + 
                                 len(dfd_data.get('dfd', {}).get('assets', [])) +
                                 len(dfd_data.get('dfd', {}).get('external_entities', [])))
                
                add_log(f"DFD extraction completed: {component_count} components found", 'success')
                
                return jsonify({
                    **dfd_data,
                    'count': component_count
                })
            else:
                add_log("DFD output file not created", 'error')
                return jsonify({'error': 'Output file not created'}), 500
            
        elif step == 3:
            # Run dfd_to_threats.py
            add_log("Generating threats using STRIDE...", 'info')
            
            # For scripts that need specific input/output paths
            env['DFD_INPUT_PATH'] = os.path.join(OUTPUT_FOLDER, 'dfd_components.json')
            env['THREATS_OUTPUT_PATH'] = os.path.join(OUTPUT_FOLDER, 'identified_threats.json')
            
            # Check if DFD file exists
            if not os.path.exists(env['DFD_INPUT_PATH']):
                return jsonify({'error': 'DFD file not found. Run step 2 first.'}), 400
            
            result = subprocess.run(
                [sys.executable, 'dfd_to_threats.py'],
                capture_output=True,
                text=True,
                env=env,
                timeout=180  # 3 minute timeout for threat generation
            )
            
            if result.returncode != 0:
                add_log(f"Threat generation failed: {result.stderr}", 'error')
                return jsonify({'error': result.stderr or 'Script failed'}), 500
            
            # Load the output
            threats_file = os.path.join(OUTPUT_FOLDER, 'identified_threats.json')
            if os.path.exists(threats_file):
                with open(threats_file, 'r') as f:
                    threats_data = json.load(f)
                
                threat_count = len(threats_data.get('threats', []))
                add_log(f"Threat generation completed: {threat_count} threats identified", 'success')
                
                return jsonify({
                    **threats_data,
                    'count': threat_count
                })
            else:
                add_log("Threats output file not created", 'error')
                return jsonify({'error': 'Output file not created'}), 500
            
        elif step == 4:
            # Run improve_threat_quality.py
            add_log("Refining and improving threat quality...", 'info')
            
            env.update({
                'DFD_INPUT_PATH': os.path.join(OUTPUT_FOLDER, 'dfd_components.json'),
                'THREATS_INPUT_PATH': os.path.join(OUTPUT_FOLDER, 'identified_threats.json'),
                'REFINED_THREATS_OUTPUT_PATH': os.path.join(OUTPUT_FOLDER, 'refined_threats.json'),
                'SIMILARITY_THRESHOLD': '0.80',
                'CVE_RELEVANCE_YEARS': '5'
            })
            
            result = subprocess.run(
                [sys.executable, 'improve_threat_quality.py'],
                capture_output=True,
                text=True,
                env=env,
                timeout=120
            )
            
            if result.returncode != 0:
                add_log(f"Threat refinement failed: {result.stderr}", 'error')
                return jsonify({'error': result.stderr or 'Script failed'}), 500
            
            # Load refined threats
            refined_file = os.path.join(OUTPUT_FOLDER, 'refined_threats.json')
            if os.path.exists(refined_file):
                with open(refined_file, 'r') as f:
                    refined_data = json.load(f)
                
                threat_count = len(refined_data.get('threats', []))
                add_log(f"Threat refinement completed: {threat_count} refined threats", 'success')
                
                return jsonify({
                    **refined_data,
                    'count': threat_count
                })
            else:
                return jsonify({'error': 'Output file not created'}), 500
            
        elif step == 5:
            # Run attack_path_analyzer.py
            add_log("Analyzing attack paths...", 'info')
            
            env.update({
                'REFINED_THREATS_PATH': os.path.join(OUTPUT_FOLDER, 'refined_threats.json'),
                'DFD_PATH': os.path.join(OUTPUT_FOLDER, 'dfd_components.json'),
                'ATTACK_PATHS_OUTPUT': os.path.join(OUTPUT_FOLDER, 'attack_paths.json'),
                'MAX_PATH_LENGTH': '5',
                'MAX_PATHS_TO_ANALYZE': '20',
                'ENABLE_VECTOR_STORE': 'false'  # Disable by default
            })
            
            result = subprocess.run(
                [sys.executable, 'attack_path_analyzer.py'],
                capture_output=True,
                text=True,
                env=env,
                timeout=180
            )
            
            if result.returncode != 0:
                add_log(f"Attack path analysis failed: {result.stderr}", 'error')
                return jsonify({'error': result.stderr or 'Script failed'}), 500
            
            # Load attack paths
            paths_file = os.path.join(OUTPUT_FOLDER, 'attack_paths.json')
            if os.path.exists(paths_file):
                with open(paths_file, 'r') as f:
                    paths_data = json.load(f)
                
                path_count = len(paths_data.get('attack_paths', []))
                add_log(f"Attack path analysis completed: {path_count} paths identified", 'success')
                
                return jsonify({
                    **paths_data,
                    'count': path_count
                })
            else:
                return jsonify({'error': 'Output file not created'}), 500
            
        else:
            return jsonify({'error': f'Unknown step: {step}'}), 400
            
    except subprocess.TimeoutExpired:
        add_log(f"Step {step} timed out", 'error')
        return jsonify({'error': 'Script execution timed out'}), 500
    except Exception as e:
        logger.error(f"Step execution error: {str(e)}\n{traceback.format_exc()}")
        add_log(f"Step execution error: {str(e)}", 'error')
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-step', methods=['POST'])
def save_step():
    """Save edited data for a specific step."""
    try:
        data = request.json
        step = data['step']
        step_data = data['data']
        
        # Map step to file
        files = {
            2: 'dfd_components.json',
            3: 'identified_threats.json',
            4: 'refined_threats.json',
            5: 'attack_paths.json'
        }
        
        if step in files:
            file_path = os.path.join(OUTPUT_FOLDER, files[step])
            
            # Create backup
            if os.path.exists(file_path):
                backup_path = file_path.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                shutil.copy(file_path, backup_path)
            
            # Save new data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(step_data, f, indent=2, ensure_ascii=False)
            
            add_log(f"Saved changes to {files[step]}", 'success')
            return jsonify({'status': 'saved', 'file': files[step]})
        
        return jsonify({'error': 'Invalid step'}), 400
        
    except Exception as e:
        logger.error(f"Save error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/<step>', methods=['GET'])
def export_data(step):
    """Export data for a specific step."""
    try:
        files = {
            '2': 'dfd_components.json',
            '3': 'identified_threats.json',
            '4': 'refined_threats.json',
            '5': 'attack_paths.json',
            'all': 'complete_analysis.json'
        }
        
        if step == 'all':
            # Combine all data
            complete_data = {
                'export_date': datetime.now().isoformat(),
                'session_id': pipeline_state['current_session']
            }
            
            for step_num, filename in files.items():
                if step_num != 'all':
                    file_path = os.path.join(OUTPUT_FOLDER, filename)
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as f:
                            complete_data[f'step_{step_num}'] = json.load(f)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(complete_data, temp_file, indent=2)
            temp_file.close()
            
            return send_file(temp_file.name, as_attachment=True, download_name='threat_model_complete.json')
        
        elif step in files:
            file_path = os.path.join(OUTPUT_FOLDER, files[step])
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
            else:
                return jsonify({'error': 'File not found'}), 404
        
        return jsonify({'error': 'Invalid step'}), 400
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get pipeline execution logs."""
    return jsonify({'logs': pipeline_state['logs']})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'session': pipeline_state['current_session'],
        'has_api_key': bool(os.getenv('SCW_API_KEY') or os.getenv('SCALEWAY_API_KEY'))
    })

@app.route('/api/reset', methods=['POST'])
def reset_pipeline():
    """Reset the pipeline state."""
    global pipeline_state
    pipeline_state = {
        'current_session': None,
        'logs': []
    }
    
    # Optionally clean output directory
    if request.json and request.json.get('clean_output', False):
        for file in os.listdir(OUTPUT_FOLDER):
            if file.endswith('.json'):
                os.remove(os.path.join(OUTPUT_FOLDER, file))
    
    add_log("Pipeline reset", 'info')
    return jsonify({'status': 'reset'})

if __name__ == '__main__':
    logger.info("Starting Threat Modeling Pipeline Backend...")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Output folder: {OUTPUT_FOLDER}")
    
    # Final check for API key
    if not (os.getenv('SCW_API_KEY') or os.getenv('SCALEWAY_API_KEY')):
        logger.warning("⚠️  No API key found! The LLM calls will fail.")
        logger.warning("Please create a .env file with: SCW_API_KEY=your_key_here")
    
    app.run(debug=True, port=5000, host='0.0.0.0')