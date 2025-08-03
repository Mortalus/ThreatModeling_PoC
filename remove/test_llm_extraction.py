#!/usr/bin/env python3
"""
Test the LLM extraction service directly to see why it's falling back to rule-based
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_llm_extraction():
    print("🧪 TESTING LLM EXTRACTION SERVICE")
    print("=" * 60)
    
    # Load environment
    load_dotenv()
    
    try:
        # Import required modules
        from config.settings import Config
        from services.llm_service import LLMService
        from services.document_analysis_service import DocumentAnalysisService
        
        print("✅ Modules imported successfully")
        
        # Get configuration
        config = Config.get_config()
        
        print(f"🔧 Configuration:")
        print(f"   LLM Provider: {config['llm_provider']}")
        print(f"   LLM Model: {config['llm_model']}")
        print(f"   API URL: {config.get('scw_api_url', 'Not set')}")
        print(f"   API Key: {'***' + config.get('scw_secret_key', '')[-4:] if config.get('scw_secret_key') else 'Not set'}")
        print()
        
        # Initialize services
        print("🚀 Initializing services...")
        llm_service = LLMService(config)
        doc_analyzer = DocumentAnalysisService()
        
        # Load test content
        print("📄 Loading test content...")
        test_file = './input_documents/20250802_203015_extracted.txt'
        
        if os.path.exists(test_file):
            with open(test_file, 'r') as f:
                content = f.read()
            print(f"   ✅ Loaded: {len(content)} characters")
            print(f"   📄 Preview: {content[:150]}...")
        else:
            print(f"   ❌ Test file not found: {test_file}")
            print("   Using sample content instead")
            content = """
            HealthData Insights Platform - System Design Document
            
            System Components:
            - Web Application Server
            - Database Server (PostgreSQL)
            - Authentication Service
            - API Gateway
            
            External Entities:
            - Healthcare Providers
            - Patients
            - Insurance Companies
            - Regulatory Bodies
            
            Data Flows:
            - Patient data from Providers to Web Application
            - Encrypted health records to Database
            - Authentication tokens between services
            - Audit logs to Compliance system
            """
        
        print()
        
        # Test document analysis
        print("📊 Testing document analysis...")
        doc_analysis = doc_analyzer.analyze_document_content(content)
        print(f"   Industry: {doc_analysis.get('industry_context', 'Unknown')}")
        print(f"   Document Type: {doc_analysis.get('document_type', 'Unknown')}")
        print(f"   Complexity: {doc_analysis.get('complexity_score', 0)}")
        print()
        
        # Test LLM extraction
        print("🤖 Testing LLM extraction...")
        print("   This is where we should see the actual LLM call...")
        
        # Call the extraction method directly
        result = llm_service.extract_dfd_components(content, doc_analysis)
        
        if result:
            print("✅ LLM extraction returned a result")
            
            # Check if it's rule-based or LLM-based
            result_dict = result.to_dict()
            
            print(f"📊 Result summary:")
            print(f"   Project: {result_dict.get('project_name', 'Unknown')}")
            print(f"   External Entities: {len(result_dict.get('external_entities', []))}")
            print(f"   Processes: {len(result_dict.get('processes', []))}")
            print(f"   Assets: {len(result_dict.get('assets', []))}")
            print(f"   Data Flows: {len(result_dict.get('data_flows', []))}")
            
            # Check assumptions to see if it's rule-based
            assumptions = result_dict.get('assumptions', [])
            if any('rule-based' in str(assumption).lower() for assumption in assumptions):
                print("❌ This is RULE-BASED extraction (LLM failed)")
                print("   The LLM call failed silently and fell back to rules")
            else:
                print("✅ This appears to be LLM-based extraction")
            
            # Show some example content
            if result_dict.get('external_entities'):
                print(f"\n📝 Sample entities: {result_dict['external_entities'][:3]}")
            if result_dict.get('processes'):
                print(f"📝 Sample processes: {result_dict['processes'][:3]}")
                
        else:
            print("❌ LLM extraction returned None")
        
        print()
        
        # Test raw LLM call
        print("🔌 Testing raw LLM connection...")
        
        # Test if the LLM service has a working client
        if hasattr(llm_service, 'raw_client') and llm_service.raw_client:
            print("   ✅ Raw client is available")
            
            # Try a simple test call
            try:
                test_prompt = "Respond with exactly: 'LLM Working'"
                
                response = llm_service.raw_client.chat.completions.create(
                    model=llm_service.model,
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=50,
                    temperature=0.1
                )
                
                response_text = response.choices[0].message.content
                print(f"   ✅ LLM Response: '{response_text}'")
                
                if "LLM Working" in response_text:
                    print("   ✅ LLM is responding correctly!")
                else:
                    print("   ⚠️  LLM responded but not as expected")
                    
            except Exception as e:
                print(f"   ❌ LLM call failed: {e}")
                print("   This explains why it's falling back to rule-based extraction")
                
        else:
            print("   ❌ No raw client available")
            print("   This explains why it's using rule-based extraction")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_extraction()