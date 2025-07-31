#!/usr/bin/env python3
"""
Check Scaleway API authentication and configuration
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("SCALEWAY API CONFIGURATION CHECK")
print("=" * 60)

# Check API Key
api_key = os.getenv('SCW_API_KEY') or os.getenv('SCALEWAY_API_KEY') or os.getenv('SCW_SECRET_KEY')
if api_key:
    print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    print(f"  Length: {len(api_key)} characters")
else:
    print("✗ No API key found!")
    print("\nPlease add to your .env file:")
    print("SCW_API_KEY=your_api_key_here")

# Check Project ID
project_id = os.getenv('SCALEWAY_PROJECT_ID') or os.getenv('SCW_PROJECT_ID')
if project_id:
    print(f"\n✓ Project ID found: {project_id}")
else:
    print("\n⚠️  No project ID in .env file")
    print("  Using default: 4a8fd76b-8606-46e6-afe6-617ce8eeb948")

# Test connection with correct format
print("\n" + "=" * 60)
print("TESTING API CONNECTION")
print("=" * 60)

if api_key:
    import requests
    
    # Try the correct Scaleway API endpoint format
    # The URL should be: https://api.scaleway.ai/v1/inference/deployments/{deployment-id}/chat/completions
    
    print("\nTrying different API configurations...")
    
    # Configuration 1: With project ID in URL (old format)
    url1 = f"https://api.scaleway.ai/{project_id or '4a8fd76b-8606-46e6-afe6-617ce8eeb948'}/v1/chat/completions"
    print(f"\n1. Testing: {url1}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    test_payload = {
        "model": "llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(url1, json=test_payload, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 403:
            print("   ✗ Authentication failed - check API key")
        elif response.status_code == 404:
            print("   ✗ Endpoint not found - wrong URL format")
        else:
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Configuration 2: Standard Scaleway format
    url2 = "https://api.scaleway.ai/v1/chat/completions"
    print(f"\n2. Testing: {url2}")
    
    try:
        response = requests.post(url2, json=test_payload, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ This URL format works!")
        else:
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")

print("\n" + "=" * 60)
print("RECOMMENDED .env FILE:")
print("=" * 60)
print("""
# Scaleway API Configuration
SCW_API_KEY=your_scaleway_api_key_here
SCALEWAY_API_KEY=your_scaleway_api_key_here  # Some scripts use this name
LLM_PROVIDER=scaleway
LLM_MODEL=llama-3.3-70b-instruct

# Optional - leave empty to use default
SCALEWAY_PROJECT_ID=
""")

print("\nTo get your Scaleway API key:")
print("1. Go to: https://console.scaleway.com/iam/api-keys")
print("2. Create a new API key or copy an existing one")
print("3. Make sure the key has 'AI' permissions")
print("4. Copy the full key (starts with 'SCW')")
print("5. Add it to your .env file")