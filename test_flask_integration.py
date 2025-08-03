#!/usr/bin/env python3
"""
Test script to verify Flask pipeline integration
This will simulate what happens when Flask calls the DFD extraction
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_flask_pipeline_integration():
    """Test the complete Flask pipeline flow."""
    print("🔗 FLASK PIPELINE INTEGRATION TEST")
    print("=" * 60)
    
    # Step 1: Check current state
    print("📊 Current State:")
    
    # Check for uploaded files
    output_dir = './output'
    input_dir = './input_documents'
    
    output_files = []
    input_files = []
    
    if os.path.exists(output_dir):
        output_files = [f for f in os.listdir(output_dir) if f.endswith('_extracted.txt')]
    
    if os.path.exists(input_dir):
        input_files = [f for f in os.listdir(input_dir) if f.endswith('_extracted.txt')]
    
    print(f"   Output extracted files: {output_files}")
    print(f"   Input extracted files: {input_files}")
    
    # Get the most recent file (simulate current session)
    all_files = [(f, os.path.join(output_dir, f)) for f in output_files] + \
                [(f, os.path.join(input_dir, f)) for f in input_files]
    
    if not all_files:
        print("   ❌ No extracted files found!")
        print("   🔧 Upload a document first through the web interface")
        return 1
    
    # Find most recent file
    most_recent = max(all_files, key=lambda x: os.path.getmtime(x[1]))
    recent_file, recent_path = most_recent
    
    print(f"   📄 Most recent file: {recent_file}")
    print(f"   📍 Location: {recent_path}")
    
    # Extract session ID from filename (YYYYMMDD_HHMMSS format)
    if '_extracted.txt' in recent_file:
        session_id = recent_file.replace('_extracted.txt', '')
        print(f"   🎯 Extracted session ID: {session_id}")
    else:
        print("   ❌ Could not extract session ID from filename")
        return 1
    
    # Step 2: Simulate Flask environment
    print(f"\n🌍 Simulating Flask Environment:")
    
    # Set up environment variables like Flask would
    flask_env = os.environ.copy()
    flask_env.update({
        'SESSION_ID': session_id,
        'INPUT_DIR': input_dir,
        'OUTPUT_DIR': output_dir,
        'LLM_PROVIDER': 'scaleway',
        'LLM_MODEL': 'llama-3.3-70b-instruct',
        'SCW_API_URL': 'https://api.scaleway.ai/v1',
        'LOG_LEVEL': 'INFO',
        'TEMPERATURE': '0.2',
        'MAX_TOKENS': '4096'
    })
    
    print(f"   ✅ SESSION_ID: {flask_env['SESSION_ID']}")
    print(f"   ✅ INPUT_DIR: {flask_env['INPUT_DIR']}")
    print(f"   ✅ OUTPUT_DIR: {flask_env['OUTPUT_DIR']}")
    
    # Step 3: Test our test script with Flask environment
    print(f"\n🧪 Testing with Flask-like environment:")
    
    try:
        result = subprocess.run(
            [sys.executable, 'test_session_env.py'],
            env=flask_env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("Test script output:")
        print(result.stdout)
        
        if result.stderr:
            print("Test script stderr:")
            print(result.stderr)
            
        if result.returncode == 0:
            print("   ✅ Environment test passed!")
        else:
            print("   ❌ Environment test failed!")
            
    except Exception as e:
        print(f"   ❌ Failed to run test script: {e}")
        return 1
    
    # Step 4: Test DFD extraction with Flask environment
    print(f"\n🚀 Testing DFD extraction with Flask environment:")
    
    try:
        result = subprocess.run(
            [sys.executable, 'debug_dfd_script.py'],
            env=flask_env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("DFD debug output:")
        print(result.stdout)
        
        if "Session ID: None" in result.stdout:
            print("   ❌ Session ID still not being read correctly")
        elif f"Session ID: {session_id}" in result.stdout:
            print("   ✅ Session ID being passed correctly!")
        else:
            print("   ⚠️  Unclear session ID status")
            
    except Exception as e:
        print(f"   ❌ Failed to run DFD debug: {e}")
        return 1
    
    # Step 5: Test actual DFD extraction
    print(f"\n🎯 Testing actual DFD extraction:")
    
    try:
        result = subprocess.run(
            [sys.executable, 'info_to_dfds.py'],
            env=flask_env,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            # Show last 20 lines of output
            lines = result.stdout.split('\n')
            print("Last 20 lines of output:")
            for line in lines[-20:]:
                if line.strip():
                    print(f"   {line}")
        
        if result.stderr:
            print("Error output:")
            print(result.stderr)
        
        # Check if output was created
        dfd_output = os.path.join(output_dir, 'dfd_components.json')
        if os.path.exists(dfd_output):
            print("   ✅ DFD output file created!")
            
            # Check file size
            size = os.path.getsize(dfd_output)
            print(f"   📊 File size: {size} bytes")
            
            # Quick check of content
            try:
                with open(dfd_output, 'r') as f:
                    data = json.load(f)
                if 'dfd' in data:
                    dfd = data['dfd']
                    print(f"   📋 DFD components:")
                    print(f"      External entities: {len(dfd.get('external_entities', []))}")
                    print(f"      Processes: {len(dfd.get('processes', []))}")
                    print(f"      Assets: {len(dfd.get('assets', []))}")
                    
                    # Check if it's sample data or real data
                    if any('sample' in str(component).lower() for component in dfd.get('external_entities', [])):
                        print("   ⚠️  Contains sample data - may not be processing uploaded file")
                    else:
                        print("   ✅ Appears to contain real extracted data!")
                        
            except Exception as e:
                print(f"   ⚠️  Could not analyze DFD content: {e}")
        else:
            print("   ❌ DFD output file not created")
            
    except Exception as e:
        print(f"   ❌ Failed to run DFD extraction: {e}")
        return 1
    
    print(f"\n📋 Summary:")
    print(f"   Session ID: {session_id}")
    print(f"   Environment setup: ✅")
    print(f"   Ready for Flask integration testing")
    
    return 0

if __name__ == "__main__":
    sys.exit(test_flask_pipeline_integration())
