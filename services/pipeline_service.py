import json
import os
import subprocess
import sys
from datetime import datetime
from services.review_service import ReviewService
from services.validation_service import ValidationService
from utils.file_utils import save_step_data
from models.pipeline_state import PipelineState

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
            'SCW_API_URL': runtime_config['scw_api_url']
        }
        env.update(env_updates)
        if runtime_config['scw_secret_key']:
            env['SCW_SECRET_KEY'] = runtime_config['scw_secret_key']
            env['SCW_API_KEY'] = runtime_config['scw_secret_key']
        output_file = None
        script_name = None
        if step == 1:
            return pipeline_state.state['step_outputs'].get(1, {})
        elif step == 2:
            script_name = 'info_to_dfds.py'
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
        if script_name:
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
                pipeline_state.add_log(f"Step {step} failed: {error_msg}", 'error')
                if session_id:
                    PipelineService.update_progress(session_id, step, {
                        'status': 'error',
                        'progress': 0,
                        'message': error_msg
                    }, pipeline_state, socketio)
                raise RuntimeError(error_msg)
        if output_file and os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                step_data = json.load(f)
            validation = ValidationService.validate_json_structure(step_data, step)
            if not validation['valid']:
                pipeline_state.add_log(f"Step {step} validation errors: {', '.join(validation['errors'])}", 'warning')
            with pipeline_state.lock:
                pipeline_state.state['validations'][step] = validation
                pipeline_state.state['step_outputs'][step] = step_data
                review_items = ReviewService.generate_review_items(step, step_data)
                items_needing_review = [
                    item for item in review_items
                    if item['confidence'] < 0.8 or 'missing_fields' in item or 'attributes_needed' in item
                ]
                if items_needing_review:
                    pipeline_state.state['review_queue'][step] = items_needing_review
                    socketio.emit('reviews_available', {
                        'step': step,
                        'count': len(items_needing_review)
                    })
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
            pipeline_state.add_log(f"Step {step} completed: {count} items found", 'success')
            if session_id:
                PipelineService.update_progress(session_id, step, {
                    'status': 'completed',
                    'progress': 100,
                    'message': f'Step {step} completed successfully'
                }, pipeline_state, socketio)
            return {
                **step_data,
                'count': count,
                'validation': validation,
                'step': step,
                'timestamp': datetime.now().isoformat(),
                'review_needed': len(items_needing_review)
            }
        raise FileNotFoundError(f'Output file not created: {output_file}')

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
                        review_items = ReviewService.generate_review_items(step, data)
                        if review_items:
                            pipeline_state.state['review_queue'][step] = review_items
                        files_loaded[step] = {
                            'status': 'loaded',
                            'file': filename,
                            'description': description,
                            'review_items': len(review_items)
                        }
                        if 1 not in pipeline_state.state['step_outputs'] and step == 2:
                            pipeline_state.state['step_outputs'][1] = {
                                'status': 'success',
                                'session_id': pipeline_state.state['current_session'],
                                'filename': 'debug_recovery.txt',
                                'text_length': 1000,
                                'count': 1
                            }
                            files_loaded[1] = {
                                'status': 'simulated',
                                'description': 'Upload step simulated for recovery'
                            }
                    except Exception as e:
                        files_loaded[step] = {
                            'status': 'error',
                            'file': filename,
                            'error': str(e)
                        }
                else:
                    files_loaded[step] = {
                        'status': 'not_found',
                        'file': filename
                    }
        return {
            'status': 'debug_load_complete',
            'files_loaded': files_loaded,
            'current_session': pipeline_state.state.get('current_session'),
            'completed_steps': list(pipeline_state.state.get('step_outputs', {}).keys()),
            'pending_reviews': pipeline_state.count_pending_reviews()
        }