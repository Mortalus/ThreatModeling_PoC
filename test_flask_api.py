#!/usr/bin/env python3
"""Test the Flask API endpoints to verify they work correctly."""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def test_endpoint(method, endpoint, data=None, description=""):
    """Test a single endpoint."""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {method} {endpoint}")
    if description:
        print(f"Purpose: {description}")
    
    try:
        headers = {'Content-Type': 'application/json'} if data else {}
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            if data:
                response = requests.post(url, json=data, headers=headers)
            else:
                response = requests.post(url, headers=headers)
        
        print(f"Status: {response.status_code}")
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        print(f"Content-Type: {content_type}")
        
        # Try to parse response
        if 'application/json' in content_type:
            try:
                json_data = response.json()
                print(f"Response: {json.dumps(json_data, indent=2)}")
            except:
                print(f"Failed to parse JSON: {response.text[:200]}")
        else:
            print(f"Response (HTML): {response.text[:200]}...")
            
        return response.status_code
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to Flask backend at http://localhost:5000")
        print("Make sure the Flask server is running!")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    """Run all API tests."""
    print("Flask API Endpoint Test")
    print("=" * 60)
    
    # Test health endpoint
    test_endpoint("GET", "/api/health", description="Health check")
    
    # Test the main endpoint
    test_endpoint("GET", "/api/test", description="Test endpoint")
    
    # Test config endpoint
    test_endpoint("GET", "/api/config", description="Get configuration")
    
    # Test run-step with proper JSON body
    print("\n" + "="*60)
    print("Testing pipeline step execution...")
    
    # Test with proper JSON body
    step_data = {
        "step": 2,
        "input": {}
    }
    test_endpoint("POST", "/api/run-step", data=step_data, 
                 description="Run pipeline step 2 (DFD Extraction)")
    
    # Test progress endpoint
    test_endpoint("GET", "/api/progress/latest", description="Get latest progress")
    
    print("\n" + "="*60)
    print("\nSummary:")
    print("- If you see 'Cannot connect', start your Flask backend: python app.py")
    print("- If you see 405 errors, check that you're using the correct HTTP method")
    print("- If you see 400 errors, check that you're sending proper JSON data")
    print("- The /api/run-step endpoint expects POST with JSON body: {\"step\": 2, \"input\": {}}")

if __name__ == "__main__":
    main()
