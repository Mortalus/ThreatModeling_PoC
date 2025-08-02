from flask import jsonify, request, send_file
from datetime import datetime
import json
import os
import tempfile
import traceback
from config.settings import Config
from models.pipeline_state import PipelineState
from services.document_service import process_upload
from services.pipeline_service import PipelineService
from utils.logging_utils import logger

def register_routes(app, pipeline_state: PipelineState, runtime_config, upload_folder, output_folder, input_folder, socketio):
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
        return jsonify({'error': 'Bad Request', 'message': str(e)}), 400

    @app.errorhandler(500)
    def handle_internal_error(e):
        logger.error(f"500 Internal Server Error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

    @app.route('/api/test', methods=['GET', 'POST'])
    def test_endpoint():
        return jsonify({
            'status': 'success',
            'method': request.method,
            'timestamp': datetime.now().isoformat(),
            'message': 'API is working',
            'config': {
                'llm_provider': runtime_config['llm_provider'],
                'has_api_key': bool(runtime_config['scw_secret_key']),
                'output_dir': output_folder,
                'input_dir': input_folder
            }
        })

    @app.route('/api/configuration', methods=['GET', 'POST'])
    def handle_configuration():
        global runtime_config
        if request.method == 'GET':
            return jsonify(runtime_config)
        elif request.method == 'POST':
            try:
                updates = request.get_json()
                if not updates:
                    return jsonify({'error': 'No JSON data provided'}), 400
                for key, value in updates.items():
                    if key in runtime_config:
                        runtime_config[key] = value
                        pipeline_state.add_log(f"Configuration updated: {key} = {value}", 'info')
                return jsonify({
                    'status': 'updated',
                    'configuration': runtime_config
                })
            except Exception as e:
                logger.error(f"Configuration update error: {e}")
                return jsonify({'error': str(e)}), 500

    @app.route('/api/upload', methods=['POST'])
    def upload_document():
        try:
            if 'document' not in request.files:
                return jsonify({'error': 'No file part in request'}), 400
            file = request.files['document']
            upload_data = process_upload(file, upload_folder, input_folder, pipeline_state, output_folder)
            return jsonify(upload_data)
        except Exception as e:
            logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
            pipeline_state.add_log(f"Upload error: {str(e)}", 'error')
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500

    @app.route('/api/export/<step>', methods=['GET'])
    def export_data(step):
        try:
            files = {
                '2': 'dfd_components.json',
                '3': 'identified_threats.json',
                '4': 'refined_threats.json',
                '5': 'attack_paths.json',
                'all': 'complete_analysis.json'
            }
            if step == 'all':
                complete_data = {
                    'export_date': datetime.now().isoformat(),
                    'session_id': pipeline_state.state['current_session'],
                    'validations': pipeline_state.state.get('validations', {}),
                    'review_summary': {
                        'total_reviews': len(pipeline_state.state.get('review_history', [])),
                        'pending_reviews': pipeline_state.count_pending_reviews()
                    },
                    'steps': {}
                }
                for step_num in range(1, 6):
                    if step_num in pipeline_state.state.get('step_outputs', {}):
                        complete_data['steps'][step_num] = pipeline_state.state['step_outputs'][step_num]
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
                file_path = os.path.join(output_folder, files[step])
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
        try:
            with pipeline_state.lock:
                limit = request.args.get('limit', 100, type=int)
                logs = pipeline_state.state['logs'][-limit:]
            return jsonify({'logs': logs})
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/status', methods=['GET'])
    def get_status():
        try:
            with pipeline_state.lock:
                completed_steps = []
                for step in range(1, 6):
                    if step in pipeline_state.state.get('step_outputs', {}):
                        completed_steps.append(step)
                status = {
                    'session_id': pipeline_state.state['current_session'],
                    'completed_steps': completed_steps,
                    'validations': pipeline_state.state.get('validations', {}),
                    'pending_reviews': pipeline_state.count_pending_reviews(),
                    'last_log': pipeline_state.state['logs'][-1] if pipeline_state.state['logs'] else None,
                    'timestamp': datetime.now().isoformat()
                }
            return jsonify(status)
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/health', methods=['GET'])
    def health_check():
        try:
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'session': pipeline_state.state['current_session'],
                'has_api_key': bool(runtime_config['scw_secret_key']),
                'scripts_available': all(os.path.exists(s) for s in ['info_to_dfds.py', 'dfd_to_threats.py', 'improve_threat_quality.py', 'attack_path_analyzer.py']),
                'review_system': 'enabled',
                'pending_reviews': pipeline_state.count_pending_reviews(),
                'directories': {
                    'upload': os.path.exists(upload_folder),
                    'output': os.path.exists(output_folder),
                    'input': os.path.exists(input_folder)
                },
                'dependencies': {
                    'pdf_support': 'PyPDF2' in globals(),  # Assuming import checks are global
                    'docx_support': 'DocxDocument' in globals()
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

    @app.route('/api/reset', methods=['POST'])
    def reset_pipeline():
        try:
            request_data = request.get_json() or {}
            pipeline_state.reset(
                save_session=request_data.get('save_session', False),
                clean_output=request_data.get('clean_output', False),
                output_folder=output_folder
            )
            return jsonify({'status': 'reset', 'timestamp': datetime.now().isoformat()})
        except Exception as e:
            logger.error(f"Reset error: {e}")
            return jsonify({'error': str(e)}), 500