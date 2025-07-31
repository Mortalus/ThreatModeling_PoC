#!/usr/bin/env python3
"""
Minimal Flask app that properly calls info_to_dfds.py
This should work if the script works directly
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import sys
from dotenv import load_dotenv
import json

# IMPORTANT: Load .env file BEFORE creating Flask app
load_dotenv()

app = Flask(__name__)
CORS(app)

# Verify environment on startup
print("\n" + "="*60)
print("MINIMAL FLASK APP STARTING")
print("="*60)
api_key = os.getenv('SCW_API_KEY')
if api_key:
    print(f"✓ API Key loaded: ***{api_key[-4:]}")
else:
    print("✗ No API key found!")
print(f"Working directory: {os.getcwd()}")
print(f"Python: {sys.executable}")
print("="*60 + "\n")

@app.route('/api/test-script', methods=['POST'])
def test_script():
    """Run info_to_dfds.py with minimal setup"""
    
    # Ensure directories exist
    os.makedirs('./input_documents', exist_ok=True)
    os.makedirs('./output', exist_ok=True)
    
    # Get text from request or use default
    data = request.get_json() or {}
    text_content = data.get('text', '''System: Test App
External Entities: User
Assets: Database
Processes: Web Server
Data Flows:
- From User to Web Server: Data, Confidential, HTTPS, Auth''')
    
    # Save text to file
    with open('./input_documents/test.txt', 'w') as f:
        f.write(text_content)
    
    # CRITICAL: Pass current environment to subprocess
    # This ensures the API key is available
    env = os.environ.copy()
    
    # Add any additional variables needed
    env.update({
        'INPUT_DIR': './input_documents',
        'OUTPUT_DIR': './output',
        'DFD_OUTPUT_PATH': './output/dfd_components.json'
    })
    
    try:
        # Run the script
        print(f"Running info_to_dfds.py...")
        print(f"API Key in env: {'Yes' if env.get('SCW_API_KEY') else 'No'}")
        
        result = subprocess.run(
            [sys.executable, 'info_to_dfds.py'],
            env=env,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        print(f"Script returned: {result.returncode}")
        
        if result.returncode == 0:
            # Try to load the output
            output_file = './output/dfd_components.json'
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    dfd_data = json.load(f)
                return jsonify({
                    'success': True,
                    'data': dfd_data,
                    'message': 'Script executed successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Output file not created',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                })
        else:
            return jsonify({
                'success': False,
                'error': 'Script failed',
                'stdout': result.stdout[-1000:],  # Last 1000 chars
                'stderr': result.stderr[-1000:],
                'return_code': result.returncode
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Script timed out after 2 minutes'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'type': type(e).__name__
        })

@app.route('/api/check-env', methods=['GET'])
def check_env():
    """Check if environment variables are accessible"""
    return jsonify({
        'has_api_key': bool(os.getenv('SCW_API_KEY')),
        'working_dir': os.getcwd(),
        'python': sys.executable,
        'info_to_dfds_exists': os.path.exists('info_to_dfds.py'),
        'dirs_exist': {
            'input_documents': os.path.exists('./input_documents'),
            'output': os.path.exists('./output')
        }
    })

@app.route('/')
def home():
    """Simple test page"""
    return '''
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h1>Minimal Flask Test</h1>
        <button onclick="checkEnv()">Check Environment</button>
        <button onclick="runScript()">Run info_to_dfds.py</button>
        <pre id="output" style="background: #f0f0f0; padding: 10px; margin-top: 20px;"></pre>
        
        <script>
        async function checkEnv() {
            const resp = await fetch('/api/check-env');
            const data = await resp.json();
            document.getElementById('output').textContent = JSON.stringify(data, null, 2);
        }
        
        async function runScript() {
            document.getElementById('output').textContent = 'Running script...';
            const resp = await fetch('/api/test-script', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: 'System: Test\\nExternal Entities: User\\nAssets: DB\\nProcesses: Server'})
            });
            const data = await resp.json();
            document.getElementById('output').textContent = JSON.stringify(data, null, 2);
        }
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("\nStarting Flask app on http://localhost:5002")
    print("Open this URL and click 'Run info_to_dfds.py' to test\n")
    app.run(debug=True, port=5002)