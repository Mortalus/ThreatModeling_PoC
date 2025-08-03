#!/usr/bin/env python3
"""
Test Step 2 (DFD Extraction) directly via API call
This bypasses any UI issues
"""

import requests
import json
from datetime import datetime

def test_step2_directly():
    """Test Step 2 via direct API call."""
    
    print("🎯 TESTING STEP 2 DIRECTLY")
    print("=" * 60)
    
    # API endpoint
    url = "http://localhost:5000/api/run-step"
    
    # Step 2 payload
    payload = {
        "step": 2,  # This should trigger DFD extraction
        "input": {}
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"📡 Making API call to: {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        
        print(f"\n📊 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("   ✅ API call successful")
            
            try:
                response_data = response.json()
                print(f"   📄 Response Data: {json.dumps(response_data, indent=2)[:500]}...")
                
                # Check if it's actually DFD data
                if 'dfd' in response_data:
                    dfd = response_data['dfd']
                    print(f"\n🎉 DFD EXTRACTION SUCCESSFUL!")
                    print(f"   External entities: {len(dfd.get('external_entities', []))}")
                    print(f"   Processes: {len(dfd.get('processes', []))}")
                    print(f"   Assets: {len(dfd.get('assets', []))}")
                    print(f"   Data flows: {len(dfd.get('data_flows', []))}")
                    
                    # Check if it's sample data
                    all_entities = str(dfd.get('external_entities', []))
                    if 'sample' in all_entities.lower() or 'example' in all_entities.lower():
                        print("   ⚠️  WARNING: Contains sample/example data")
                    else:
                        print("   ✅ Appears to contain real extracted data")
                        
                else:
                    print("   ❌ No DFD data in response")
                    
            except json.JSONDecodeError:
                print(f"   📄 Raw Response: {response.text[:500]}...")
                
        else:
            print(f"   ❌ API call failed")
            print(f"   Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print("   ⏰ Request timed out - DFD extraction is probably running")
        print("   Check Flask console for debug output")
        
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection error - is Flask running on localhost:5000?")
        
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    
    print("\n📋 Check Flask console for debug output from info_to_dfds.py")

if __name__ == "__main__":
    test_step2_directly()
