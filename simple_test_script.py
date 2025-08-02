#!/usr/bin/env python3
"""
Simple test to run info_to_dfds.py with the copied file
"""

import os
import subprocess
import sys
import json
from dotenv import load_dotenv

def test_dfd_extraction():
    print("🧪 TESTING DFD EXTRACTION")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    
    # Check that the file was copied
    input_files = [f for f in os.listdir('./input_documents') if f.endswith('_extracted.txt')]
    if input_files:
        print(f"✓ Found input file: {input_files[0]}")
        
        # Show file content preview
        with open(f'./input_documents/{input_files[0]}', 'r') as f:
            content = f.read()
        print(f"✓ File size: {len(content)} characters")
        print(f"✓ Preview: {content[:100]}...")
    else:
        print("✗ No input files found in ./input_documents/")
        return False
    
    print()
    
    # Set up environment
    env = os.environ.copy()
    env.update({
        'INPUT_DIR': './input_documents',
        'OUTPUT_DIR': './output',
        'DFD_OUTPUT_PATH': './output/dfd_components.json',
        'LOG_LEVEL': 'DEBUG'
    })
    
    # Remove old output
    output_file = './output/dfd_components.json'
    if os.path.exists(output_file):
        os.remove(output_file)
        print("🗑️  Removed old output file")
    
    print("🚀 Running info_to_dfds.py...")
    print("-" * 30)
    
    try:
        result = subprocess.run(
            [sys.executable, 'info_to_dfds.py'],
            env=env,
            capture_output=True,
            text=True,
            timeout=180  # 3 minutes
        )
        
        print(f"Return code: {result.returncode}")
        
        if result.stdout.strip():
            print("\nSTDOUT:")
            print(result.stdout)
        
        if result.stderr.strip():
            print("\nSTDERR:")
            print(result.stderr)
        
        # Check if output was created
        if os.path.exists(output_file):
            print("\n✅ SUCCESS! Output file created!")
            
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            print(f"📊 File size: {os.path.getsize(output_file)} bytes")
            
            if 'dfd' in data:
                dfd = data['dfd']
                print(f"📋 DFD Components:")
                print(f"   - External Entities: {len(dfd.get('external_entities', []))}")
                print(f"   - Processes: {len(dfd.get('processes', []))}")
                print(f"   - Assets: {len(dfd.get('assets', []))}")
                print(f"   - Data Flows: {len(dfd.get('data_flows', []))}")
                
                # Show some example content
                if dfd.get('external_entities'):
                    print(f"\n📝 Example External Entity: {dfd['external_entities'][0]}")
                if dfd.get('processes'):
                    print(f"📝 Example Process: {dfd['processes'][0]}")
            
            print("\n🎉 DFD extraction is working!")
            print("✅ Now try your frontend again")
            return True
            
        else:
            print("\n❌ No output file created")
            print("\n🔍 Possible issues:")
            print("1. LLM API call failed (check API key/network)")
            print("2. Script couldn't process the input file")
            print("3. Internal script error")
            
            # Check what files exist in output
            output_files = os.listdir('./output')
            print(f"\n📁 Files in ./output: {output_files}")
            
            return False
            
    except subprocess.TimeoutExpired:
        print("\n⏰ Script timed out after 3 minutes")
        return False
    except Exception as e:
        print(f"\n❌ Error running script: {e}")
        return False

if __name__ == "__main__":
    test_dfd_extraction()