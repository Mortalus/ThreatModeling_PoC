"""
Fixed pipeline_service.py - Ensures proper handling of step transitions
and progress tracking for step 3 after DFD extraction.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from services.review_service import ReviewService
from services.validation_service import ValidationService
from utils.file_utils import save_step_data
from models.pipeline_state import PipelineState
from utils.logging_utils import logger

class PipelineService:
    @staticmethod
    def update_progress(session_id: str, step: int, data: dict, pipeline_state: PipelineState, socketio) -> None:
        """Update progress for a specific step and session."""
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
        """Get progress for a specific step from file or return default."""
        progress_file = os.path.join(output_folder, f'step_{step}_progress.json')
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not read progress file for step {step}: {e}")
        
        # Return proper default status
        return {
            'status': 'pending',  # Changed from 'unknown' to 'pending'
            'progress': 0,
            'message': 'Ready to start'
        }

    @staticmethod
    def verify_step_output(step: int, output_folder: str) -> bool:
        """Verify that step output exists and is valid."""
        output_files = {
            2: 'dfd_components.json',
            3: 'identified_threats.json',
            4: 'refined_threats.json',
            5: 'attack_paths.json'
        }
        
        if step not in output_files:
            return False
            
        output_file = os.path.join(output_folder, output_files[step])
        if not os.path.exists(output_file):
            return False
            
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
                # Basic validation that the file has content
                return bool(data)
        except Exception as e:
            logger.error(f"Invalid output file for step {step}: {e}")
            return False

    @staticmethod
    def execute_step(step: int, input_data: dict, runtime_config: dict, pipeline_state: PipelineState, 
                    socketio, output_folder: str, input_folder: str) -> dict:
        """Execute a specific pipeline step with improved error handling."""
        
        if not isinstance(step, int) or step < 1 or step > 5:
            raise ValueError('Invalid step number. Must be 1-5.')
        
        # Check if previous step is completed (except for step 1 and 2)
        if step > 2:
            with pipeline_state.lock:
                step_outputs = pipeline_state.state.get('step_outputs', {})
                prev_step_output = step_outputs.get(step - 1)
            
            if not prev_step_output:
                # Try to load from file if not in memory
                if step == 3:
                    dfd_file = os.path.join(output_folder, 'dfd_components.json')
                    if os.path.exists(dfd_file):
                        try:
                            with open(dfd_file, 'r') as f:
                                dfd_data = json.load(f)
                                # Store in pipeline state for next steps
                                with pipeline_state.lock:
                                    pipeline_state.state['step_outputs'][2] = dfd_data
                                logger.info(f"Loaded DFD data from file for step 3")
                        except Exception as e:
                            logger.error(f"Failed to load DFD data: {e}")
                            raise ValueError(f'Step 2 output (DFD) is missing or invalid')
                    else:
                        raise ValueError(f'Step 2 must be completed first - DFD file not found')
                else:
                    # For steps 4 and 5, check previous step
                    prev_file = {
                        4: 'identified_threats.json',
                        5: 'refined_threats.json'
                    }.get(step)
                    
                    if prev_file:
                        prev_path = os.path.join(output_folder, prev_file)
                        if not os.path.exists(prev_path):
                            raise ValueError(f'Step {step - 1} must be completed first')
        
        # Log step start
        pipeline_state.add_log(f"Starting step {step}", 'info')
        session_id = pipeline_state.state.get('current_session')
        
        if session_id:
            PipelineService.update_progress(session_id, step, {
                'status': 'running',
                'progress': 0,
                'message': f'Starting step {step}...'
            }, pipeline_state, socketio)
        
        # Prepare environment
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
        
        # Add session ID to environment for tracking
        if session_id:
            env_updates['SESSION_ID'] = session_id
        
        # Handle API keys securely
        for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GROQ_API_KEY', 
                   'GOOGLE_API_KEY', 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT',
                   'BEDROCK_ACCESS_KEY', 'BEDROCK_SECRET_KEY', 'BEDROCK_REGION']:
            value = runtime_config.get(key.lower()) or os.getenv(key)
            if value:
                env_updates[key] = value
        
        env.update(env_updates)
        
        # Determine script and output file
        script_name = None
        output_file = None
        
        if step == 2:
            script_name = 'info_to_dfds.py'
            
            # Ensure input files are available for DFD extraction
            with pipeline_state.lock:
                current_session = pipeline_state.state.get('current_session')
                uploaded_file = pipeline_state.state.get('uploaded_file')
            
            if current_session and uploaded_file:
                # Create session-specific file for better tracking
                uploaded_path = os.path.join(input_folder, uploaded_file)
                if uploaded_path.endswith('_extracted.txt'):
                    session_file = os.path.join(output_folder, f"session_{current_session}.txt")
                    
                    if os.path.exists(uploaded_path) and not os.path.exists(session_file):
                        try:
                            import shutil
                            shutil.copy2(uploaded_path, session_file)
                            logger.info(f"Created session file: {session_file}")
                        except Exception as e:
                            logger.warning(f"Could not create session file: {e}")
            
            output_file = os.path.join(output_folder, 'dfd_components.json')
            
        elif step == 3:
            script_name = 'dfd_to_threats.py'
            output_file = os.path.join(output_folder, 'identified_threats.json')
            
            # Verify DFD file exists before running
            dfd_file = os.path.join(output_folder, 'dfd_components.json')
            if not os.path.exists(dfd_file):
                raise ValueError('DFD components file not found. Please complete step 2 first.')
            
            # Set specific environment variable for DFD path
            env['DFD_INPUT_PATH'] = dfd_file
            
        elif step == 4:
            script_name = 'improve_threat_quality.py'
            output_file = os.path.join(output_folder, 'refined_threats.json')
            
        elif step == 5:
            script_name = 'attack_path_analyzer.py'
            output_file = os.path.join(output_folder, 'attack_paths.json')
        
        # Clean up any existing progress file
        cleanup_progress_file(step, output_folder)
        
        if not script_name:
            raise ValueError(f'No script defined for step {step}')
        
        # Execute the script
        try:
            logger.info(f"Executing: {sys.executable} {script_name}")
            logger.debug(f"Environment: {env_updates}")
            
            result = subprocess.run(
                [sys.executable, script_name],
                env=env,
                capture_output=True,
                text=True,
                timeout=runtime_config['timeout']
            )
            
            # Log output for debugging
            if result.stdout:
                logger.info(f"Step {step} stdout: {result.stdout[:500]}")
            if result.stderr:
                logger.warning(f"Step {step} stderr: {result.stderr[:500]}")
            
            # Check for successful execution
            if result.returncode != 0:
                error_msg = f"Script {script_name} failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                raise RuntimeError(error_msg)
            
            # Load and validate output
            if output_file and os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    output_data = json.load(f)
                
                # Store in pipeline state
                with pipeline_state.lock:
                    pipeline_state.state['step_outputs'][step] = output_data
                
                logger.info(f"Step {step} completed successfully")
                
                # Update progress to completed
                if session_id:
                    PipelineService.update_progress(session_id, step, {
                        'status': 'completed',
                        'progress': 100,
                        'message': f'Step {step} completed successfully'
                    }, pipeline_state, socketio)
                
                # Write final progress file
                progress_file = os.path.join(output_folder, f'step_{step}_progress.json')
                with open(progress_file, 'w') as f:
                    json.dump({
                        'status': 'completed',
                        'progress': 100,
                        'message': f'Step {step} completed',
                        'timestamp': datetime.now().isoformat()
                    }, f)
                
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