#!/usr/bin/env python3
"""
Diagnostic script to trace exactly what happens when Flask calls DFD extraction
This will help us see the disconnect between our test and the actual Flask execution
"""

import os
import sys
import json
from datetime import datetime

# Add this to the TOP of your info_to_dfds.py file to debug what's happening

def debug_flask_execution():
    """Debug function to log execution details."""
    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'environment_variables': {},
        'directories': {},
        'files_found': {},
        'execution_path': []
    }
    
    # Log all environment variables
    env_vars_to_check = [
        'SESSION_ID', 'INPUT_DIR', 'OUTPUT_DIR', 'LLM_PROVIDER', 'LLM_MODEL',
        'SCW_API_URL', 'LOG_LEVEL', 'TEMPERATURE', 'MAX_TOKENS'
    ]
    
    for var in env_vars_to_check:
        debug_info['environment_variables'][var] = os.getenv(var, 'NOT_SET')
    
    # Check directories
    dirs_to_check = {
        'input_documents': './input_documents',
        'output': './output',
        'uploads': './uploads'
    }
    
    for name, path in dirs_to_check.items():
        debug_info['directories'][name] = {
            'exists': os.path.exists(path),
            'path': path,
            'txt_files': []
        }
        
        if os.path.exists(path):
            txt_files = [f for f in os.listdir(path) if f.endswith('.txt')]
            debug_info['directories'][name]['txt_files'] = txt_files
    
    # Log current working directory
    debug_info['cwd'] = os.getcwd()
    debug_info['script_path'] = os.path.abspath(__file__)
    debug_info['python_path'] = sys.path
    
    # Write debug info to file
    debug_file = './output/flask_execution_debug.json'
    os.makedirs('./output', exist_ok=True)
    
    with open(debug_file, 'w') as f:
        json.dump(debug_info, f, indent=2)
    
    print(f"🔍 DEBUG: Execution details saved to {debug_file}")
    print(f"🔍 DEBUG: SESSION_ID = {os.getenv('SESSION_ID', 'NOT_SET')}")
    print(f"🔍 DEBUG: INPUT_DIR = {os.getenv('INPUT_DIR', 'NOT_SET')}")
    print(f"🔍 DEBUG: Current working directory = {os.getcwd()}")
    
    return debug_info

if __name__ == "__main__":
    debug_flask_execution()
