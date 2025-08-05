#!/usr/bin/env python3
"""Test script to check if the Flask backend is running correctly."""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def test_endpoint(method, endpoint, data=None):
    """Test a single endpoint."""
    url = f"{BASE_URL}{endpoint}"
    print(f"\nTesting {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=data or {}, headers=headers)
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        # Try to parse as JSON
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        except:
            print(f"Response (text): {response.text[:200]}...")
            
        return response.status_code
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to backend. Is it running?")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    """Run all tests."""
    print("Testing Flask Backend API Endpoints")
    print("=" * 40)
    
    # Test health endpoint
    test_endpoint("GET", "/api/health")
    
    # Test config endpoint
    test_endpoint("GET", "/api/config")
    
    # Test pipeline status
    test_endpoint("GET", "/api/pipeline-status")
    
    # Test run-step endpoints
    for step in range(2, 6):
        # Try both GET and POST
        get_status = test_endpoint("GET", f"/api/run-step/{step}")
        if get_status == 405:  # Method not allowed
            test_endpoint("POST", f"/api/run-step/{step}")

if __name__ == "__main__":
    main()
