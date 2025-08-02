from flask import jsonify, request
from datetime import datetime
from services.pipeline_service import PipelineService
from models.pipeline_state import PipelineState
from utils.logging_utils import logger
import subprocess
import os
import traceback

def register_pipeline_routes(app, pipeline_state: PipelineState, runtime_config, socketio, output_folder, input_folder):
    @app.route('/api/progress/<session_id>', methods=['GET'])
    def get_progress(session_id):
        try:
            with pipeline_state.lock:
                if session_id == 'latest':
                    session_id = pipeline_state.state.get('current_session')
                if not session_id:
                    return jsonify({
                        'error': 'No active session',
                        'overall_percentage': 0,
                        'current_step': 0,
                        'status': 'idle'
                    })
                session_progress = pipeline_state.state.get('progress', {}).get(session_id, {})
            overall_progress = {
                'overall_percentage': 0,
                'current_step': 0,
                'status': 'unknown',
                'steps': [],
                'elapsed_time': 0
            }
            step_info = [
                {'name': 'Document Upload', 'description': 'Upload and extract text from documents'},
                {'name': 'DFD Extraction', 'description': 'Extract data flow diagram components'},
                {'name': 'Threat Identification', 'description': 'Identify threats using STRIDE methodology'},
                {'name': 'Threat Refinement', 'description': 'Improve and enrich threat quality'},
                {'name': 'Attack Path Analysis', 'description': 'Analyze potential attack paths'}
            ]
            completed_steps = 0
            current_step_num = 0
            all_steps_data = []
            for i in range(1, 6):
                step_completed = i in pipeline_state.state.get('step_outputs', {})
                step_progress_data = PipelineService.get_step_progress(i, output_folder)
                if i in session_progress:
                    step_progress_data.update(session_progress[i])
                step_data = {
                    'name': step_info[i-1]['name'],
                    'description': step_info[i-1]['description'],
                    'percentage': 100 if step_completed else step_progress_data.get('progress', 0),
                    'status': 'completed' if step_completed else step_progress_data.get('status', 'pending'),
                    'details': step_progress_data.get('message', ''),
                    'sub_steps': step_progress_data.get('sub_steps', [])
                }
                all_steps_data.append(step_data)
                if step_completed:
                    completed_steps += 1
                elif step_data['status'] == 'running':
                    current_step_num = i
            if current_step_num > 0:
                current_step_progress = all_steps_data[current_step_num - 1]['percentage']
                overall_progress['overall_percentage'] = ((completed_steps + current_step_progress / 100) / 5) * 100
                overall_progress['current_step'] = current_step_num
                overall_progress['status'] = 'running'
            else:
                overall_progress['overall_percentage'] = (completed_steps / 5) * 100
                overall_progress['current_step'] = completed_steps
                overall_progress['status'] = 'completed' if completed_steps == 5 else 'idle'
            overall_progress['steps'] = all_steps_data
            return jsonify(overall_progress)
        except Exception as e:
            logger.error(f"Progress check error: {e}")
            return jsonify({
                'error': str(e),
                'overall_percentage': 0,
                'current_step': 0,
                'status': 'error'
            })

    @app.route('/api/run-step', methods=['POST'])
    def run_step():
        try:
            if not request.is_json:
                return jsonify({'error': 'Request must be JSON'}), 400
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            if 'step' not in data:
                return jsonify({'error': 'Missing step parameter'}), 400
            step = data['step']
            input_data = data.get('input', {})
            response_data = PipelineService.execute_step(step, input_data, runtime_config, pipeline_state, socketio, output_folder, input_folder)
            return jsonify(response_data)
        except subprocess.TimeoutExpired:
            pipeline_state.add_log(f"Step {step} timed out after {runtime_config['timeout']} seconds", 'error')
            return jsonify({'error': f'Script execution timed out'}), 500
        except Exception as e:
            logger.error(f"Step execution error: {str(e)}\n{traceback.format_exc()}")
            pipeline_state.add_log(f"Step execution error: {str(e)}", 'error')
            return jsonify({'error': f'Step execution failed: {str(e)}'}), 500

    @app.route('/api/save-step', methods=['POST'])
    def save_step():
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
            response = PipelineService.save_step_data(step, step_data, pipeline_state, output_folder)
            return jsonify(response)
        except Exception as e:
            logger.error(f"Save error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/debug-state', methods=['GET'])
    def debug_state():
        try:
            with pipeline_state.lock:
                debug_info = {
                    'current_session': pipeline_state.state.get('current_session'),
                    'completed_steps': list(pipeline_state.state.get('step_outputs', {}).keys()),
                    'review_queue_summary': {
                        step: len(items) for step, items in pipeline_state.state.get('review_queue', {}).items()
                    },
                    'total_reviews': len(pipeline_state.state.get('review_history', [])),
                    'files_on_disk': {
                        'dfd_components.json': os.path.exists(os.path.join(output_folder, 'dfd_components.json')),
                        'identified_threats.json': os.path.exists(os.path.join(output_folder, 'identified_threats.json')),
                        'refined_threats.json': os.path.exists(os.path.join(output_folder, 'refined_threats.json')),
                        'attack_paths.json': os.path.exists(os.path.join(output_folder, 'attack_paths.json'))
                    },
                    'timestamp': datetime.now().isoformat()
                }
            return jsonify(debug_info)
        except Exception as e:
            logger.error(f"Debug state error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/debug-load-files', methods=['GET', 'POST'])
    def debug_load_files():
        try:
            response = PipelineService.load_existing_files(pipeline_state, output_folder)
            return jsonify(response)
        except Exception as e:
            logger.error(f"Debug load files error: {e}")
            return jsonify({'error': str(e)}), 500