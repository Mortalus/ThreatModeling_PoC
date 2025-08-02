from datetime import datetime
import os
from werkzeug.utils import secure_filename
from utils.file_utils import allowed_file, extract_text_from_file
from models.pipeline_state import PipelineState
from utils.logging_utils import logger

def process_upload(file, upload_folder, input_folder, pipeline_state: PipelineState, output_folder):
    """Process uploaded file and ensure it's available for the pipeline."""
    if file.filename == '':
        raise ValueError('No file selected')
    if not allowed_file(file.filename):
        raise ValueError('File type not allowed. Please use TXT, PDF, or DOCX files.')
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    file_path = os.path.join(upload_folder, filename)
    
    # Save the uploaded file
    file.save(file_path)
    pipeline_state.add_log(f"File uploaded: {filename}", 'success')
    logger.info(f"Saved uploaded file to: {file_path}")
    
    # Extract text content
    text_content, error = extract_text_from_file(file_path)
    if error:
        pipeline_state.add_log(f"Text extraction failed: {error}", 'error')
        raise ValueError(f'Failed to extract text: {error}')
    
    if not text_content or len(text_content.strip()) < 10:
        pipeline_state.add_log("Extracted text is too short or empty", 'error')
        raise ValueError('Extracted text is empty or too short')
    
    # CRITICAL: Save to multiple locations to ensure info_to_dfds.py finds it
    
    # 1. Save to input_documents (where info_to_dfds.py looks by default)
    os.makedirs(input_folder, exist_ok=True)
    input_text_file = os.path.join(input_folder, f"{timestamp}_extracted.txt")
    with open(input_text_file, 'w', encoding='utf-8') as f:
        f.write(text_content)
    logger.info(f"Saved extracted text to input folder: {input_text_file}")
    
    # 2. Save to output folder (for compatibility)
    os.makedirs(output_folder, exist_ok=True)
    output_text_file = os.path.join(output_folder, f"{timestamp}_extracted.txt")
    with open(output_text_file, 'w', encoding='utf-8') as f:
        f.write(text_content)
    logger.info(f"Saved extracted text to output folder: {output_text_file}")
    
    # Update pipeline state
    pipeline_state.add_log(f"Text extracted: {len(text_content)} characters", 'success')
    
    session_id = timestamp
    upload_data = {
        'status': 'success',
        'session_id': session_id,
        'filename': filename,
        'file_path': file_path,
        'text_file_path': input_text_file,  # Point to input folder file
        'output_text_file': output_text_file,
        'text_preview': text_content[:500] + '...' if len(text_content) > 500 else text_content,
        'text_length': len(text_content),
        'count': 1
    }
    
    with pipeline_state.lock:
        pipeline_state.state['current_session'] = session_id
        pipeline_state.state['step_outputs'][1] = upload_data  # Step 1 is upload
        pipeline_state.state['current_input_file'] = input_text_file
        
    pipeline_state.add_log(f"Step 1 completed successfully: {filename}", 'success')
    logger.info(f"Upload processing complete. Files ready for pipeline.")
    
    return upload_data