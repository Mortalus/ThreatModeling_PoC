#!/usr/bin/env python3
"""
Enable enhanced progress display for existing scripts
Run this to patch the progress_utils module with enhanced features
"""

import os
import shutil
import sys

def enable_enhanced_progress():
    """Copy enhanced progress to utils directory"""
    
    # Check if we're in the right directory
    if not os.path.exists('utils/progress_utils.py'):
        print("❌ Error: Run this script from the project root directory")
        return False
    
    # Backup original
    if not os.path.exists('utils/progress_utils_original.py'):
        shutil.copy('utils/progress_utils.py', 'utils/progress_utils_original.py')
        print("✅ Backed up original progress_utils.py")
    
    # Check if enhanced version exists
    if not os.path.exists('utils/enhanced_progress.py'):
        print("❌ Error: enhanced_progress.py not found. Create it first.")
        return False
    
    # Create a wrapper that includes both old and new functionality
    wrapper_content = '''"""
Enhanced progress utilities with console display
This is a patched version that adds console progress bars
"""
import os
import sys
import json
import time
from datetime import datetime
from typing import Optional

# Import the enhanced progress system
try:
    from .enhanced_progress import (
        ProgressTracker, ProgressLogger, Colors,
        write_progress as enhanced_write_progress,
        check_kill_signal as enhanced_check_kill_signal,
        cleanup_progress_file as enhanced_cleanup_progress_file
    )
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False

# Global progress trackers for each step
_progress_trackers = {}

def write_progress(step: int, current: int, total: int, message: str, details: str = ""):
    """Write progress with enhanced console display if available"""
    if ENHANCED_AVAILABLE and os.getenv('SHOW_PROGRESS_CONSOLE', 'true').lower() == 'true':
        # Use or create a progress tracker for this step
        if step not in _progress_trackers:
            _progress_trackers[step] = ProgressTracker(step, total)
        
        tracker = _progress_trackers[step]
        tracker.total_steps = total  # Update total in case it changed
        tracker.update(current, message, details)
        
        # Clean up if complete
        if current >= total:
            del _progress_trackers[step]
    else:
        # Fallback to original implementation
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
            print(f"Warning: Could not write progress: {e}")

def check_kill_signal(step: int) -> bool:
    """Check if user requested to kill this step"""
    if ENHANCED_AVAILABLE:
        return enhanced_check_kill_signal(step)
    else:
        try:
            output_dir = os.getenv('OUTPUT_DIR', './output')
            kill_file = os.path.join(output_dir, f'step_{step}_kill.flag')
            
            if os.path.exists(kill_file):
                return True
            return False
        except:
            return False

def cleanup_progress_file(step: int):
    """Clean up progress file after successful completion"""
    if ENHANCED_AVAILABLE:
        enhanced_cleanup_progress_file(step)
    else:
        try:
            output_dir = os.getenv('OUTPUT_DIR', './output')
            progress_file = os.path.join(output_dir, f'step_{step}_progress.json')
            
            if os.path.exists(progress_file):
                os.remove(progress_file)
        except:
            pass

# Export enhanced features if available
if ENHANCED_AVAILABLE:
    __all__ = ['write_progress', 'check_kill_signal', 'cleanup_progress_file', 
               'ProgressTracker', 'ProgressLogger', 'Colors']
else:
    __all__ = ['write_progress', 'check_kill_signal', 'cleanup_progress_file']
'''
    
    # Write the wrapper
    with open('utils/progress_utils.py', 'w') as f:
        f.write(wrapper_content)
    
    print("✅ Enhanced progress system enabled!")
    print("\nUsage:")
    print("  - Progress bars will show in console by default")
    print("  - Disable with: export SHOW_PROGRESS_CONSOLE=false")
    print("  - Restore original: python enable_enhanced_progress.py --restore")
    
    return True

def restore_original():
    """Restore original progress_utils.py"""
    if os.path.exists('utils/progress_utils_original.py'):
        shutil.copy('utils/progress_utils_original.py', 'utils/progress_utils.py')
        print("✅ Restored original progress_utils.py")
        return True
    else:
        print("❌ Error: Original backup not found")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--restore':
        restore_original()
    else:
        enable_enhanced_progress()