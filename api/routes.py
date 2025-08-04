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
                'has_api_key': bool(runtime_config.get('scw_secret_key')),
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
                'has_api_key': bool(runtime_config.get('scw_secret_key')),
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
            
            # REMOVED: API key handling - API keys should only be managed via .env file
            # if 'scw_secret_key' in new_config:
            #     # This is removed for security - API keys must be in .env only
            
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
            
            # Save configuration to file for persistence (excluding API keys)
            config_file = os.path.join(output_folder, 'runtime_config.json')
            # Filter out any API keys before saving
            config_to_save = {k: v for k, v in runtime_config.items() 
                            if not k.endswith('_key') and not k.endswith('_secret')}
            with open(config_file, 'w') as f:
                json.dump(config_to_save, f, indent=2)
            
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
            
            # Update runtime configuration (but keep API keys from env)
            for key, value in default_config.items():
                if not key.endswith('_key') and not key.endswith('_secret'):
                    runtime_config[key] = value
            
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
                completed_steps = [
                    step for step in range(1, 6)
                    if step in pipeline_state.state.get('step_outputs', {})
                ]
                
                # Check for existing output files if no in-memory data
                if not completed_steps:
                    output_files = {
                        2: 'dfd_components.json',
                        3: 'identified_threats.json',
                        4: 'refined_threats.json',
                        5: 'attack_paths.json'
                    }
                    for step, filename in output_files.items():
                        if os.path.exists(os.path.join(output_folder, filename)):
                            completed_steps.append(step)
                
                return jsonify({
                    'completed_steps': completed_steps,
                    'total_steps': 5,
                    'current_session': pipeline_state.state.get('current_session'),
                    'review_stats': {
                        'pending': pipeline_state.count_pending_reviews(),
                        'completed': len(pipeline_state.state.get('review_history', []))
                    },
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Status error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/logs', methods=['GET'])
    def get_logs():
        """Get recent pipeline logs."""
        try:
            with pipeline_state.lock:
                logs = pipeline_state.state.get('logs', [])[-50:]  # Last 50 logs
            return jsonify({'logs': logs})
        except Exception as e:
            logger.error(f"Logs error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/export/<format>', methods=['GET'])
    def export_results(format):
        """Export results in various formats."""
        try:
            if format not in ['json', 'markdown', 'csv']:
                return jsonify({'error': 'Invalid format. Use json, markdown, or csv'}), 400
            
            # Gather all step outputs
            with pipeline_state.lock:
                data = {
                    'session': pipeline_state.state.get('current_session'),
                    'timestamp': datetime.now().isoformat(),
                    'dfd': pipeline_state.state.get('step_outputs', {}).get(2),
                    'threats': pipeline_state.state.get('step_outputs', {}).get(3),
                    'refined_threats': pipeline_state.state.get('step_outputs', {}).get(4),
                    'attack_paths': pipeline_state.state.get('step_outputs', {}).get(5),
                    'reviews': pipeline_state.state.get('review_history', [])
                }
            
            # Create export file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format}', delete=False)
            
            if format == 'json':
                json.dump(data, temp_file, indent=2)
                mimetype = 'application/json'
            elif format == 'markdown':
                # Convert to markdown
                md_content = f"# Threat Model Export\n\n"
                md_content += f"**Session:** {data['session']}\n"
                md_content += f"**Timestamp:** {data['timestamp']}\n\n"
                
                if data['dfd']:
                    md_content += "## Data Flow Diagram\n\n"
                    # Add DFD details...
                
                temp_file.write(md_content)
                mimetype = 'text/markdown'
            else:  # CSV
                # Convert to CSV format
                # This would need more complex handling for nested data
                mimetype = 'text/csv'
            
            temp_file.close()
            
            return send_file(
                temp_file.name,
                mimetype=mimetype,
                as_attachment=True,
                download_name=f'threat_model_{data["session"]}.{format}'
            )
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/version', methods=['GET'])
    def get_version():
        """Get application version information."""
        return jsonify({
            'version': '2.0.0',
            'features': {
                'review_system': True,
                'async_processing': True,
                'multi_llm_support': True,
                'mitre_integration': True
            }
        })
    
    @app.route('/api/ollama/models', methods=['GET'])
    def get_ollama_models():
        """Get available models from Ollama instance."""
        try:
            import requests
            
            # Get Ollama endpoint from config
            ollama_endpoint = runtime_config.get('local_llm_endpoint', 'http://localhost:11434')
            
            # Extract base URL (remove /api/generate if present)
            base_url = ollama_endpoint.replace('/api/generate', '').rstrip('/')
            
            # Call Ollama API to list models
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                models = []
                
                # Extract model names from the response
                for model in data.get('models', []):
                    model_info = {
                        'name': model.get('name', ''),
                        'size': model.get('size', 0),
                        'modified': model.get('modified_at', ''),
                        'digest': model.get('digest', '')
                    }
                    models.append(model_info)
                
                # Sort by name
                models.sort(key=lambda x: x['name'])
                
                return jsonify({
                    'status': 'success',
                    'models': models,
                    'endpoint': base_url
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': 'Failed to fetch models from Ollama',
                    'details': f'Status code: {response.status_code}'
                }), 500
                
        except requests.exceptions.ConnectionError:
            return jsonify({
                'status': 'error',
                'error': 'Cannot connect to Ollama',
                'details': 'Make sure Ollama is running on the specified endpoint'
            }), 503
        except requests.exceptions.Timeout:
            return jsonify({
                'status': 'error',
                'error': 'Ollama request timed out',
                'details': 'The Ollama server took too long to respond'
            }), 504
        except Exception as e:
            logger.error(f"Ollama models fetch error: {e}")
            return jsonify({
                'status': 'error',
                'error': 'Failed to fetch Ollama models',
                'details': str(e)
            }), 500