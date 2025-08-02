#!/usr/bin/env python3
"""
Enhanced Flask Backend for Threat Modeling Pipeline with Review System
Includes quality checkpoints, confidence scoring, and collaborative review
"""
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import traceback
from config.settings import Config
from models.pipeline_state import PipelineState
from utils.logging_utils import setup_logging, log_startup_info, logger
from api.routes import register_routes
from api.review_routes import register_review_routes
from api.pipeline_routes import register_pipeline_routes
from api.websockets import register_websocket_handlers
import os
from datetime import datetime

def create_app():
    runtime_config = Config.get_config()
    UPLOAD_FOLDER = './uploads'
    OUTPUT_FOLDER = runtime_config['output_dir']
    INPUT_FOLDER = runtime_config['input_dir']
    Config.ensure_directories(UPLOAD_FOLDER, OUTPUT_FOLDER, INPUT_FOLDER)
    app = Flask(__name__)
    CORS(app)
    socketio = SocketIO(app, cors_allowed_origins="*")
    setup_logging()
    pipeline_state = PipelineState()
    log_startup_info(runtime_config)
    if not runtime_config['scw_secret_key']:
        logger.warning("⚠️ No API key found! The LLM calls will fail.")
        logger.warning("Please create a .env file with: SCW_SECRET_KEY=your_key_here")
    test_file = os.path.join(OUTPUT_FOLDER, 'test_permissions.txt')
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info("✓ File system permissions OK")
    except Exception as e:
        logger.error(f"✗ File system permission error: {e}")
    register_routes(app, pipeline_state, runtime_config, UPLOAD_FOLDER, OUTPUT_FOLDER, INPUT_FOLDER, socketio)
    register_review_routes(app, pipeline_state, socketio, OUTPUT_FOLDER)
    register_pipeline_routes(app, pipeline_state, runtime_config, socketio, OUTPUT_FOLDER, INPUT_FOLDER)
    register_websocket_handlers(socketio, pipeline_state)
    logger.info("Starting Enhanced Threat Modeling Pipeline Backend...")
    logger.info("Review system: ENABLED")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Output folder: {OUTPUT_FOLDER}")
    logger.info(f"Input folder: {INPUT_FOLDER}")
    logger.info("Backend ready with review system!")

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app()
    socketio.run(app, debug=True, port=5000, host='0.0.0.0')
else:
    application, _ = create_app()  # Export 'application' for Gunicorn