#!/usr/bin/env python3
"""
Test to ensure folders are set up correctly for the pipeline
"""

import os
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()

print("FOLDER SETUP TEST")
print("="*60)

# Create all necessary folders
folders = {
    './uploads': 'Where Flask saves uploaded files',
    './input_documents': 'Where info_to_dfds.py looks for input',
    './output': 'Where all scripts save their output'
}

for folder, description in folders.items():
    os.makedirs(folder, exist_ok=True)
    print(f"✓ Created {folder}: {description}")

# Create a test file in the correct location
test_content = """System: Test Application
External Entities: User, Admin
Assets: Database, File Storage
Processes: Web Server, API Server
Data Flows:
- From User to Web Server: Login data, Confidential, HTTPS, Password Auth
- From Web Server to Database: User queries, PII, TLS, Service Account
"""

# Save to input_documents (where info_to_dfds.py expects it)
test_file = './input_documents/test.txt'
with open(test_file, 'w') as f:
    f.write(test_content)
print(f"\n✓ Created test file: {test_file}")

# Test 1: Run info_to_dfds.py directly
print("\n" + "-"*60)
print("TEST 1: Run info_to_dfds.py directly")
print("-"*60)

# The script should find the file automatically
env = os.environ.copy()
# Don't override INPUT_DIR - let the script use its default

result = subprocess.run(
    [sys.executable, 'info_to_dfds.py'],
    capture_output=True,
    text=True,
    env=env
)

print(f"Return code: {result.returncode}")
if result.returncode == 0:
    print("✓ Script ran successfully")
    # Check if output was created
    if os.path.exists('./output/dfd_components.json'):
        print("✓ Output file created")
else:
    print("✗ Script failed")
    print(f"STDERR: {result.stderr[:500]}")

# Test 2: Run with explicit INPUT_DIR
print("\n" + "-"*60)
print("TEST 2: Run with explicit INPUT_DIR")
print("-"*60)

env['INPUT_DIR'] = './input_documents'
env['OUTPUT_DIR'] = './output'

result = subprocess.run(
    [sys.executable, 'info_to_dfds.py'],
    capture_output=True,
    text=True,
    env=env
)

print(f"Return code: {result.returncode}")
print(f"INPUT_DIR was set to: {env['INPUT_DIR']}")

# Check what info_to_dfds.py is actually using
print("\n" + "-"*60)
print("CHECKING info_to_dfds.py DEFAULT SETTINGS")
print("-"*60)

# Look for the INPUT_DIR default in the script
with open('info_to_dfds.py', 'r') as f:
    content = f.read()
    
# Find INPUT_DIR usage
import re
input_dir_matches = re.findall(r'INPUT_DIR.*?=.*?getenv.*?"(.*?)"', content)
if input_dir_matches:
    print(f"info_to_dfds.py default INPUT_DIR: {input_dir_matches[0]}")

# Summary
print("\n" + "="*60)
print("SOLUTION:")
print("="*60)
print("\nThe Flask app should save extracted text to: ./input_documents/")
print("NOT to: ./uploads/")
print("\nOr, it should set INPUT_DIR environment variable to point to ./uploads/")
print("\nRecommended fix in Flask app.py:")
print("  1. Save extracted text to INPUT_FOLDER (./input_documents/)")
print("  2. OR set env['INPUT_DIR'] = UPLOAD_FOLDER when calling the script")