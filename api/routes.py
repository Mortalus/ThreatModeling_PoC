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
            }
        })

    @app.route('/api/health', methods=['GET'])
    def health_check():
        try:
            # Check if all required scripts exist
            scripts = ['info_to_dfds.py', 'dfd_to_threats.py', 'improve_threat_quality.py', 'attack_path_analyzer.py']
            scripts_exist = all(os.path.exists(s) for s in scripts)
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'session': pipeline_state.state['current_session'],
                'has_api_key': bool(runtime_config['scw_secret_key']),
                'scripts_available': scripts_exist,
                'review_system': 'enabled',
                'pending_reviews': pipeline_state.count_pending_reviews(),
                'directories': {
                    'upload': os.path.exists(upload_folder),
                    'output': os.path.exists(output_folder),
                    'input': os.path.exists(input_folder)
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

    @app.route('/api/config', methods=['GET'])
    def get_config():
        """Get current configuration settings."""
        try:
            # Return the current runtime configuration
            # Filter out sensitive information
            safe_config = {
                'llm_provider': runtime_config['llm_provider'],
                'llm_model': runtime_config['llm_model'],
                'local_llm_endpoint': runtime_config['local_llm_endpoint'],
                'timeout': runtime_config['timeout'],
                'temperature': runtime_config['temperature'],
                'max_tokens': runtime_config['max_tokens'],
                'enable_quality_check': runtime_config.get('enable_quality_check', True),
                'enable_multi_pass': runtime_config.get('enable_multi_pass', True),
                'enable_mermaid': runtime_config.get('enable_mermaid', True),
                'enable_llm_enrichment': runtime_config.get('enable_llm_enrichment', True),
                'mitre_enabled': runtime_config.get('mitre_enabled', True),
                'mitre_version': runtime_config.get('mitre_version', 'v13.1'),
                'output_dir': output_folder,
                'input_dir': input_folder,
                # Don't send the actual API key, just whether it's set
                'has_api_key': bool(runtime_config.get('scw_secret_key'))
            }
            return jsonify(safe_config)
        except Exception as e:
            logger.error(f"Config fetch error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/config', methods=['POST'])
    def update_config():
        """Update runtime configuration settings."""
        try:
            new_config = request.get_json()
            if not new_config:
                return jsonify({'error': 'No configuration provided'}), 400
            
            # Update runtime configuration
            updates = {}
            
            # LLM settings
            if 'llm_provider' in new_config:
                updates['llm_provider'] = new_config['llm_provider']
                runtime_config['llm_provider'] = new_config['llm_provider']
            
            if 'llm_model' in new_config:
                updates['llm_model'] = new_config['llm_model']
                runtime_config['llm_model'] = new_config['llm_model']
            
            if 'scw_secret_key' in new_config and new_config['scw_secret_key']:
                updates['scw_secret_key'] = new_config['scw_secret_key']
                runtime_config['scw_secret_key'] = new_config['scw_secret_key']
                # Also set in environment for child processes
                os.environ['SCW_SECRET_KEY'] = new_config['scw_secret_key']
                os.environ['SCW_API_KEY'] = new_config['scw_secret_key']
            
            if 'local_llm_endpoint' in new_config:
                updates['local_llm_endpoint'] = new_config['local_llm_endpoint']
                runtime_config['local_llm_endpoint'] = new_config['local_llm_endpoint']
            
            # Processing parameters
            if 'timeout' in new_config:
                updates['timeout'] = int(new_config['timeout'])
                runtime_config['timeout'] = int(new_config['timeout'])
            
            if 'temperature' in new_config:
                updates['temperature'] = float(new_config['temperature'])
                runtime_config['temperature'] = float(new_config['temperature'])
            
            if 'max_tokens' in new_config:
                updates['max_tokens'] = int(new_config['max_tokens'])
                runtime_config['max_tokens'] = int(new_config['max_tokens'])
            
            # Feature flags
            for flag in ['enable_quality_check', 'enable_multi_pass', 'enable_mermaid', 
                         'enable_llm_enrichment', 'mitre_enabled']:
                if flag in new_config:
                    updates[flag] = bool(new_config[flag])
                    runtime_config[flag] = bool(new_config[flag])
            
            # Save configuration to file for persistence (optional)
            config_file = os.path.join(output_folder, 'runtime_config.json')
            with open(config_file, 'w') as f:
                json.dump(runtime_config, f, indent=2)
            
            # Log the configuration change
            logger.info(f"Configuration updated: {updates}")
            pipeline_state.add_log(f"Configuration updated: {', '.join(updates.keys())}", 'info')
            
            return jsonify({
                'status': 'success',
                'message': 'Configuration updated successfully',
                'updates': list(updates.keys())
            })
            
        except ValueError as e:
            logger.error(f"Invalid configuration value: {e}")
            return jsonify({'error': f'Invalid value: {str(e)}'}), 400
        except Exception as e:
            logger.error(f"Config update error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/config/reset', methods=['POST'])
    def reset_config():
        """Reset configuration to defaults."""
        try:
            # Reset to original configuration from Config class
            default_config = Config.get_config()
            
            # Update runtime configuration
            runtime_config.update(default_config)
            
            # Clear any custom API keys from environment
            if 'SCW_SECRET_KEY' in os.environ:
                del os.environ['SCW_SECRET_KEY']
            if 'SCW_API_KEY' in os.environ:
                del os.environ['SCW_API_KEY']
            
            # Remove saved config file if exists
            config_file = os.path.join(output_folder, 'runtime_config.json')
            if os.path.exists(config_file):
                os.remove(config_file)
            
            logger.info("Configuration reset to defaults")
            pipeline_state.add_log("Configuration reset to defaults", 'info')
            
            return jsonify({
                'status': 'success',
                'message': 'Configuration reset to defaults'
            })
            
        except Exception as e:
            logger.error(f"Config reset error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """Handle file upload."""
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file part'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400
            
            if file:
                # Process the upload with all required arguments
                result = process_upload(
                    file=file, 
                    upload_folder=upload_folder,
                    input_folder=input_folder,
                    pipeline_state=pipeline_state,
                    output_folder=output_folder
                )
                
                if result.get('error'):
                    return jsonify({'error': result['error']}), 400
                
                # Log the result to see what fields are available
                logger.info(f"Upload result: {result}")
                
                # Update pipeline state
                with pipeline_state.lock:
                    pipeline_state.state['uploaded_file'] = result.get('filename', 'unknown')
                    pipeline_state.state['step_outputs'][0] = {  # Step 0 is upload
                        'filename': result.get('filename', 'unknown'),
                        'text_length': result.get('text_length', 0),
                        'preview': result.get('preview', result.get('text_preview', 'No preview available'))
                    }
                
                pipeline_state.add_log(f"Uploaded file: {result.get('filename', 'unknown')}", 'success')
                
                return jsonify({
                    'status': 'success',
                    'filename': result.get('filename', 'unknown'),
                    'text_length': result.get('text_length', 0),
                    'preview': result.get('preview', result.get('text_preview', 'No preview available')),
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Upload error: {e}")
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500

    # Note: /api/run-step is registered in pipeline_routes.py to avoid duplication

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

    @app.route('/api/status', methods=['GET'])
    def get_status():
        """Get current pipeline status."""
        try:
            with pipeline_state.lock:
                return jsonify({
                    'session': pipeline_state.state['current_session'],
                    'steps': pipeline_state.state['step_outputs'],
                    'validations': pipeline_state.state['validations'],
                    'review_queue': pipeline_state.state['review_queue'],
                    'logs': pipeline_state.state['logs'][-20:],  # Last 20 logs
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Status error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/review-items', methods=['GET'])
    def get_review_items():
        """Get all review items across all steps."""
        try:
            with pipeline_state.lock:
                review_queue = pipeline_state.state.get('review_queue', {})
                all_items = []
                for step, items in review_queue.items():
                    all_items.extend(items)
            return jsonify(all_items)
        except Exception as e:
            logger.error(f"Error fetching review items: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/routes', methods=['GET'])
    def list_routes():
        """List all registered routes for debugging."""
        import urllib
        output = []
        for rule in app.url_map.iter_rules():
            methods = ','.join(rule.methods)
            line = urllib.parse.unquote(f"{rule.endpoint}: {methods} {rule}")
            output.append(line)
        return jsonify({'routes': sorted(output)})

    @app.route('/api/export/json', methods=['POST'])
    def export_json():
        """Export pipeline results as JSON."""
        try:
            data = request.get_json() or {}
            pipeline_data = data.get('pipeline_state', {})
            
            # Create export data
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'session': pipeline_state.state['current_session'],
                'pipeline': pipeline_data,
                'version': '1.0'
            }
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(export_data, f, indent=2)
                temp_path = f.name
            
            return send_file(
                temp_path,
                mimetype='application/json',
                as_attachment=True,
                download_name=f'threat-model-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
            )
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/export/markdown', methods=['POST'])
    def export_markdown():
        """Export pipeline results as Markdown."""
        try:
            data = request.get_json() or {}
            pipeline_data = data.get('pipeline_state', {})
            
            # Create markdown content
            md_content = f"""# Threat Model Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This threat model was generated using AI-powered analysis.

## DFD Components

{json.dumps(pipeline_data.get('steps', [{}])[1].get('data', {}), indent=2)}

## Identified Threats

{json.dumps(pipeline_data.get('steps', [{}])[2].get('data', {}), indent=2)}

## Attack Paths

{json.dumps(pipeline_data.get('steps', [{}])[4].get('data', {}), indent=2)}
"""
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(md_content)
                temp_path = f.name
            
            return send_file(
                temp_path,
                mimetype='text/markdown',
                as_attachment=True,
                download_name=f'threat-model-{datetime.now().strftime("%Y%m%d-%H%M%S")}.md'
            )
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return jsonify({'error': str(e)}), 500