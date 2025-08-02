from datetime import datetime
import os
from werkzeug.utils import secure_filename
from utils.file_utils import allowed_file, extract_text_from_file
from models.pipeline_state import PipelineState

def process_upload(file, upload_folder, input_folder, pipeline_state: PipelineState, output_folder):
    if file.filename == '':
        raise ValueError('No file selected')
    if not allowed_file(file.filename):
        raise ValueError('File type not allowed. Please use TXT, PDF, or DOCX files.')
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    pipeline_state.add_log(f"File uploaded: {filename}", 'success')
    text_content, error = extract_text_from_file(file_path)
    if error:
        pipeline_state.add_log(f"Text extraction failed: {error}", 'error')
        raise ValueError(f'Failed to extract text: {error}')
    if not text_content or len(text_content.strip()) < 10:
        pipeline_state.add_log("Extracted text is too short or empty", 'error')
        raise ValueError('Extracted text is empty or too short')
    text_file_path = os.path.join(input_folder, f"{timestamp}_extracted.txt")
    with open(text_file_path, 'w', encoding='utf-8') as f:
        f.write(text_content)
    pipeline_state.add_log(f"Text extracted: {len(text_content)} characters", 'success')
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
    with pipeline_state.lock:
        pipeline_state.state['current_session'] = session_id
        pipeline_state.state['step_outputs'][1] = upload_data
    pipeline_state.add_log(f"Step 1 completed successfully: {filename}", 'success')
    return upload_data