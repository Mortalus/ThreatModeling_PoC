#!/usr/bin/env python3
"""
Test if the LLM service is working properly
"""
import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config
from services.llm_service import LLMService
from services.document_analysis_service import DocumentAnalysisService

def test_llm_service():
    """Test the LLM service with a simple request"""
    print("=== TESTING LLM SERVICE ===")
    
    # Get configuration
    config = Config.get_config()
    
    print(f"\nConfiguration:")
    print(f"  Provider: {config['llm_provider']}")
    print(f"  Model: {config['llm_model']}")
    if config.get('scw_secret_key'):
        print(f"  API Key: ***{config['scw_secret_key'][-4:]}")
    else:
        print(f"  API Key: NOT SET")
    
    # Initialize services
    try:
        llm_service = LLMService(config)
        doc_analyzer = DocumentAnalysisService()
        print("\n✅ Services initialized successfully")
    except Exception as e:
        print(f"\n❌ Failed to initialize services: {e}")
        return
    
    # Test with a simple document
    test_content = """
    Simple Test System
    
    Components:
    - Web Application: Handles user requests
    - Database: Stores user data
    - External API: Third-party payment service
    
    Data Flows:
    - Users send login credentials to Web Application
    - Web Application queries Database for user records
    - Web Application sends payment data to External API
    """
    
    print("\n📝 Test document created")
    
    # Analyze document
    print("\n🔍 Analyzing document...")
    doc_analysis = doc_analyzer.analyze_document_content(test_content)
    print(f"  Document type: {doc_analysis['document_type']}")
    print(f"  Industry: {doc_analysis['industry_context']}")
    
    # Extract DFD components
    print("\n🚀 Extracting DFD components...")
    try:
        result = llm_service.extract_dfd_components(test_content, doc_analysis)
        if result:
            print("\n✅ LLM extraction successful!")
            dfd_dict = result.to_dict()
            print(f"  External entities: {len(dfd_dict.get('external_entities', []))}")
            print(f"  Processes: {len(dfd_dict.get('processes', []))}")
            print(f"  Assets: {len(dfd_dict.get('assets', []))}")
            print(f"  Data flows: {len(dfd_dict.get('data_flows', []))}")
            
            # Save result for inspection
            with open('test_llm_result.json', 'w') as f:
                json.dump(dfd_dict, f, indent=2)
            print("\n📄 Full result saved to test_llm_result.json")
        else:
            print("\n❌ LLM extraction returned None")
    except Exception as e:
        print(f"\n❌ LLM extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_service()