#!/usr/bin/env python3
"""
Minimal test to verify basic pipeline functionality
This bypasses Flask and tests the core components directly
"""

import os
import json
import sys
from pathlib import Path

print("MINIMAL PIPELINE TEST")
print("=" * 50)

# Step 1: Create a simple test document
test_dir = Path("./test_run")
test_dir.mkdir(exist_ok=True)

input_dir = test_dir / "input_documents"
output_dir = test_dir / "output"
input_dir.mkdir(exist_ok=True)
output_dir.mkdir(exist_ok=True)

# Create test content
test_content = """System: Test Web Application
External Entities: User, Admin
Assets: Database, File Storage
Processes: Web Server, API Server
Data Flows:
- From User to Web Server: Login data, Confidential, HTTPS, Password Auth
- From Web Server to Database: User queries, PII, TLS, Service Account
"""

test_file = input_dir / "test.txt"
with open(test_file, 'w') as f:
    f.write(test_content)

print(f"✓ Created test file: {test_file}")

# Step 2: Set up environment
env = os.environ.copy()
env.update({
    'INPUT_DIR': str(input_dir),
    'OUTPUT_DIR': str(output_dir),
    'DFD_OUTPUT_PATH': str(output_dir / 'dfd.json'),
    'LLM_PROVIDER': 'scaleway',
    'LOG_LEVEL': 'INFO'
})

# Load .env file if it exists
if os.path.exists('.env'):
    print("✓ Found .env file")
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                env[key] = value
                if key == 'SCW_API_KEY':
                    print(f"✓ Loaded API key: ***{value[-4:]}")

# Step 3: Run info_to_dfds.py
print("\nRunning info_to_dfds.py...")
print("-" * 50)

import subprocess

result = subprocess.run(
    [sys.executable, 'info_to_dfds.py'],
    env=env,
    capture_output=True,
    text=True
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print("-" * 50)

if result.returncode == 0:
    print("✓ Script completed successfully")
    
    # Check output
    dfd_file = output_dir / 'dfd.json'
    if dfd_file.exists():
        with open(dfd_file, 'r') as f:
            data = json.load(f)
        print(f"✓ DFD created with {len(data.get('dfd', {}).get('processes', []))} processes")
        print("\nDFD Content Preview:")
        print(json.dumps(data.get('dfd', {}), indent=2)[:500] + "...")
    else:
        print("✗ No output file created")
else:
    print(f"✗ Script failed with code: {result.returncode}")

print("\nTest complete!")
print("\nIf this worked, the issue is with the Flask integration.")
print("If this failed, check the error messages above.")