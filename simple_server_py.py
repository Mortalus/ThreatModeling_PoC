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
HTML_FILE = "threat-modeling-visualizer.html"

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
            print("2. Open your browser to: http://localhost:3000")
            print("3. Or wait 3 seconds for auto-open...")
            print("\n🛑 Press Ctrl+C to stop the server")
            print("=" * 60)
            
            # Auto-open browser after 3 seconds
            import threading
            def open_browser():
                import time
                time.sleep(3)
                try:
                    webbrowser.open(f'http://localhost:{PORT}')
                    print(f"\n🚀 Opened browser to http://localhost:{PORT}")
                except Exception as e:
                    print(f"\n⚠️  Could not auto-open browser: {e}")
                    print(f"   Manually open: http://localhost:{PORT}")
            
            browser_thread = threading.Thread(target=open_browser, daemon=True)
            browser_thread.start()
            
            # Start serving
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Error: Port {PORT} is already in use")
            print("Try a different port or stop the other service")
        else:
            print(f"❌ Error starting server: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()