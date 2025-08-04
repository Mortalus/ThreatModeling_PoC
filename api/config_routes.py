# api/config_routes.py

from flask import Blueprint, request, jsonify
import json
import os
from datetime import datetime
from utils.logging_utils import logger

config_bp = Blueprint('config', __name__)

@config_bp.route('/api/config/save', methods=['POST'])
def save_config_file():
    """Save configuration to a JSON file for persistence."""
    try:
        config_data = request.get_json()
        if not config_data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        # Add metadata
        config_data['saved_at'] = datetime.now().isoformat()
        config_data['version'] = config_data.get('version', '1.0')
        
        # Save to output directory
        output_dir = os.getenv('OUTPUT_DIR', './output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save main config file
        config_file = os.path.join(output_dir, 'runtime_config.json')
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Also save a timestamped backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(output_dir, f'config_backup_{timestamp}.json')
        with open(backup_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Clean up old backups (keep only last 10)
        backup_files = sorted([f for f in os.listdir(output_dir) if f.startswith('config_backup_')])
        if len(backup_files) > 10:
            for old_backup in backup_files[:-10]:
                try:
                    os.remove(os.path.join(output_dir, old_backup))
                except:
                    pass
        
        logger.info(f"Configuration saved to {config_file}")
        return jsonify({'success': True, 'file': config_file})
        
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return jsonify({'error': str(e)}), 500

@config_bp.route('/api/config/load', methods=['GET'])
def load_config_file():
    """Load configuration from saved file."""
    try:
        output_dir = os.getenv('OUTPUT_DIR', './output')
        config_file = os.path.join(output_dir, 'runtime_config.json')
        
        if not os.path.exists(config_file):
            return jsonify({'error': 'No saved configuration found'}), 404
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        return jsonify(config_data)
        
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return jsonify({'error': str(e)}), 500

@config_bp.route('/api/config/reset', methods=['POST'])
def reset_config():
    """Reset configuration to defaults."""
    try:
        output_dir = os.getenv('OUTPUT_DIR', './output')
        config_file = os.path.join(output_dir, 'runtime_config.json')
        
        # Backup current config before reset
        if os.path.exists(config_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(output_dir, f'config_before_reset_{timestamp}.json')
            with open(config_file, 'r') as f:
                current_config = json.load(f)
            with open(backup_file, 'w') as f:
                json.dump(current_config, f, indent=2)
        
        # Remove the main config file
        if os.path.exists(config_file):
            os.remove(config_file)
        
        logger.info("Configuration reset to defaults")
        return jsonify({'success': True, 'message': 'Configuration reset to defaults'})
        
    except Exception as e:
        logger.error(f"Error resetting configuration: {e}")
        return jsonify({'error': str(e)}), 500