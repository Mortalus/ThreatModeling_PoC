"""
Quick script to check if your Flask app has proper CORS configuration.
Run this to see what CORS headers your Flask app is sending.
"""

import requests
import json

def test_cors():
    base_url = "http://localhost:5000"
    
    # Test the health endpoint
    try:
        print("🔧 Testing Flask CORS configuration...")
        print("=" * 50)
        
        # Make a simple GET request
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"✅ Health check status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
        
        # Check CORS headers
        print("CORS Headers:")
        cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods', 
            'Access-Control-Allow-Headers',
            'Access-Control-Allow-Credentials'
        ]
        
        for header in cors_headers:
            value = response.headers.get(header, 'NOT SET')
            print(f"  {header}: {value}")
        
        print()
        
        # Test upload endpoint exists
        try:
            # Don't actually upload, just check if endpoint exists
            response = requests.options(f"{base_url}/api/upload", timeout=5)
            print(f"✅ Upload endpoint accessible: {response.status_code}")
        except:
            print("❌ Upload endpoint not accessible")
            
        print()
        print("🎯 Recommendations:")
        print("1. Make sure your Flask app has CORS configured")
        print("2. Add these headers to your Flask responses:")
        print("   - Access-Control-Allow-Origin: http://localhost:3001")
        print("   - Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS")
        print("   - Access-Control-Allow-Headers: Content-Type, Authorization")
        print()
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask backend at http://localhost:5000")
        print("Make sure your Flask app is running with: python app.py")
    except Exception as e:
        print(f"❌ Error testing CORS: {e}")

if __name__ == "__main__":
    test_cors()
