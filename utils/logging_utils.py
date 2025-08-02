"""
Logging utilities for the threat modeling pipeline.
"""
import logging
import os
import sys

# Create logger
logger = logging.getLogger(__name__)

def setup_logging():
    """Set up logging configuration."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from some libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def log_startup_info(runtime_config):
    """Log startup information."""
    print("\n" + "="*60)
    print("THREAT MODELING PIPELINE")
    print("="*60)
    
    api_key = runtime_config.get('scw_secret_key')
    if api_key:
        print(f"✓ API Key loaded: ***{api_key[-4:]}")
    else:
        print("⚠️ WARNING: No API key found in environment!")
        print(" Please ensure your .env file contains SCW_SECRET_KEY=your_key_here")
    
    print(f"Working directory: {os.getcwd()}")
    print(f"Python: {sys.executable}")
    
    # Check for required scripts
    scripts = ['info_to_dfds.py', 'dfd_to_threats.py', 'improve_threat_quality.py', 'attack_path_analyzer.py']
    for script in scripts:
        if os.path.exists(script):
            print(f"✓ Found: {script}")
        else:
            print(f"✗ Missing: {script}")
    
    print("="*60)