#!/usr/bin/env python3
"""
Verbose test script that mimics the exact execution path of info_to_dfds.py
This will help us identify exactly where the script is failing silently
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path (like the script does)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_verbose_logging():
    """Set up verbose logging to see everything"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def test_dfd_extraction_verbose():
    print("🔍 VERBOSE DFD EXTRACTION TEST")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    setup_verbose_logging()
    
    try:
        # Import the modules that info_to_dfds.py imports
        print("📦 Importing modules...")
        
        from config.settings import Config
        print("   ✓ Config imported")
        
        from services.document_loader_service import DocumentLoaderService
        print("   ✓ DocumentLoaderService imported")
        
        from services.dfd_extraction_service import DFDExtractionService
        print("   ✓ DFDExtractionService imported")
        
        from utils.logging_utils import logger, setup_logging
        print("   ✓ Logging utils imported")
        
        # Set up configuration (like the script does)
        print("\n⚙️  Setting up configuration...")
        config = Config.get_config()
        
        # Override for our test
        config.update({
            'input_dir': './input_documents',
            'output_dir': './output',
            'dfd_output_path': './output/dfd_components.json'
        })
        
        print(f"   Input dir: {config['input_dir']}")
        print(f"   Output dir: {config['output_dir']}")
        print(f"   LLM Provider: {config['llm_provider']}")
        print(f"   LLM Model: {config['llm_model']}")
        print(f"   API URL: {config.get('scw_api_url', 'Not set')}")
        
        # Ensure directories exist
        Config.ensure_directories(config['output_dir'])
        
        # Test 1: Document Loading
        print("\n📂 Testing document loading...")
        doc_loader = DocumentLoaderService(config)
        
        # Try to load from both input_documents and output folders
        documents1, doc_info1 = doc_loader.load_documents_from_step1(config['input_dir'])
        print(f"   From input_documents: {len(documents1)} documents")
        
        documents2, doc_info2 = doc_loader.load_documents_from_step1(config['output_dir'])
        print(f"   From output: {len(documents2)} documents")
        
        # Use whichever has documents
        documents = documents1 if documents1 else documents2
        doc_info = doc_info1 if doc_info1 else doc_info2
        
        if not documents:
            print("   ❌ No documents found!")
            return False
        
        print(f"   ✓ Found {len(documents)} documents")
        print(f"   📄 Document info: {doc_info}")
        print(f"   📊 Total content length: {sum(len(doc) for doc in documents)} chars")
        
        # Test 2: DFD Extraction Service
        print("\n🚀 Testing DFD extraction...")
        extraction_service = DFDExtractionService(config)
        
        print("   📝 Calling extract_from_documents...")
        result = extraction_service.extract_from_documents(documents, doc_info)
        
        if not result:
            print("   ❌ Extraction returned None!")
            return False
        
        print(f"   ✓ Extraction completed")
        print(f"   📊 Result type: {type(result)}")
        print(f"   🔑 Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Test 3: Output File Creation
        print("\n💾 Testing output file creation...")
        output_path = config['dfd_output_path']
        
        print(f"   Output path: {output_path}")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"   ✓ File written successfully")
            print(f"   📊 File size: {os.path.getsize(output_path)} bytes")
            
            # Verify content
            with open(output_path, 'r') as f:
                saved_data = json.load(f)
            
            if 'dfd' in saved_data:
                dfd = saved_data['dfd']
                print(f"   📋 DFD Components:")
                print(f"     - External Entities: {len(dfd.get('external_entities', []))}")
                print(f"     - Processes: {len(dfd.get('processes', []))}")
                print(f"     - Assets: {len(dfd.get('assets', []))}")
                print(f"     - Data Flows: {len(dfd.get('data_flows', []))}")
                
                if dfd.get('external_entities'):
                    print(f"   📝 Example entity: {dfd['external_entities'][0]}")
            
            print("\n✅ SUCCESS! DFD extraction completed successfully!")
            return True
            
        except Exception as e:
            print(f"   ❌ Error writing output file: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Check that all required modules are available")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dfd_extraction_verbose()
    if success:
        print("\n🎉 If this worked, then info_to_dfds.py should work too!")
        print("   The issue might be with environment variables in the Flask context")
    else:
        print("\n🔧 This test failed, showing us where the real problem is")
