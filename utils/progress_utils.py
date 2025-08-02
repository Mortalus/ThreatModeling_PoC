"""
Progress tracking utilities for the threat modeling pipeline.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

def write_progress(step: int, current: int, total: int, message: str, details: str = ""):
    """Write progress information to a file that the frontend can read."""
    try:
        progress_data = {
            'step': step,
            'current': current,
            'total': total,
            'progress': round((current / total * 100) if total > 0 else 0, 1),
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        output_dir = os.getenv('OUTPUT_DIR', './output')
        progress_file = os.path.join(output_dir, f'step_{step}_progress.json')
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
            
    except Exception as e:
        logger.warning(f"Could not write progress: {e}")

def check_kill_signal(step: int) -> bool:
    """Check if user requested to kill this step."""
    try:
        output_dir = os.getenv('OUTPUT_DIR', './output')
        kill_file = os.path.join(output_dir, f'step_{step}_kill.flag')
        
        if os.path.exists(kill_file):
            logger.info("Kill signal detected, stopping execution")
            return True
        return False
    except:
        return False

def cleanup_progress_file(step: int):
    """Clean up progress file after successful completion."""
    try:
        output_dir = os.getenv('OUTPUT_DIR', './output')
        progress_file = os.path.join(output_dir, f'step_{step}_progress.json')
        
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except:
        pass