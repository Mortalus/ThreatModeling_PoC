"""
Fixed pipeline_service.py - Now properly passes session information to DFD extraction
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from services.review_service import ReviewService
from services.validation_service import ValidationService
from utils.file_utils import save_step_data
from models.pipeline_state import PipelineState
from utils.logging_utils import logger

class PipelineService:
    @staticmethod
    def update_progress(session_id: str, step: int, data: dict, pipeline_state: PipelineState, socketio) -> None:
        with pipeline_state.lock:
            if session_id not in pipeline_state.state['progress']:
                pipeline_state.state['progress'][session_id] = {}
            pipeline_state.state['progress'][session_id][step] = {
                **data,
                'last_update': datetime.now().isoformat()
            }
        socketio.emit('progress_update', {
            'session_id': session_id,
            'step': step,
            'progress': data
        })

    @staticmethod
    def get_step_progress(step: int, output_folder: str) -> dict:
        progress_file = os.path.join(output_folder, f'step_{step}_progress.json')
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            'status': 'unknown',
            'progress': 0,
            'message': 'No progress information available'
        }

    @staticmethod
    def execute_step(step: int, input_data: dict, runtime_config: dict, pipeline_state: PipelineState, 
                    socketio, output_folder: str, input_folder: str) -> dict:
        if not isinstance(step, int) or step < 1 or step > 5:
            raise ValueError('Invalid step number. Must be 1-5.')
        
        if step > 1:
            with pipeline_state.lock:
                step_outputs = pipeline_state.state.get('step_outputs', {})
                prev_step_output = step_outputs.get(step - 1)
            if not prev_step_output:
                if step == 3:
                    dfd_file = os.path.join(output_folder, 'dfd_components.json')
                    if os.path.exists(dfd_file):
                        with open(dfd_file, 'r') as f:
                            pipeline_state.state['step_outputs'][2] = json.load(f)
                    else:
                        raise ValueError(f'Step {step - 1} must be completed first')
                else:
                    raise ValueError(f'Step {step - 1} must be completed first')
        
        pipeline_state.add_log(f"Starting step {step}", 'info')
        session_id = pipeline_state.state.get('current_session')
        if session_id:
            PipelineService.update_progress(session_id, step, {
                'status': 'running',
                'progress': 0,
                'message': f'Starting step {step}...'
            }, pipeline_state, socketio)
        
        env = os.environ.copy()
        
        # Base environment updates
        env_updates = {
            'INPUT_DIR': input_folder,
            'OUTPUT_DIR': output_folder,
            'LOG_LEVEL': 'INFO',
            'PIPELINE_TIMEOUT': str(runtime_config['timeout']),
            'LLM_PROVIDER': runtime_config['llm_provider'],
            'LLM_MODEL': runtime_config['llm_model'],
            'LOCAL_LLM_ENDPOINT': runtime_config['local_llm_endpoint'],
            'CUSTOM_SYSTEM_PROMPT': runtime_config['custom_system_prompt'],
            'MITRE_ENABLED': str(runtime_config['mitre_enabled']).lower(),
            'MITRE_VERSION': runtime_config['mitre_version'],
            'SCW_API_URL': runtime_config['scw_api_url'],
            'TEMPERATURE': str(runtime_config.get('temperature', 0.2)),
            'MAX_TOKENS': str(runtime_config.get('max_tokens', 4096)),
        }
        
        # **CRITICAL FIX**: Add session ID to environment for DFD extraction
        if session_id:
            env_updates['SESSION_ID'] = session_id
            logger.info(f"Setting SESSION_ID environment variable: {session_id}")
        
        env.update(env_updates)
        
        if runtime_config['scw_secret_key']:
            env['SCW_SECRET_KEY'] = runtime_config['scw_secret_key']
            env['SCW_API_KEY'] = runtime_config['scw_secret_key']
        
        # Log LLM configuration
        logger.info(f"LLM Configuration for step {step}:")
        logger.info(f"  Provider: {runtime_config['llm_provider']}")
        logger.info(f"  Model: {runtime_config['llm_model']}")
        logger.info(f"  Endpoint: {runtime_config.get('local_llm_endpoint', 'N/A')}")
        logger.info(f"  Session ID: {session_id}")
        
        output_file = None
        script_name = None
        
        if step == 1:
            # Step 1 is upload, handled separately
            logger.warning("Step 1 (upload) called through run-step API")
            return pipeline_state.state['step_outputs'].get(1, {})
            
        elif step == 2:
            script_name = 'info_to_dfds.py'
            
            # Get current session and file info
            current_session = pipeline_state.state.get('current_session')
            upload_data = pipeline_state.state.get('step_outputs', {}).get(1, {})
            
            if current_session:
                logger.info(f"Current session: {current_session}")
                
                # **ADDITIONAL FIX**: Verify uploaded file exists and create symlink if needed
                uploaded_file = upload_data.get('text_file_path') if upload_data else None
                if uploaded_file and os.path.exists(uploaded_file):
                    logger.info(f"Verified uploaded file exists: {uploaded_file}")
                    
                    # Ensure the file is also accessible with session ID naming
                    session_file = os.path.join(input_folder, f"{current_session}_extracted.txt")
                    if not os.path.exists(session_file):
                        try:
                            # Create a copy with session ID naming for compatibility
                            import shutil
                            shutil.copy2(uploaded_file, session_file)
                            logger.info(f"Created session file: {session_file}")
                        except Exception as e:
                            logger.warning(f"Could not create session file: {e}")
                else:
                    logger.warning(f"Uploaded file not found: {uploaded_file}")
                
                # Clean up old extracted files that don't match current session
                for dir_path in [input_folder, output_folder, './uploads', './output', './input_documents']:
                    if os.path.exists(dir_path):
                        for filename in os.listdir(dir_path):
                            if filename.endswith('_extracted.txt') and current_session not in filename:
                                old_file = os.path.join(dir_path, filename)
                                try:
                                    os.remove(old_file)
                                    logger.info(f"Removed old file: {old_file}")
                                except Exception as e:
                                    logger.warning(f"Could not remove old file {old_file}: {e}")
            
            output_file = os.path.join(output_folder, 'dfd_components.json')
            
        elif step == 3:
            script_name = 'dfd_to_threats.py'
            output_file = os.path.join(output_folder, 'identified_threats.json')
            
        elif step == 4:
            script_name = 'improve_threat_quality.py'
            output_file = os.path.join(output_folder, 'refined_threats.json')
            
        elif step == 5:
            script_name = 'attack_path_analyzer.py'
            output_file = os.path.join(output_folder, 'attack_paths.json')
        
        # Ensure cleanup of any progress tracking file for this step
        cleanup_progress_file(step, output_folder)
        
        if not script_name:
            raise ValueError(f'Unknown step: {step}')
        
        if not os.path.exists(script_name):
            raise FileNotFoundError(f'Script not found: {script_name}')
        
        # **ENHANCED LOGGING**: Show what files are available before running script
        logger.info(f"Files in input directory ({input_folder}):")
        if os.path.exists(input_folder):
            for file in os.listdir(input_folder):
                if file.endswith('.txt'):
                    file_path = os.path.join(input_folder, file)
                    file_size = os.path.getsize(file_path)
                    logger.info(f"  - {file} ({file_size} bytes)")
        else:
            logger.warning(f"Input directory does not exist: {input_folder}")
        
        logger.info(f"Files in output directory ({output_folder}):")
        if os.path.exists(output_folder):
            for file in os.listdir(output_folder):
                if file.endswith('.txt'):
                    file_path = os.path.join(output_folder, file)
                    file_size = os.path.getsize(file_path)
                    logger.info(f"  - {file} ({file_size} bytes)")
        
        # Run the script
        logger.info(f"Executing {script_name} for step {step}")
        
        try:
            result = subprocess.run(
                [sys.executable, script_name],
                env=env,
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=runtime_config['timeout']
            )
            
            # Log the script output
            if result.stdout:
                logger.info(f"Script output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Script stderr: {result.stderr}")
            
            if result.returncode != 0:
                error_msg = f"Script {script_name} failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Load and validate output
            if output_file and os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    output_data = json.load(f)
                
                # Store in pipeline state
                with pipeline_state.lock:
                    pipeline_state.state['step_outputs'][step] = output_data
                
                logger.info(f"Step {step} completed successfully")
                
                if session_id:
                    PipelineService.update_progress(session_id, step, {
                        'status': 'completed',
                        'progress': 100,
                        'message': f'Step {step} completed successfully'
                    }, pipeline_state, socketio)
                
                return output_data
            else:
                error_msg = f"Output file not generated: {output_file}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
        except subprocess.TimeoutExpired:
            error_msg = f"Script {script_name} timed out after {runtime_config['timeout']} seconds"
            logger.error(error_msg)
            if session_id:
                PipelineService.update_progress(session_id, step, {
                    'status': 'failed',
                    'progress': 0,
                    'message': error_msg
                }, pipeline_state, socketio)
            raise
        except Exception as e:
            error_msg = f"Script {script_name} execution failed: {str(e)}"
            logger.error(error_msg)
            if session_id:
                PipelineService.update_progress(session_id, step, {
                    'status': 'failed',
                    'progress': 0,
                    'message': error_msg
                }, pipeline_state, socketio)
            raise

    @staticmethod
    def save_step_data(step: int, step_data: dict, pipeline_state: PipelineState, output_folder: str) -> dict:
        """Save step data to both memory and disk."""
        try:
            # Save to pipeline state
            with pipeline_state.lock:
                pipeline_state.state['step_outputs'][step] = step_data
            
            # Save to disk
            filename = f'step_{step}_data.json'
            output_path = os.path.join(output_folder, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(step_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved step {step} data to {output_path}")
            pipeline_state.add_log(f"Step {step} data saved", 'success')
            
            return {'status': 'success', 'message': f'Step {step} data saved successfully'}
            
        except Exception as e:
            error_msg = f"Failed to save step {step} data: {str(e)}"
            logger.error(error_msg)
            pipeline_state.add_log(error_msg, 'error')
            return {'status': 'error', 'message': error_msg}

def cleanup_progress_file(step: int, output_folder: str) -> None:
    """Clean up any existing progress file for a step."""
    progress_file = os.path.join(output_folder, f'step_{step}_progress.json')
    if os.path.exists(progress_file):
        try:
            os.remove(progress_file)
            logger.info(f"Cleaned up progress file: {progress_file}")
        except Exception as e:
            logger.warning(f"Could not remove progress file: {e}")