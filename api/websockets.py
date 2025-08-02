from utils.logging_utils import logger

def register_websocket_handlers(socketio):
    @socketio.on('connect')
    def handle_connect():
        logger.info('Client connected')
        socketio.emit('connected', {'data': 'Connected to review system'})

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected')

    @socketio.on('request_progress')
    def handle_progress_request(data):
        """Handle real-time progress requests via WebSocket."""
        session_id = data.get('session_id', 'latest')
        try:
            with pipeline_state.lock:
                if session_id == 'latest':
                    session_id = pipeline_state.state.get('current_session')
                if session_id and session_id in pipeline_state.state.get('progress', {}):
                    socketio.emit('progress_update', {
                        'session_id': session_id,
                        'progress': pipeline_state.state['progress'][session_id]
                    })
                else:
                    socketio.emit('progress_update', {
                        'session_id': session_id,
                        'error': 'No progress data available'
                    })
        except Exception as e:
            logger.error(f"Progress WebSocket error: {e}")
            socketio.emit('progress_error', {'error': str(e)})