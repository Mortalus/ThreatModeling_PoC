#!/usr/bin/env python3
"""
Debug wrapper to run info_to_dfds.py with proper environment
"""
import os
import subprocess
import sys

def run_with_debug():
    """Run info_to_dfds.py with debugging"""
    
    # Set up environment like pipeline_service does
    env = os.environ.copy()
    
    # Add the required environment variables
    env.update({
        'INPUT_DIR': './input_documents',
        'OUTPUT_DIR': './output',
        'LOG_LEVEL': 'INFO',
        'LLM_PROVIDER': 'scaleway',
        'LLM_MODEL': 'llama-3.3-70b-instruct',
        'TEMPERATURE': '0.2',
        'MAX_TOKENS': '4096',
    })
    
    # Get API key from environment or config
    api_key = os.getenv('SCW_API_KEY') or os.getenv('SCW_SECRET_KEY')
    if api_key:
        env['SCW_API_KEY'] = api_key
        env['SCW_SECRET_KEY'] = api_key
        print(f"✅ API Key set: ***{api_key[-4:]}")
    else:
        print("❌ No API key found!")
    
    print("\nEnvironment variables:")
    for key in ['SCW_API_KEY', 'SCW_SECRET_KEY', 'LLM_PROVIDER', 'INPUT_DIR', 'OUTPUT_DIR']:
        value = env.get(key, 'NOT SET')
        if key in ['SCW_API_KEY', 'SCW_SECRET_KEY'] and value != 'NOT SET':
            print(f"  {key}: ***{value[-4:]}")
        else:
            print(f"  {key}: {value}")
    
    print(f"\nRunning: {sys.executable} info_to_dfds.py")
    print("-" * 60)
    
    # Run the script
    result = subprocess.run(
        [sys.executable, 'info_to_dfds.py'],
        env=env,
        text=True
    )
    
    print("-" * 60)
    print(f"\nReturn code: {result.returncode}")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_with_debug())