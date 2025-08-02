#!/usr/bin/env python3
"""
Simple HTTP server to serve the frontend HTML file
This avoids CORS issues when opening HTML files directly
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Configuration
PORT = 1337
HTML_FILE = "index.html"  # Changed from threat-modeling-visualizer.html

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        # Serve the HTML file for root path
        if self.path == '/' or self.path == '':
            self.path = f'/{HTML_FILE}'
        super().do_GET()

def main():
    # Check if HTML file exists
    if not os.path.exists(HTML_FILE):
        print(f"❌ Error: {HTML_FILE} not found in current directory")
        print("Please make sure the HTML file is in the same directory as this script")
        return
    
    # Start server
    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print("=" * 60)
            print("🌐 FRONTEND SERVER STARTING")
            print("=" * 60)
            print(f"✓ Serving: {HTML_FILE}")
            print(f"✓ Server: http://localhost:{PORT}")
            print(f"✓ Backend: http://localhost:5000 (make sure it's running)")
            print("=" * 60)
            print("\n📋 INSTRUCTIONS:")
            print("1. Make sure your Flask backend is running (python app.py)")
            print("2. Open your browser to: http://localhost:1337")
            print("3. Use Ctrl+C to stop the server")
            print("=" * 60)
            
            # Optionally open browser automatically
            # webbrowser.open(f'http://localhost:{PORT}')
            
            print("\n✅ Server is running...")
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

if __name__ == "__main__":
    main()