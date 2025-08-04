#!/usr/bin/env python3
"""
Check if the API key is properly set
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config

def check_api_key():
    """Check API key configuration"""
    print("=== API KEY CHECK ===")
    
    # Check environment variables
    env_keys = ['SCW_SECRET_KEY', 'SCW_API_KEY', 'LLM_PROVIDER']
    print("\nEnvironment Variables:")
    for key in env_keys:
        value = os.environ.get(key)
        if key in ['SCW_SECRET_KEY', 'SCW_API_KEY'] and value:
            print(f"  {key}: ***{value[-4:]}")
        else:
            print(f"  {key}: {value}")
    
    # Check config
    config = Config.get_config()
    print("\nConfiguration:")
    print(f"  llm_provider: {config['llm_provider']}")
    print(f"  llm_model: {config['llm_model']}")
    if config.get('scw_secret_key'):
        print(f"  scw_secret_key: ***{config['scw_secret_key'][-4:]}")
    else:
        print(f"  scw_secret_key: None")
    
    # Check .env file
    print("\n.env File:")
    if os.path.exists('.env'):
        print("  .env file exists")
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, _ = line.split('=', 1)
                        if key in ['SCW_SECRET_KEY', 'SCW_API_KEY']:
                            print(f"  {key} is defined in .env")
    else:
        print("  .env file NOT FOUND")
    
    # Recommendations
    print("\nRecommendations:")
    if not config.get('scw_secret_key'):
        print("  ❌ No API key found!")
        print("  1. Create a .env file in the project root")
        print("  2. Add: SCW_SECRET_KEY=your_actual_api_key")
        print("  3. Restart the application")
    else:
        print("  ✅ API key is configured")

if __name__ == "__main__":
    check_api_key()