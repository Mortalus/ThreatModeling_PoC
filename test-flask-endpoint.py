#!/usr/bin/env python3
"""
Test the Flask endpoint directly to see what's happening
"""

import requests
import json
import time

print("TESTING FLASK ENDPOINTS")
print("="*60)

# Check if Flask is running
try:
    response = requests.get('http://localhost:5000/api/health')
    print("✓ Flask is running")
    health = response.json()
    print(f"  Has API key: {health.get('has_api_key', False)}")
except:
    print("✗ Flask is not running on port 5000")
    print("  Please start the Flask app first: python app.py")
    exit(1)

# Test 1: Upload a text file
print("\n1. Testing file upload...")
test_content = """System: E-Commerce Platform
External Entities: User (U), Payment Gateway (PG)
Assets: Customer Database (DB_C), Product Database (DB_P)
Processes: Web Server (WS), API Gateway (API), Payment Processor (PP)
Trust Boundaries: Internet to DMZ, DMZ to Internal
Data Flows:
- From User to Web Server: Login credentials, Confidential, HTTPS, JWT
- From Web Server to Customer Database: Customer data, PII, TLS, Service Account
- From Payment Processor to Payment Gateway: Payment info, PCI, HTTPS, API Key
"""

# Create a test file
with open('test_upload.txt', 'w') as f:
    f.write(test_content)

# Upload it
with open('test_upload.txt', 'rb') as f:
    files = {'document': ('test_system.txt', f, 'text/plain')}
    response = requests.post('http://localhost:5000/api/upload', files=files)

if response.status_code == 200:
    upload_result = response.json()
    print("✓ File uploaded successfully")
    print(f"  Session ID: {upload_result.get('session_id')}")
    print(f"  Text length: {upload_result.get('text_length')} characters")
    print(f"  Text saved to: {upload_result.get('text_file_path')}")
else:
    print(f"✗ Upload failed: {response.status_code}")
    print(f"  Error: {response.text}")
    exit(1)

# Test 2: Run step 2 (DFD extraction)
print("\n2. Testing DFD extraction (Step 2)...")
print("  This calls info_to_dfds.py")
print("  Sending request...")

start_time = time.time()
response = requests.post(
    'http://localhost:5000/api/run-step',
    json={
        'step': 2,
        'input': upload_result
    }
)
elapsed = time.time() - start_time

print(f"  Response received in {elapsed:.1f} seconds")
print(f"  Status code: {response.status_code}")

if response.status_code == 200:
    dfd_result = response.json()
    print("✓ DFD extraction successful")
    if 'dfd' in dfd_result:
        dfd = dfd_result['dfd']
        print(f"  Project: {dfd.get('project_name', 'Unknown')}")
        print(f"  Components: {dfd_result.get('count', 0)}")
        print(f"  Processes: {len(dfd.get('processes', []))}")
        print(f"  Assets: {len(dfd.get('assets', []))}")
else:
    print("✗ DFD extraction failed")
    error_data = response.json()
    print(f"  Error: {error_data.get('error', 'Unknown error')}")
    if 'stdout' in error_data:
        print(f"  Script output: {error_data['stdout'][:500]}")
    if 'stderr' in error_data:
        print(f"  Script errors: {error_data['stderr'][:500]}")

# Check logs
print("\n3. Checking Flask logs...")
response = requests.get('http://localhost:5000/api/logs')
if response.status_code == 200:
    logs = response.json().get('logs', [])
    print(f"  Found {len(logs)} log entries")
    for log in logs[-5:]:  # Last 5 logs
        print(f"  [{log['type']}] {log['message']}")

# Cleanup
import os
if os.path.exists('test_upload.txt'):
    os.remove('test_upload.txt')

print("\n" + "="*60)
print("TEST COMPLETE")
print("Check the Flask console for additional output")