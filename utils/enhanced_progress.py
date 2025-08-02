#!/usr/bin/env python3
"""
Enhanced progress utilities with console display
"""
import os
import sys
import json
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any

# ANSI color codes for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ProgressTracker:
    """Enhanced progress tracker with console display"""
    
    def __init__(self, step: int, total_steps: int = 100):
        self.step = step
        self.total_steps = total_steps
        self.current = 0
        self.message = ""
        self.details = ""
        self.start_time = time.time()
        self.output_dir = os.getenv('OUTPUT_DIR', './output')
        
        # Console display settings
        self.show_console = os.getenv('SHOW_PROGRESS_CONSOLE', 'true').lower() == 'true'
        self.last_console_update = 0
        self.console_update_interval = 0.5  # seconds
        
    def update(self, current: int, message: str, details: str = ""):
        """Update progress with console display"""
        self.current = current
        self.message = message
        self.details = details
        
        # Write to file for web UI
        self._write_progress_file()
        
        # Update console if enabled
        if self.show_console:
            self._update_console()
    
    def _write_progress_file(self):
        """Write progress to JSON file"""
        try:
            progress_data = {
                'step': self.step,
                'current': self.current,
                'total': self.total_steps,
                'progress': round((self.current / self.total_steps * 100) if self.total_steps > 0 else 0, 1),
                'message': self.message,
                'details': self.details,
                'timestamp': datetime.now().isoformat(),
                'elapsed_seconds': round(time.time() - self.start_time, 1)
            }
            
            progress_file = os.path.join(self.output_dir, f'step_{self.step}_progress.json')
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not write progress file: {e}")
    
    def _update_console(self):
        """Update console display with progress bar"""
        current_time = time.time()
        
        # Throttle console updates
        if current_time - self.last_console_update < self.console_update_interval:
            return
            
        self.last_console_update = current_time
        
        # Calculate progress
        progress = (self.current / self.total_steps * 100) if self.total_steps > 0 else 0
        elapsed = current_time - self.start_time
        
        # Create progress bar
        bar_length = 40
        filled_length = int(bar_length * self.current // self.total_steps)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Color based on progress
        if progress < 33:
            color = Colors.FAIL
        elif progress < 66:
            color = Colors.WARNING
        else:
            color = Colors.GREEN
        
        # Build status line
        status_line = f"\r{color}Step {self.step} │ {bar} │ {progress:>5.1f}% │ {self.message:<30}"
        
        if self.details:
            status_line += f" │ {self.details:<20}"
        
        status_line += f" │ {elapsed:>5.1f}s{Colors.ENDC}"
        
        # Write to stdout
        sys.stdout.write(status_line)
        sys.stdout.flush()
        
        # Add newline when complete
        if self.current >= self.total_steps:
            print()  # New line after completion
    
    def complete(self, message: str = "Complete"):
        """Mark step as complete"""
        self.update(self.total_steps, message, "")
        
        # Clean up progress file
        try:
            progress_file = os.path.join(self.output_dir, f'step_{self.step}_progress.json')
            if os.path.exists(progress_file):
                os.remove(progress_file)
        except:
            pass
    
    def fail(self, error_message: str):
        """Mark step as failed"""
        self.update(self.total_steps, "Failed", error_message)
        if self.show_console:
            print(f"\n{Colors.FAIL}✗ Step {self.step} failed: {error_message}{Colors.ENDC}")


# Enhanced logging that works with progress display
class ProgressLogger:
    """Logger that clears progress line before logging"""
    
    def __init__(self, name: str):
        self.name = name
        
    def _log(self, level: str, message: str, color: str = ""):
        """Log with proper formatting"""
        # Clear current line
        sys.stdout.write('\r' + ' ' * 100 + '\r')
        sys.stdout.flush()
        
        # Print log message
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {level:>8} │ {self.name} │ {message}{Colors.ENDC}")
        
    def info(self, message: str):
        self._log("INFO", message, Colors.CYAN)
        
    def warning(self, message: str):
        self._log("WARNING", message, Colors.WARNING)
        
    def error(self, message: str):
        self._log("ERROR", message, Colors.FAIL)
        
    def success(self, message: str):
        self._log("SUCCESS", message, Colors.GREEN)


# Backward compatible functions
def write_progress(step: int, current: int, total: int, message: str, details: str = ""):
    """Legacy function - now uses ProgressTracker"""
    tracker = ProgressTracker(step, total)
    tracker.update(current, message, details)

def check_kill_signal(step: int) -> bool:
    """Check if user requested to kill this step"""
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
    try:
        output_dir = os.getenv('OUTPUT_DIR', './output')
        progress_file = os.path.join(output_dir, f'step_{step}_progress.json')
        
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except:
        pass


# Progress monitoring thread for web UI
class ProgressMonitor(threading.Thread):
    """Monitor progress files and emit websocket updates"""
    
    def __init__(self, socketio, output_dir: str = './output'):
        super().__init__(daemon=True)
        self.socketio = socketio
        self.output_dir = output_dir
        self.running = True
        self.last_progress = {}
        
    def run(self):
        """Monitor progress files"""
        while self.running:
            try:
                for step in range(1, 6):
                    progress_file = os.path.join(self.output_dir, f'step_{step}_progress.json')
                    
                    if os.path.exists(progress_file):
                        with open(progress_file, 'r') as f:
                            progress_data = json.load(f)
                        
                        # Check if progress changed
                        step_key = f"step_{step}"
                        if self.last_progress.get(step_key) != progress_data:
                            self.last_progress[step_key] = progress_data
                            
                            # Emit websocket update
                            self.socketio.emit('progress_update', {
                                'step': step,
                                'progress': progress_data
                            })
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                print(f"Progress monitor error: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop monitoring"""
        self.running = False


# Example usage in scripts
if __name__ == "__main__":
    # Demo the enhanced progress system
    print(f"\n{Colors.HEADER}=== Enhanced Progress System Demo ==={Colors.ENDC}\n")
    
    # Simulate a step with progress
    logger = ProgressLogger("demo")
    logger.info("Starting demo process")
    
    tracker = ProgressTracker(step=1, total_steps=100)
    
    # Simulate work
    tasks = [
        (10, "Initializing", "Loading configuration"),
        (25, "Processing", "Analyzing documents"),
        (50, "Extracting", "Finding components"),
        (75, "Building", "Creating DFD"),
        (90, "Validating", "Checking results"),
        (100, "Complete", "DFD generated successfully")
    ]
    
    for progress, message, details in tasks:
        tracker.update(progress, message, details)
        time.sleep(0.5)  # Simulate work
        
        # Log some messages
        if progress == 50:
            logger.warning("Large document detected")
        elif progress == 90:
            logger.success("Validation passed")
    
    tracker.complete()
    logger.success("Demo completed successfully!")
    
    print(f"\n{Colors.HEADER}Progress files are saved in: {tracker.output_dir}{Colors.ENDC}")