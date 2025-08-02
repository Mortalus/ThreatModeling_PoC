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
    def update_progress(session_id, step, data, pipeline_state: PipelineState, socketio):
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
    def get_step_progress(step, output_folder):
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
    def execute_step(step, input_data, runtime_config, pipeline_state: PipelineState, socketio, output_folder, input_folder):
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
        env.update(env_updates)
        
        if runtime_config['scw_secret_key']:
            env['SCW_SECRET_KEY'] = runtime_config['scw_secret_key']
            env['SCW_API_KEY'] = runtime_config['scw_secret_key']
        
        # Log LLM configuration
        logger.info(f"LLM Configuration for step {step}:")
        logger.info(f"  Provider: {runtime_config['llm_provider']}")
        logger.info(f"  Model: {runtime_config['llm_model']}")
        logger.info(f"  Endpoint: {runtime_config.get('local_llm_endpoint', 'N/A')}")
        
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
                
                # Clean up old extracted files that don't match current session
                for dir_path in [input_folder, output_folder, './uploads', './output', './input_documents']:
                    if os.path.exists(dir_path):
                        for filename in os.listdir(dir_path):
                            if filename.endswith('_extracted.txt') and current_session not in filename:
                                old_file = os.path.join(dir_path, filename)
                                logger.info(f"Removing old file: {old_file}")
                                try:
                                    os.remove(old_file)
                                except Exception as e:
                                    logger.warning(f"Could not remove {old_file}: {e}")
            
            # Set INPUT_DIR to where the current file is
            current_text_file = upload_data.get('text_file_path') or upload_data.get('output_text_file')
            
            if current_text_file and os.path.exists(current_text_file):
                # Use the directory containing the current file
                env['INPUT_DIR'] = os.path.dirname(current_text_file)
                logger.info(f"Using INPUT_DIR from current file: {env['INPUT_DIR']}")
                logger.info(f"Processing file: {os.path.basename(current_text_file)}")
            else:
                # Fallback to finding the most recent file
                possible_dirs = [input_folder, output_folder, './uploads', './output', './input_documents']
                latest_file = None
                latest_time = 0
                
                for dir_path in possible_dirs:
                    if os.path.exists(dir_path):
                        for filename in os.listdir(dir_path):
                            if filename.endswith('_extracted.txt'):
                                file_path = os.path.join(dir_path, filename)
                                file_time = os.path.getmtime(file_path)
                                if file_time > latest_time:
                                    latest_time = file_time
                                    latest_file = file_path
                
                if latest_file:
                    env['INPUT_DIR'] = os.path.dirname(latest_file)
                    logger.info(f"Using most recent file: {latest_file}")
                else:
                    logger.error("No extracted text files found!")
                    # Log what's in each directory for debugging
                    for dir_path in possible_dirs:
                        if os.path.exists(dir_path):
                            files = [f for f in os.listdir(dir_path) if not f.startswith('.')]
                            logger.info(f"  {dir_path}: {files[:5]}")
            
            # Pass session ID to the script
            if current_session:
                env['SESSION_ID'] = current_session
            
            # Clear any old DFD output to force fresh extraction
            old_dfd = os.path.join(output_folder, 'dfd_components.json')
            if os.path.exists(old_dfd):
                logger.info(f"Removing old DFD output: {old_dfd}")
                try:
                    os.remove(old_dfd)
                except Exception as e:
                    logger.warning(f"Could not remove old DFD: {e}")
            
            env['DFD_OUTPUT_PATH'] = os.path.join(output_folder, 'dfd_components.json')
            output_file = env['DFD_OUTPUT_PATH']
            
        elif step == 3:
            script_name = 'dfd_to_threats.py'
            env['DFD_INPUT_PATH'] = os.path.join(output_folder, 'dfd_components.json')
            env['THREATS_OUTPUT_PATH'] = os.path.join(output_folder, 'identified_threats.json')
            output_file = env['THREATS_OUTPUT_PATH']
            
        elif step == 4:
            script_name = 'improve_threat_quality.py'
            env.update({
                'DFD_INPUT_PATH': os.path.join(output_folder, 'dfd_components.json'),
                'THREATS_INPUT_PATH': os.path.join(output_folder, 'identified_threats.json'),
                'REFINED_THREATS_OUTPUT_PATH': os.path.join(output_folder, 'refined_threats.json'),
                'SIMILARITY_THRESHOLD': '0.80',
                'CVE_RELEVANCE_YEARS': '5'
            })
            output_file = env['REFINED_THREATS_OUTPUT_PATH']
            
        elif step == 5:
            script_name = 'attack_path_analyzer.py'
            env.update({
                'REFINED_THREATS_PATH': os.path.join(output_folder, 'refined_threats.json'),
                'DFD_PATH': os.path.join(output_folder, 'dfd_components.json'),
                'ATTACK_PATHS_OUTPUT': os.path.join(output_folder, 'attack_paths.json'),
                'MAX_PATH_LENGTH': '5',
                'MAX_PATHS_TO_ANALYZE': '20',
                'ENABLE_VECTOR_STORE': 'false'
            })
            output_file = env['ATTACK_PATHS_OUTPUT']
        
        if script_name and not os.path.exists(script_name):
            raise FileNotFoundError(f'Script not found: {script_name}')
        
        # Log environment for debugging
        logger.info(f"Environment variables for {script_name}:")
        for key in ['LLM_PROVIDER', 'LLM_MODEL', 'LOCAL_LLM_ENDPOINT', 'INPUT_DIR', 'OUTPUT_DIR']:
            logger.info(f"  {key}: {env.get(key, 'NOT SET')}")
        
        if script_name:
            logger.info(f"Running script: {script_name}")
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                env=env,
                timeout=int(runtime_config['timeout']),
                cwd=os.getcwd()
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or f'Script {script_name} failed'
                logger.error(f"Script failed: {error_msg}")
                raise RuntimeError(error_msg)
            
            logger.info(f"Script completed successfully")
            
            # Log output for debugging
            if result.stdout:
                logger.debug(f"Script output (first 500 chars): {result.stdout[:500]}")
        
        if output_file and os.path.exists(output_file):
            logger.info(f"Loading output from: {output_file}")
            with open(output_file, 'r') as f:
                step_data = json.load(f)
            
            # Add metadata
            step_data['timestamp'] = datetime.now().isoformat()
            step_data['step'] = step
            
            # Validate and process
            validation = ValidationService.validate_json_structure(step_data, step)
            step_data['validation'] = validation
            
            # Save to pipeline state
            with pipeline_state.lock:
                pipeline_state.state['step_outputs'][step] = step_data
                pipeline_state.state['validations'][step] = validation
            
            # Generate review items
            review_items = ReviewService.generate_review_items(step, step_data)
            if review_items:
                with pipeline_state.lock:
                    pipeline_state.state['review_queue'][step] = review_items
            
            # Count items
            count = 0
            if step == 2:
                dfd = step_data.get('dfd', {})
                count = (len(dfd.get('external_entities', [])) + 
                        len(dfd.get('processes', [])) + 
                        len(dfd.get('assets', [])))
            elif step in [3, 4]:
                count = len(step_data.get('threats', []))
            elif step == 5:
                count = len(step_data.get('attack_paths', []))
            
            step_data['count'] = count
            step_data['review_needed'] = len(review_items)
            
            pipeline_state.add_log(f"Step {step} completed: {count} items", 'success')
            
            if session_id:
                PipelineService.update_progress(session_id, step, {
                    'status': 'completed',
                    'progress': 100,
                    'message': f'Step {step} completed successfully'
                }, pipeline_state, socketio)
            
            return step_data
            
        raise FileNotFoundError(f'Output file not created: {output_file}')

    @staticmethod
    def run_step(step, pipeline_state: PipelineState, runtime_config, input_folder, output_folder, socketio):
        """Wrapper for backward compatibility."""
        return PipelineService.execute_step(
            step=step,
            input_data={},
            runtime_config=runtime_config,
            pipeline_state=pipeline_state,
            socketio=socketio,
            output_folder=output_folder,
            input_folder=input_folder
        )

    @staticmethod
    def save_step_data(step, data, pipeline_state: PipelineState, output_folder):
        validation = ValidationService.validate_json_structure(data, step)
        if not validation['valid']:
            raise ValueError('Invalid data structure')
        save_step_data(step, data, output_folder)
        with pipeline_state.lock:
            pipeline_state.state['step_outputs'][step] = data
            pipeline_state.state['validations'][step] = validation
            review_items = ReviewService.generate_review_items(step, data)
            if review_items:
                pipeline_state.state['review_queue'][step] = review_items
        pipeline_state.add_log(f"Saved changes to step {step}", 'success')
        return {'status': 'saved', 'validation': validation}

    @staticmethod
    def load_existing_files(pipeline_state: PipelineState, output_folder):
        file_mappings = {
            2: ('dfd_components.json', 'DFD'),
            3: ('identified_threats.json', 'Threats'),
            4: ('refined_threats.json', 'Refined Threats'),
            5: ('attack_paths.json', 'Attack Paths')
        }
        files_loaded = {}
        with pipeline_state.lock:
            if not pipeline_state.state.get('current_session'):
                pipeline_state.state['current_session'] = datetime.now().strftime('%Y%m%d_%H%M%S')
            for step, (filename, description) in file_mappings.items():
                filepath = os.path.join(output_folder, filename)
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        pipeline_state.state['step_outputs'][step] = data
                        files_loaded[step] = description
                    except Exception as e:
                        logger.error(f"Failed to load {filename}: {e}")
        return files_loaded