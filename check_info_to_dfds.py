#!/usr/bin/env python3
"""
Check why info_to_dfds.py is failing to find documents
"""
import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config
from services.document_loader_service import DocumentLoaderService

def test_document_loading():
    """Test the document loading process"""
    print("=== Testing Document Loading Process ===")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    
    # Get configuration
    config = Config.get_config()
    print(f"\nConfiguration:")
    print(f"  input_dir: {config['input_dir']}")
    print(f"  output_dir: {config['output_dir']}")
    
    # Check environment variables
    print(f"\nEnvironment variables:")
    print(f"  INPUT_DIR: {os.getenv('INPUT_DIR')}")
    print(f"  OUTPUT_DIR: {os.getenv('OUTPUT_DIR')}")
    print(f"  SESSION_ID: {os.getenv('SESSION_ID')}")
    
    # Initialize document loader
    doc_loader = DocumentLoaderService(config)
    
    # Test loading from input directory
    print(f"\n--- Testing load from input_dir ({config['input_dir']}) ---")
    try:
        documents1, doc_info1 = doc_loader.load_documents_from_step1(config['input_dir'])
        print(f"✓ Successfully loaded {len(documents1)} documents")
        for i, info in enumerate(doc_info1):
            print(f"  Document {i+1}: {info}")
            if documents1[i]:
                print(f"    Content preview: {documents1[i][:100]}...")
    except Exception as e:
        print(f"✗ Failed to load: {e}")
        import traceback
        traceback.print_exc()
    
    # Test loading from output directory
    print(f"\n--- Testing load from output_dir ({config['output_dir']}) ---")
    try:
        documents2, doc_info2 = doc_loader.load_documents_from_step1(config['output_dir'])
        print(f"✓ Successfully loaded {len(documents2)} documents")
        for i, info in enumerate(doc_info2):
            print(f"  Document {i+1}: {info}")
            if documents2[i]:
                print(f"    Content preview: {documents2[i][:100]}...")
    except Exception as e:
        print(f"✗ Failed to load: {e}")
        import traceback
        traceback.print_exc()
    
    # Check what would happen in main
    print(f"\n--- Simulating main() behavior ---")
    documents = documents1 if documents1 else documents2
    doc_info = doc_info1 if doc_info1 else doc_info2
    
    if not documents:
        print("✗ No documents found for processing (this is the error!)")
    else:
        print(f"✓ Would process {len(documents)} documents")
    
    # Check for session files
    if os.getenv('SESSION_ID'):
        session_id = os.getenv('SESSION_ID')
        print(f"\n--- Checking for session files (SESSION_ID: {session_id}) ---")
        for directory in [config['input_dir'], config['output_dir']]:
            session_file = os.path.join(directory, f"session_{session_id}.txt")
            if os.path.exists(session_file):
                print(f"✓ Found session file: {session_file}")
            else:
                print(f"✗ No session file at: {session_file}")

if __name__ == "__main__":
    test_document_loading()