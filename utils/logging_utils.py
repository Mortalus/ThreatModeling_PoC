import logging
import os
import sys

logger = logging.getLogger(__name__)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def log_startup_info(runtime_config):
    print("\n" + "="*60)
    print("THREAT MODELING PIPELINE BACKEND WITH REVIEW SYSTEM")
    print("="*60)
    api_key = runtime_config['scw_secret_key']
    if api_key:
        print(f"✓ API Key loaded: ***{api_key[-4:]}")
    else:
        print("⚠️ WARNING: No API key found in environment!")
        print(" Please ensure your .env file contains SCW_SECRET_KEY=your_key_here")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python: {sys.executable}")
    scripts = ['info_to_dfds.py', 'dfd_to_threats.py', 'improve_threat_quality.py', 'attack_path_analyzer.py']
    for script in scripts:
        if os.path.exists(script):
            print(f"✓ Found: {script}")
        else:
            print(f"✗ Missing: {script}")
    print("="*60)