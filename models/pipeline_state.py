from datetime import datetime
import threading
import uuid
from collections import defaultdict
import os
import json

class PipelineState:
    def __init__(self):
        self.state = {
            'current_session': None,
            'logs': [],
            'step_outputs': {},
            'validations': {},
            'review_queue': defaultdict(list),
            'review_history': [],
            'quality_metrics': {},
            'progress': {}
        }
        self.lock = threading.Lock()

    def add_log(self, message, log_type='info'):
        """Add a log entry to the pipeline state."""
        with self.lock:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': log_type,
                'message': message
            }
            self.state['logs'].append(log_entry)
            if len(self.state['logs']) > 1000:
                self.state['logs'] = self.state['logs'][-1000:]

    def count_pending_reviews(self):
        """Count total pending reviews across all steps."""
        count = 0
        for step_items in self.state.get('review_queue', {}).values():
            count += len([item for item in step_items if item['status'] == 'pending'])
        return count

    def reset(self, save_session=False, clean_output=False, output_folder=None):
        """Reset the pipeline state."""
        with self.lock:
            if save_session and self.state['current_session']:
                session_backup = {
                    'session_id': self.state['current_session'],
                    'timestamp': datetime.now().isoformat(),
                    'step_outputs': self.state.get('step_outputs', {}),
                    'validations': self.state.get('validations', {}),
                    'review_history': self.state.get('review_history', [])
                }
                if output_folder:
                    backup_file = os.path.join(output_folder, f'session_backup_{self.state["current_session"]}.json')
                    with open(backup_file, 'w') as f:
                        json.dump(session_backup, f, indent=2)
                    self.add_log(f"Session backed up to {os.path.basename(backup_file)}", 'info')

            self.state = {
                'current_session': None,
                'logs': [],
                'step_outputs': {},
                'validations': {},
                'review_queue': defaultdict(list),
                'review_history': [],
                'quality_metrics': {},
                'progress': {}
            }

        if clean_output and output_folder:
            for file in os.listdir(output_folder):
                if file.endswith('.json') and not file.startswith('session_backup'):
                    try:
                        os.remove(os.path.join(output_folder, file))
                    except Exception:
                        pass

        self.add_log("Pipeline reset", 'info')