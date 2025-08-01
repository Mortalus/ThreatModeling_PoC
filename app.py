#!/usr/bin/env python3
"""
Enhanced Flask Backend for Threat Modeling Pipeline
Fixed version with proper error handling and integration
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
import threading
import time

# IMPORTANT: Load .env BEFORE anything else
load_dotenv()

# Import config function
def get_config():
    """Get configuration from environment with defaults."""
    return {
        'llm_provider': os.getenv('LLM_PROVIDER', 'scaleway'),
        'llm_model': os.getenv('LLM_MODEL', 'llama-3.3-70b-instruct'),
        'local_llm_endpoint': os.getenv('LOCAL_LLM_ENDPOINT', 'http://localhost:11434/api/generate'),
        'custom_system_prompt': os.getenv('CUSTOM_SYSTEM_PROMPT', ''),
        'timeout': int(os.getenv('PIPELINE_TIMEOUT', '5000')),
        'input_dir': os.getenv('INPUT_DIR', './input_documents'),
        'output_dir': os.getenv('OUTPUT_DIR', './output'),
        'dfd_output_path': os.getenv('DFD_OUTPUT_PATH', './output/dfd_components.json'),
        'mitre_enabled': os.getenv('MITRE_ENABLED', 'true').lower() == 'true',
        'mitre_version': os.getenv('MITRE_VERSION', 'v13.1'),
        'scw_api_url': os.getenv('SCW_API_URL', 'https://api.scaleway.ai/v1'),
        'scw_secret_key': os.getenv('SCW_SECRET_KEY') or os.getenv('SCW_API_KEY')
    }

# Document processing imports with error handling
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: PyPDF2 not available. PDF processing disabled.")

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("Warning: python-docx not available. DOCX processing disabled.")

# Global configuration (runtime overrides)
runtime_config = get_config()

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
OUTPUT_FOLDER = runtime_config['output_dir']
INPUT_FOLDER = runtime_config['input_dir']
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

# Ensure directories exist
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, INPUT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Verify environment on startup
print("\n" + "="*60)
print("THREAT MODELING PIPELINE BACKEND")
print("="*60)
api_key = runtime_config['scw_secret_key']
if api_key:
    print(f"✓ API Key loaded: ***{api_key[-4:]}")
else:
    print("⚠️  WARNING: No API key found in environment!")
    print("  Please ensure your .env file contains SCW_SECRET_KEY=your_key_here")
print(f"Working directory: {os.getcwd()}")
print(f"Python: {sys.executable}")

# Check for required scripts
scripts = ['info_to_dfds.py', 'dfd_to_threats.py', 'improve_threat_quality.py', 'attack_path_analyzer.py']
for script in scripts:
    if os.path.exists(script):
        print(f"✓ Found: {script}")
    else:
        print(f"✗ Missing: {script}")

print("="*60)

# Global state for pipeline - Initialize with proper structure
pipeline_state = {
    'current_session': None,
    'logs': [],
    'step_outputs': {},  # Store outputs for each step
    'validations': {}    # Store validation results
}

# Lock for thread-safe operations
state_lock = threading.Lock()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path):
    """Extract text content from various file formats."""
    file_ext = file_path.lower().split('.')[-1]
    text_content = ""
    
    try:
        if file_ext == 'txt':
            # Try different encodings
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
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        return None, str(e)
    
    return text_content, None

def add_log(message, log_type='info'):
    """Add a log entry to the pipeline state."""
    with state_lock:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': log_type,
            'message': message
        }
        pipeline_state['logs'].append(log_entry)
        
        # Keep only last 1000 logs
        if len(pipeline_state['logs']) > 1000:
            pipeline_state['logs'] = pipeline_state['logs'][-1000:]
    
    logger.info(f"[{log_type}] {message}")

def validate_json_structure(data, step):
    """Validate JSON structure for each step."""
    errors = []
    warnings = []
    
    try:
        if step == 2:  # DFD
            if 'dfd' not in data:
                errors.append("Missing 'dfd' key in output")
            else:
                dfd = data['dfd']
                required_fields = ['project_name', 'external_entities', 'processes', 'assets', 'data_flows']
                for field in required_fields:
                    if field not in dfd:
                        errors.append(f"Missing required field: {field}")
                    elif not dfd[field]:
                        warnings.append(f"Empty field: {field}")
                
                # Validate data flows
                if 'data_flows' in dfd and isinstance(dfd['data_flows'], list):
                    for i, flow in enumerate(dfd['data_flows']):
                        if not isinstance(flow, dict):
                            errors.append(f"Data flow {i} is not a dictionary")
                        else:
                            for req in ['source', 'destination']:
                                if req not in flow:
                                    errors.append(f"Data flow {i} missing '{req}'")
        
        elif step == 3 or step == 4:  # Threats
            if 'threats' not in data:
                errors.append("Missing 'threats' key in output")
            else:
                threats = data['threats']
                if not isinstance(threats, list):
                    errors.append("'threats' must be a list")
                else:
                    for i, threat in enumerate(threats):
                        if not isinstance(threat, dict):
                            errors.append(f"Threat {i} is not a dictionary")
                        else:
                            required = ['component_name', 'stride_category', 'threat_description', 
                                      'mitigation_suggestion', 'impact', 'likelihood']
                            for field in required:
                                if field not in threat:
                                    errors.append(f"Threat {i} missing '{field}'")
        
        elif step == 5:  # Attack Paths
            if 'attack_paths' not in data:
                errors.append("Missing 'attack_paths' key in output")
            else:
                paths = data['attack_paths']
                if not isinstance(paths, list):
                    errors.append("'attack_paths' must be a list")
    
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }

# Add request logging and error handling
@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.url}")
    if request.method == 'POST':
        logger.info(f"Content-Type: {request.content_type}")
        if request.is_json:
            logger.info(f"JSON body: {request.get_json()}")
        else:
            logger.info(f"Form data keys: {list(request.form.keys())}")
            logger.info(f"Files: {list(request.files.keys())}")

@app.errorhandler(400)
def handle_bad_request(e):
    logger.error(f"400 Bad Request: {e}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request Method: {request.method}")
    logger.error(f"Request Headers: {dict(request.headers)}")
    logger.error(f"Request Body: {request.get_data()}")
    return jsonify({'error': 'Bad Request', 'message': str(e)}), 400

@app.errorhandler(500)
def handle_internal_error(e):
    logger.error(f"500 Internal Server Error: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@app.route('/api/test', methods=['GET', 'POST'])
def test_endpoint():
    """Simple test endpoint for debugging."""
    return jsonify({
        'status': 'success',
        'method': request.method,
        'timestamp': datetime.now().isoformat(),
        'message': 'API is working',
        'config': {
            'llm_provider': runtime_config['llm_provider'],
            'has_api_key': bool(runtime_config['scw_secret_key']),
            'output_dir': OUTPUT_FOLDER,
            'input_dir': INPUT_FOLDER
        }
    })

@app.route('/api/configuration', methods=['GET', 'POST'])
def handle_configuration():
    """Get or update runtime configuration."""
    global runtime_config
    
    if request.method == 'GET':
        return jsonify(runtime_config)
    
    elif request.method == 'POST':
        try:
            updates = request.get_json()
            if not updates:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            # Update runtime configuration
            for key, value in updates.items():
                if key in runtime_config:
                    runtime_config[key] = value
                    add_log(f"Configuration updated: {key} = {value}", 'info')
            
            return jsonify({
                'status': 'updated',
                'configuration': runtime_config
            })
        except Exception as e:
            logger.error(f"Configuration update error: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Handle document upload and text extraction."""
    try:
        # Debug logging
        logger.info(f"Upload request received - Method: {request.method}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Files in request: {list(request.files.keys())}")
        logger.info(f"Form data: {list(request.form.keys())}")
        
        if 'document' not in request.files:
            logger.error("No 'document' field in request files")
            return jsonify({'error': 'No file part in request'}), 400
        
        file = request.files['document']
        logger.info(f"File received: {file.filename}")
        
        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
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
            
            if not text_content or len(text_content.strip()) < 10:
                add_log("Extracted text is too short or empty", 'error')
                return jsonify({'error': 'Extracted text is empty or too short'}), 400
            
            # Save extracted text for the pipeline
            text_file_path = os.path.join(INPUT_FOLDER, f"{timestamp}_extracted.txt")
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            add_log(f"Text extracted: {len(text_content)} characters", 'success')
            
            # Create session and save to pipeline state
            session_id = timestamp
            upload_data = {
                'status': 'success',
                'session_id': session_id,
                'filename': filename,
                'file_path': file_path,
                'text_file_path': text_file_path,
                'text_preview': text_content[:500] + '...' if len(text_content) > 500 else text_content,
                'text_length': len(text_content),
                'count': 1
            }
            
            with state_lock:
                pipeline_state['current_session'] = session_id
                pipeline_state['step_outputs'][1] = upload_data
                # Also ensure logs list exists
                if 'logs' not in pipeline_state:
                    pipeline_state['logs'] = []
                # Ensure validations dict exists
                if 'validations' not in pipeline_state:
                    pipeline_state['validations'] = {}
            
            add_log(f"Step 1 completed successfully: {filename}", 'success')
            logger.info(f"💾 Step 1 data saved to pipeline state. Session: {session_id}")
            logger.info(f"📊 Pipeline state after upload: {list(pipeline_state.keys())}")
            logger.info(f"📋 Completed steps after upload: {list(pipeline_state.get('step_outputs', {}).keys())}")
            
            return jsonify(upload_data)
        
        logger.error(f"File type not allowed: {file.filename}")
        return jsonify({'error': 'File type not allowed. Please use TXT, PDF, or DOCX files.'}), 400
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        add_log(f"Upload error: {str(e)}", 'error')
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/run-step', methods=['POST'])
def run_step():
    """Run a specific pipeline step."""
    try:
        logger.info("="*60)
        logger.info("RUN-STEP REQUEST RECEIVED")
        logger.info("="*60)
        
        # Validate request
        if not request.is_json:
            logger.error("❌ Request is not JSON")
            logger.error(f"Content-Type: {request.content_type}")
            logger.error(f"Raw data: {request.get_data()}")
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        logger.info(f"✅ Request JSON data: {data}")
        
        if not data:
            logger.error("❌ No JSON data in request")
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if 'step' not in data:
            logger.error("❌ No 'step' field in request data")
            logger.error(f"Available keys: {list(data.keys())}")
            return jsonify({'error': 'Missing step parameter'}), 400
        
        step = data['step']
        input_data = data.get('input', {})
        
        logger.info(f"🎯 RUNNING STEP {step}")
        logger.info(f"📥 Input data: {input_data}")
        
        # Debug current pipeline state
        with state_lock:
            current_state = {
                'session': pipeline_state.get('current_session'),
                'completed_steps': list(pipeline_state.get('step_outputs', {}).keys()),
                'logs_count': len(pipeline_state.get('logs', [])),
                'validations': list(pipeline_state.get('validations', {}).keys()),
                'pipeline_keys': list(pipeline_state.keys())
            }
        logger.info(f"📊 Current pipeline state: {current_state}")
        
        # If step_outputs is empty but we're running step 2, try to recover
        if step == 2 and not pipeline_state.get('step_outputs'):
            logger.warning("⚠️ Pipeline state appears to be lost, attempting recovery...")
            
            # Check if there are recent uploaded files we can recover
            if os.path.exists(INPUT_FOLDER):
                txt_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('_extracted.txt')]
                txt_files.sort(reverse=True)  # Most recent first
                
                if txt_files:
                    most_recent = txt_files[0]
                    logger.info(f"🔄 Found recent extracted file: {most_recent}")
                    
                    # Extract session ID from filename
                    session_id = most_recent.replace('_extracted.txt', '')
                    
                    # Try to find corresponding uploaded file
                    upload_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(session_id)]
                    
                    if upload_files:
                        upload_file = upload_files[0]
                        text_file_path = os.path.join(INPUT_FOLDER, most_recent)
                        
                        try:
                            with open(text_file_path, 'r', encoding='utf-8') as f:
                                text_content = f.read()
                            
                            # Reconstruct step 1 data
                            recovered_data = {
                                'status': 'success',
                                'session_id': session_id,
                                'filename': upload_file,
                                'file_path': os.path.join(UPLOAD_FOLDER, upload_file),
                                'text_file_path': text_file_path,
                                'text_preview': text_content[:500] + '...' if len(text_content) > 500 else text_content,
                                'text_length': len(text_content),
                                'count': 1
                            }
                            
                            with state_lock:
                                pipeline_state['current_session'] = session_id
                                pipeline_state['step_outputs'][1] = recovered_data
                                if 'logs' not in pipeline_state:
                                    pipeline_state['logs'] = []
                                if 'validations' not in pipeline_state:
                                    pipeline_state['validations'] = {}
                            
                            logger.info(f"✅ Successfully recovered step 1 data for session: {session_id}")
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to recover step 1 data: {e}")
        
        add_log(f"Starting step {step}", 'info')
        
        # Validate step number
        if not isinstance(step, int) or step < 1 or step > 5:
            logger.error(f"❌ Invalid step number: {step} (type: {type(step)})")
            return jsonify({'error': 'Invalid step number. Must be 1-5.'}), 400
        
        logger.info(f"✅ Step number validated: {step}")
        
        # Check prerequisites
        if step > 1:
            logger.info(f"🔍 Checking prerequisites for step {step}")
            
            with state_lock:
                step_outputs = pipeline_state.get('step_outputs', {})
                logger.info(f"📋 Available step outputs: {list(step_outputs.keys())}")
                
                prev_step_output = step_outputs.get(step - 1)
                logger.info(f"🔎 Previous step ({step-1}) output exists: {bool(prev_step_output)}")
                
                if prev_step_output:
                    logger.info(f"📄 Previous step output type: {type(prev_step_output)}")
                    if isinstance(prev_step_output, dict):
                        logger.info(f"📄 Previous step output keys: {list(prev_step_output.keys())}")
                        logger.info(f"📄 Previous step output status: {prev_step_output.get('status', 'unknown')}")
                
                if not prev_step_output:
                    # More detailed error message
                    completed_steps = list(step_outputs.keys())
                    logger.error(f"❌ Step {step} validation failed. Completed steps: {completed_steps}")
                    logger.error(f"❌ Required step {step-1} not found in outputs")
                    
                    # Check if files exist on disk even if not in memory
                    file_checks = {}
                    if step == 3:  # Need DFD from step 2
                        dfd_file = os.path.join(OUTPUT_FOLDER, 'dfd_components.json')
                        file_checks['dfd_file_exists'] = os.path.exists(dfd_file)
                        if file_checks['dfd_file_exists']:
                            try:
                                with open(dfd_file, 'r') as f:
                                    dfd_data = json.load(f)
                                file_checks['dfd_file_valid'] = True
                                file_checks['dfd_keys'] = list(dfd_data.keys())
                                logger.info(f"📁 DFD file exists on disk with keys: {file_checks['dfd_keys']}")
                                
                                # Try to recover by loading file into memory
                                logger.info("🔄 Attempting to recover step 2 from disk...")
                                pipeline_state['step_outputs'][2] = dfd_data
                                logger.info("✅ Step 2 data recovered from disk")
                                
                            except Exception as e:
                                file_checks['dfd_file_valid'] = False
                                file_checks['dfd_error'] = str(e)
                                logger.error(f"❌ DFD file exists but is invalid: {e}")
                    
                    logger.info(f"📁 File system checks: {file_checks}")
                    
                    # If we couldn't recover, return error
                    if step - 1 not in pipeline_state.get('step_outputs', {}):
                        return jsonify({
                            'error': f'Step {step - 1} must be completed first',
                            'completed_steps': completed_steps,
                            'required_step': step - 1,
                            'file_checks': file_checks
                        }), 400
        
        logger.info("✅ Prerequisites check passed")
        
        # CRITICAL: Start with a copy of the current environment
        logger.info("🌍 Setting up environment variables...")
        env = os.environ.copy()
        
        # Add/override specific variables for the scripts
        env_updates = {
            'INPUT_DIR': INPUT_FOLDER,
            'OUTPUT_DIR': OUTPUT_FOLDER,
            'LOG_LEVEL': 'INFO',
            'PIPELINE_TIMEOUT': str(runtime_config['timeout']),
            'LLM_PROVIDER': runtime_config['llm_provider'],
            'LLM_MODEL': runtime_config['llm_model'],
            'LOCAL_LLM_ENDPOINT': runtime_config['local_llm_endpoint'],
            'CUSTOM_SYSTEM_PROMPT': runtime_config['custom_system_prompt'],
            'MITRE_ENABLED': str(runtime_config['mitre_enabled']).lower(),
            'MITRE_VERSION': runtime_config['mitre_version'],
            'SCW_API_URL': runtime_config['scw_api_url']
        }
        
        env.update(env_updates)
        logger.info(f"📝 Environment variables updated: {list(env_updates.keys())}")
        
        # Fix: Ensure API keys are passed to subprocess
        if runtime_config['scw_secret_key']:
            env['SCW_SECRET_KEY'] = runtime_config['scw_secret_key']
            env['SCW_API_KEY'] = runtime_config['scw_secret_key']  # Some scripts might use this
            logger.info("🔑 API keys added to environment")
        else:
            logger.warning("⚠️ No API key available")
        
        result = None
        output_file = None
        script_name = None
        
        logger.info(f"🚀 Executing step {step}...")
        
        if step == 1:
            # Document already uploaded and processed
            logger.info("📄 Step 1: Document upload (already processed)")
            if 1 not in pipeline_state.get('step_outputs', {}):
                logger.error("❌ No document uploaded")
                return jsonify({'error': 'Please upload a document first'}), 400
            
            step_output = pipeline_state['step_outputs'][1]
            logger.info(f"✅ Returning step 1 data: {list(step_output.keys()) if isinstance(step_output, dict) else type(step_output)}")
            return jsonify(step_output)
            
        elif step == 2:
            # Run info_to_dfds.py
            script_name = 'info_to_dfds.py'
            logger.info(f"📜 Step 2: Running {script_name}")
            add_log("Extracting DFD components...", 'info')
            
            env['DFD_OUTPUT_PATH'] = os.path.join(OUTPUT_FOLDER, 'dfd_components.json')
            output_file = env['DFD_OUTPUT_PATH']
            logger.info(f"📁 Output file will be: {output_file}")
            
            # Check if script exists
            if not os.path.exists(script_name):
                logger.error(f"❌ Script not found: {script_name}")
                return jsonify({'error': f'Script not found: {script_name}'}), 500
            
            logger.info(f"✅ Script exists: {script_name}")
            logger.info(f"🏃 Running subprocess: {sys.executable} {script_name}")
            
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                env=env,
                timeout=int(runtime_config['timeout']),
                cwd=os.getcwd()
            )
            
        elif step == 3:
            # Run dfd_to_threats.py
            script_name = 'dfd_to_threats.py'
            logger.info(f"📜 Step 3: Running {script_name}")
            add_log("Generating threats using STRIDE...", 'info')
            
            env['DFD_INPUT_PATH'] = os.path.join(OUTPUT_FOLDER, 'dfd_components.json')
            env['THREATS_OUTPUT_PATH'] = os.path.join(OUTPUT_FOLDER, 'identified_threats.json')
            output_file = env['THREATS_OUTPUT_PATH']
            
            logger.info(f"📂 Input file: {env['DFD_INPUT_PATH']}")
            logger.info(f"📁 Output file: {output_file}")
            
            # Check if DFD file exists
            if not os.path.exists(env['DFD_INPUT_PATH']):
                logger.error(f"❌ DFD input file not found: {env['DFD_INPUT_PATH']}")
                # List what files DO exist
                if os.path.exists(OUTPUT_FOLDER):
                    existing_files = os.listdir(OUTPUT_FOLDER)
                    logger.info(f"📋 Files in output folder: {existing_files}")
                return jsonify({'error': 'DFD file not found. Run step 2 first.'}), 400
            
            # Log the DFD file content for debugging
            try:
                with open(env['DFD_INPUT_PATH'], 'r') as f:
                    dfd_content = json.load(f)
                logger.info(f"✅ DFD file exists and is valid JSON")
                logger.info(f"📄 DFD file keys: {list(dfd_content.keys())}")
                if 'dfd' in dfd_content:
                    logger.info(f"📄 Nested DFD keys: {list(dfd_content['dfd'].keys())}")
            except Exception as e:
                logger.error(f"❌ Could not read DFD file: {e}")
                return jsonify({'error': f'DFD file is corrupted: {e}'}), 500
            
            # Check if script exists
            if not os.path.exists(script_name):
                logger.error(f"❌ Script not found: {script_name}")
                return jsonify({'error': f'Script not found: {script_name}'}), 500
            
            logger.info(f"✅ Script exists: {script_name}")
            logger.info(f"🏃 Running subprocess: {sys.executable} {script_name}")
            
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                env=env,
                timeout=int(runtime_config['timeout']),
                cwd=os.getcwd()
            )
            
        elif step == 4:
            # Run improve_threat_quality.py
            script_name = 'improve_threat_quality.py'
            add_log("Refining and improving threat quality...", 'info')
            
            env.update({
                'DFD_INPUT_PATH': os.path.join(OUTPUT_FOLDER, 'dfd_components.json'),
                'THREATS_INPUT_PATH': os.path.join(OUTPUT_FOLDER, 'identified_threats.json'),
                'REFINED_THREATS_OUTPUT_PATH': os.path.join(OUTPUT_FOLDER, 'refined_threats.json'),
                'SIMILARITY_THRESHOLD': '0.80',
                'CVE_RELEVANCE_YEARS': '5'
            })
            output_file = env['REFINED_THREATS_OUTPUT_PATH']
            
            # Check prerequisites
            for prereq in [env['DFD_INPUT_PATH'], env['THREATS_INPUT_PATH']]:
                if not os.path.exists(prereq):
                    return jsonify({'error': f'Required file not found: {os.path.basename(prereq)}. Run previous steps first.'}), 400
            
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                env=env,
                timeout=int(runtime_config['timeout']),
                cwd=os.getcwd()
            )
            
        elif step == 5:
            # Run attack_path_analyzer.py
            script_name = 'attack_path_analyzer.py'
            add_log("Analyzing attack paths...", 'info')
            
            env.update({
                'REFINED_THREATS_PATH': os.path.join(OUTPUT_FOLDER, 'refined_threats.json'),
                'DFD_PATH': os.path.join(OUTPUT_FOLDER, 'dfd_components.json'),
                'ATTACK_PATHS_OUTPUT': os.path.join(OUTPUT_FOLDER, 'attack_paths.json'),
                'MAX_PATH_LENGTH': '5',
                'MAX_PATHS_TO_ANALYZE': '20',
                'ENABLE_VECTOR_STORE': 'false'
            })
            output_file = env['ATTACK_PATHS_OUTPUT']
            
            # Check prerequisites
            for prereq in [env['REFINED_THREATS_PATH'], env['DFD_PATH']]:
                if not os.path.exists(prereq):
                    return jsonify({'error': f'Required file not found: {os.path.basename(prereq)}. Run previous steps first.'}), 400
            
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                env=env,
                timeout=int(runtime_config['timeout']),
                cwd=os.getcwd()
            )
            
        else:
            return jsonify({'error': f'Unknown step: {step}'}), 400
        
        # Log subprocess output for debugging
        if result:
            logger.info("="*40)
            logger.info("SUBPROCESS RESULT")
            logger.info("="*40)
            logger.info(f"🔢 Return code: {result.returncode}")
            
            if result.stdout:
                logger.info("📤 STDOUT:")
                logger.info(result.stdout[:2000])  # First 2000 chars
                if len(result.stdout) > 2000:
                    logger.info("... (truncated)")
                    
            if result.stderr:
                logger.info("📤 STDERR:")
                logger.info(result.stderr[:2000])  # First 2000 chars
                if len(result.stderr) > 2000:
                    logger.info("... (truncated)")
            
            logger.info("="*40)
        
        # Check subprocess result
        if result and result.returncode != 0:
            error_msg = result.stderr or result.stdout or f'Script {script_name} failed with exit code {result.returncode}'
            add_log(f"Step {step} failed: {error_msg}", 'error')
            logger.error(f"❌ Step {step} subprocess failed:")
            logger.error(f"  Return code: {result.returncode}")
            logger.error(f"  Stdout: {result.stdout}")
            logger.error(f"  Stderr: {result.stderr}")
            return jsonify({'error': f'Script execution failed: {error_msg}'}), 500
        
        logger.info(f"✅ Subprocess completed successfully for step {step}")
        
        # Load and validate the output
        logger.info(f"📁 Checking output file: {output_file}")
        
        if output_file and os.path.exists(output_file):
            logger.info(f"✅ Output file exists: {output_file}")
            file_size = os.path.getsize(output_file)
            logger.info(f"📏 File size: {file_size} bytes")
            
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    step_data = json.load(f)
                
                logger.info(f"✅ Output file is valid JSON")
                logger.info(f"📄 Output data type: {type(step_data)}")
                
                if isinstance(step_data, dict):
                    logger.info(f"📄 Output keys: {list(step_data.keys())}")
                    
                    # Log some statistics
                    if step == 2 and 'dfd' in step_data:
                        dfd = step_data['dfd']
                        logger.info(f"📊 DFD statistics:")
                        logger.info(f"  - Processes: {len(dfd.get('processes', []))}")
                        logger.info(f"  - Assets: {len(dfd.get('assets', []))}")
                        logger.info(f"  - External entities: {len(dfd.get('external_entities', []))}")
                        logger.info(f"  - Data flows: {len(dfd.get('data_flows', []))}")
                    elif step in [3, 4] and 'threats' in step_data:
                        threats = step_data['threats']
                        logger.info(f"📊 Threats statistics:")
                        logger.info(f"  - Total threats: {len(threats)}")
                        if threats:
                            risk_counts = {}
                            for threat in threats:
                                risk = threat.get('risk_score', 'Unknown')
                                risk_counts[risk] = risk_counts.get(risk, 0) + 1
                            logger.info(f"  - Risk distribution: {risk_counts}")
                
                # Validate structure
                validation = validate_json_structure(step_data, step)
                logger.info(f"📋 Validation result: {validation}")
                
                if not validation['valid']:
                    add_log(f"Step {step} validation errors: {', '.join(validation['errors'])}", 'warning')
                    logger.warning(f"⚠️ Validation warnings: {validation['warnings']}")
                
                with state_lock:
                    pipeline_state['validations'][step] = validation
                    pipeline_state['step_outputs'][step] = step_data
                    logger.info(f"💾 Step {step} data saved to pipeline state")
                
                # Calculate count for response
                count = 0
                if step == 2 and 'dfd' in step_data:
                    dfd = step_data['dfd']
                    count = (len(dfd.get('processes', [])) + 
                            len(dfd.get('assets', [])) +
                            len(dfd.get('external_entities', [])))
                elif step in [3, 4] and 'threats' in step_data:
                    count = len(step_data['threats'])
                elif step == 5 and 'attack_paths' in step_data:
                    count = len(step_data['attack_paths'])
                
                add_log(f"Step {step} completed: {count} items found", 'success')
                logger.info(f"🎉 Step {step} completed successfully with {count} items")
                
                response_data = {
                    **step_data,
                    'count': count,
                    'validation': validation,
                    'step': step,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.info(f"📤 Returning response data with keys: {list(response_data.keys())}")
                return jsonify(response_data)
                
            except json.JSONDecodeError as e:
                add_log(f"Step {step} output is not valid JSON: {e}", 'error')
                logger.error(f"❌ JSON decode error: {e}")
                
                # Try to read the file as text to see what's wrong
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                    logger.error(f"📄 Raw file content (first 500 chars): {raw_content[:500]}")
                except Exception as read_error:
                    logger.error(f"❌ Could not read raw file: {read_error}")
                
                return jsonify({'error': f'Script output is not valid JSON: {e}'}), 500
                
            except Exception as e:
                add_log(f"Step {step} failed to process output: {e}", 'error')
                logger.error(f"❌ Error processing output: {e}")
                return jsonify({'error': f'Failed to process output: {e}'}), 500
        else:
            add_log(f"Step {step} output file not created: {output_file}", 'error')
            logger.error(f"❌ Output file not created: {output_file}")
            
            # List what files DO exist in the output directory
            if os.path.exists(OUTPUT_FOLDER):
                existing_files = os.listdir(OUTPUT_FOLDER)
                logger.error(f"📋 Files in output directory: {existing_files}")
            else:
                logger.error(f"❌ Output directory doesn't exist: {OUTPUT_FOLDER}")
            
            return jsonify({'error': f'Output file not created: {output_file}'}), 500
            
    except subprocess.TimeoutExpired:
        add_log(f"Step {step} timed out after {runtime_config['timeout']} seconds", 'error')
        return jsonify({'error': f'Script execution timed out after {runtime_config["timeout"]} seconds'}), 500
    except FileNotFoundError as e:
        add_log(f"Step {step} script not found: {e}", 'error')
        return jsonify({'error': f'Required script not found: {e}'}), 500
    except Exception as e:
        logger.error(f"Step execution error: {str(e)}\n{traceback.format_exc()}")
        add_log(f"Step execution error: {str(e)}", 'error')
        return jsonify({'error': f'Step execution failed: {str(e)}'}), 500

@app.route('/api/save-step', methods=['POST'])
def save_step():
    """Save edited data for a specific step."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        step = data.get('step')
        step_data = data.get('data')
        
        if not step or not step_data:
            return jsonify({'error': 'Missing step or data parameter'}), 400
        
        # Validate the new data
        validation = validate_json_structure(step_data, step)
        if not validation['valid']:
            return jsonify({
                'error': 'Invalid data structure',
                'validation': validation
            }), 400
        
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
                add_log(f"Created backup: {os.path.basename(backup_path)}", 'info')
            
            # Save new data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(step_data, f, indent=2, ensure_ascii=False)
            
            # Update state
            with state_lock:
                pipeline_state['step_outputs'][step] = step_data
                pipeline_state['validations'][step] = validation
            
            add_log(f"Saved changes to {files[step]}", 'success')
            return jsonify({
                'status': 'saved',
                'file': files[step],
                'validation': validation
            })
        
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
                'session_id': pipeline_state['current_session'],
                'validations': pipeline_state.get('validations', {}),
                'steps': {}
            }
            
            for step_num in range(1, 6):
                if step_num in pipeline_state.get('step_outputs', {}):
                    complete_data['steps'][step_num] = pipeline_state['step_outputs'][step_num]
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(complete_data, temp_file, indent=2)
            temp_file.close()
            
            return send_file(
                temp_file.name, 
                as_attachment=True, 
                download_name=f'threat_model_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                mimetype='application/json'
            )
        
        elif step in files:
            file_path = os.path.join(OUTPUT_FOLDER, files[step])
            if os.path.exists(file_path):
                return send_file(
                    file_path, 
                    as_attachment=True,
                    download_name=f'{files[step].replace(".json", "")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                    mimetype='application/json'
                )
            else:
                return jsonify({'error': 'File not found'}), 404
        
        return jsonify({'error': 'Invalid step'}), 400
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get pipeline execution logs."""
    try:
        with state_lock:
            # Get last N logs
            limit = request.args.get('limit', 100, type=int)
            logs = pipeline_state['logs'][-limit:]
        
        return jsonify({'logs': logs})
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current pipeline status."""
    try:
        with state_lock:
            completed_steps = []
            for step in range(1, 6):
                if step in pipeline_state.get('step_outputs', {}):
                    completed_steps.append(step)
            
            status = {
                'session_id': pipeline_state['current_session'],
                'completed_steps': completed_steps,
                'validations': pipeline_state.get('validations', {}),
                'last_log': pipeline_state['logs'][-1] if pipeline_state['logs'] else None,
                'timestamp': datetime.now().isoformat()
            }
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/step-progress/<int:step>', methods=['GET'])
def get_step_progress(step):
    """Get real-time progress for a running step."""
    try:
        progress_file = os.path.join(OUTPUT_FOLDER, f'step_{step}_progress.json')
        
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            return jsonify(progress_data)
        else:
            return jsonify({
                'status': 'unknown',
                'progress': 0,
                'message': 'No progress information available'
            })
    except Exception as e:
        logger.error(f"Progress check error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/kill-step/<int:step>', methods=['POST'])
def kill_step(step):
    """Emergency stop for a running step."""
    try:
        # This is a simple implementation - in a production system you'd track process IDs
        kill_file = os.path.join(OUTPUT_FOLDER, f'step_{step}_kill.flag')
        with open(kill_file, 'w') as f:
            f.write(datetime.now().isoformat())
        
        add_log(f"Kill signal sent for step {step}", 'warning')
        return jsonify({'status': 'kill_signal_sent'})
    except Exception as e:
        logger.error(f"Kill step error: {e}")
        return jsonify({'error': str(e)}), 500
        self.logger.info(f"Debug state error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'session': pipeline_state['current_session'],
            'has_api_key': bool(runtime_config['scw_secret_key']),
            'scripts_available': all(os.path.exists(s) for s in scripts),
            'directories': {
                'upload': os.path.exists(UPLOAD_FOLDER),
                'output': os.path.exists(OUTPUT_FOLDER),
                'input': os.path.exists(INPUT_FOLDER)
            },
            'dependencies': {
                'pdf_support': PDF_AVAILABLE,
                'docx_support': DOCX_AVAILABLE
            },
            'config': {
                'llm_provider': runtime_config['llm_provider'],
                'llm_model': runtime_config['llm_model'],
                'timeout': runtime_config['timeout']
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug-state', methods=['GET'])
def debug_state():
    """Debug endpoint to check pipeline state."""
    try:
        with state_lock:
            debug_info = {
                'current_session': pipeline_state.get('current_session'),
                'completed_steps': list(pipeline_state.get('step_outputs', {}).keys()),
                'step_outputs_summary': {
                    step: {
                        'exists': bool(data),
                        'keys': list(data.keys()) if isinstance(data, dict) else None,
                        'type': type(data).__name__
                    }
                    for step, data in pipeline_state.get('step_outputs', {}).items()
                },
                'files_on_disk': {
                    'dfd_components.json': os.path.exists(os.path.join(OUTPUT_FOLDER, 'dfd_components.json')),
                    'identified_threats.json': os.path.exists(os.path.join(OUTPUT_FOLDER, 'identified_threats.json')),
                    'refined_threats.json': os.path.exists(os.path.join(OUTPUT_FOLDER, 'refined_threats.json')),
                    'attack_paths.json': os.path.exists(os.path.join(OUTPUT_FOLDER, 'attack_paths.json'))
                },
                'timestamp': datetime.now().isoformat()
            }
        
        return jsonify(debug_info)
    except Exception as e:
        logger.error(f"Debug state error: {e}")
        return jsonify({'error': str(e)}), 500
def health_check():
    """Health check endpoint."""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'session': pipeline_state['current_session'],
            'has_api_key': bool(runtime_config['scw_secret_key']),
            'scripts_available': all(os.path.exists(s) for s in scripts),
            'directories': {
                'upload': os.path.exists(UPLOAD_FOLDER),
                'output': os.path.exists(OUTPUT_FOLDER),
                'input': os.path.exists(INPUT_FOLDER)
            },
            'dependencies': {
                'pdf_support': PDF_AVAILABLE,
                'docx_support': DOCX_AVAILABLE
            },
            'config': {
                'llm_provider': runtime_config['llm_provider'],
                'llm_model': runtime_config['llm_model'],
                'timeout': runtime_config['timeout']
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug-load-files', methods=['GET', 'POST'])
def debug_load_files():
    """Debug endpoint to manually load existing output files into pipeline state."""
    try:
        files_loaded = {}
        
        # Define file mappings
        file_mappings = {
            2: ('dfd_components.json', 'DFD'),
            3: ('identified_threats.json', 'Threats'),
            4: ('refined_threats.json', 'Refined Threats'),
            5: ('attack_paths.json', 'Attack Paths')
        }
        
        with state_lock:
            # Ensure we have a session
            if not pipeline_state.get('current_session'):
                pipeline_state['current_session'] = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for step, (filename, description) in file_mappings.items():
                filepath = os.path.join(OUTPUT_FOLDER, filename)
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        
                        pipeline_state['step_outputs'][step] = data
                        files_loaded[step] = {
                            'status': 'loaded',
                            'file': filename,
                            'description': description,
                            'data_type': type(data).__name__,
                            'keys': list(data.keys()) if isinstance(data, dict) else None
                        }
                        
                        # Add basic upload data for step 1 if missing
                        if 1 not in pipeline_state['step_outputs'] and step == 2:
                            pipeline_state['step_outputs'][1] = {
                                'status': 'success',
                                'session_id': pipeline_state['current_session'],
                                'filename': 'debug_recovery.txt',
                                'text_length': 1000,
                                'count': 1
                            }
                            files_loaded[1] = {
                                'status': 'simulated',
                                'description': 'Upload step simulated for recovery'
                            }
                        
                        logger.info(f"✅ Loaded {filename} into step {step}")
                        
                    except Exception as e:
                        files_loaded[step] = {
                            'status': 'error',
                            'file': filename,
                            'error': str(e)
                        }
                        logger.error(f"❌ Failed to load {filename}: {e}")
                else:
                    files_loaded[step] = {
                        'status': 'not_found',
                        'file': filename
                    }
        
        return jsonify({
            'status': 'debug_load_complete',
            'files_loaded': files_loaded,
            'current_session': pipeline_state.get('current_session'),
            'completed_steps': list(pipeline_state.get('step_outputs', {}).keys())
        })
        
    except Exception as e:
        logger.error(f"Debug load files error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_pipeline():
    """Reset the pipeline state."""
    global pipeline_state
    
    try:
        with state_lock:
            # Save current session before reset if requested
            if pipeline_state['current_session'] and request.is_json:
                request_data = request.get_json() or {}
                if request_data.get('save_session', False):
                    session_backup = {
                        'session_id': pipeline_state['current_session'],
                        'timestamp': datetime.now().isoformat(),
                        'step_outputs': pipeline_state.get('step_outputs', {}),
                        'validations': pipeline_state.get('validations', {})
                    }
                    backup_file = os.path.join(OUTPUT_FOLDER, f'session_backup_{pipeline_state["current_session"]}.json')
                    with open(backup_file, 'w') as f:
                        json.dump(session_backup, f, indent=2)
                    add_log(f"Session backed up to {os.path.basename(backup_file)}", 'info')
            
            # Reset state
            pipeline_state = {
                'current_session': None,
                'logs': [],
                'step_outputs': {},
                'validations': {}
            }
        
        # Optionally clean output directory
        if request.is_json:
            request_data = request.get_json() or {}
            if request_data.get('clean_output', False):
                for file in os.listdir(OUTPUT_FOLDER):
                    if file.endswith('.json') and not file.startswith('session_backup'):
                        try:
                            os.remove(os.path.join(OUTPUT_FOLDER, file))
                        except Exception as e:
                            logger.warning(f"Failed to remove {file}: {e}")
        
        add_log("Pipeline reset", 'info')
        return jsonify({'status': 'reset', 'timestamp': datetime.now().isoformat()})
        
    except Exception as e:
        logger.error(f"Reset error: {e}")
        return jsonify({'error': str(e)}), 500

# Add a catch-all error handler
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({
        'error': 'Internal server error',
        'message': str(e),
        'timestamp': datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    logger.info("Starting Threat Modeling Pipeline Backend...")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Output folder: {OUTPUT_FOLDER}")
    logger.info(f"Input folder: {INPUT_FOLDER}")
    
    # Final check for API key
    if not runtime_config['scw_secret_key']:
        logger.warning("⚠️  No API key found! The LLM calls will fail.")
        logger.warning("Please create a .env file with: SCW_SECRET_KEY=your_key_here")
    
    # Create required directories
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, INPUT_FOLDER]:
        try:
            os.makedirs(folder, exist_ok=True)
            logger.info(f"✓ Directory ready: {folder}")
        except Exception as e:
            logger.error(f"✗ Failed to create directory {folder}: {e}")
    
    # Test file permissions
    try:
        test_file = os.path.join(OUTPUT_FOLDER, 'test_permissions.txt')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info("✓ File system permissions OK")
    except Exception as e:
        logger.error(f"✗ File system permission error: {e}")
    
    logger.info("Backend ready!")
    app.run(debug=True, port=5000, host='0.0.0.0')