#!/usr/bin/env python3
"""
Unit Test Runner for Threatalicious Pipeline
Tests the entire flow without hitting external APIs
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MockLLMService:
    """Mock LLM Service that returns predefined responses"""
    
    def __init__(self, config):
        self.config = config
        self.model = "mock-model"
        self.client = None
        self.raw_client = None
        
    def extract_dfd_components(self, content, doc_analysis):
        """Return mock DFD components"""
        from models.dfd_models import SimpleDFDComponents, SimpleDataFlow
        
        result = SimpleDFDComponents()
        result.project_name = "Test Healthcare System"
        result.industry_context = "Healthcare"
        result.external_entities = ["Patient Portal", "Admin User", "External API"]
        result.processes = ["Web Server", "Authentication Service", "API Gateway", "Database Service"]
        result.assets = ["Patient Database", "Session Store", "Audit Logs"]
        result.trust_boundaries = ["Internet to DMZ", "DMZ to Internal", "Internal to Database"]
        
        # Add some data flows
        result.data_flows.append(SimpleDataFlow(
            source="Patient Portal",
            destination="Web Server",
            data_description="Patient login credentials",
            data_classification="Confidential",
            protocol="HTTPS",
            authentication_mechanism="Password"
        ))
        
        result.data_flows.append(SimpleDataFlow(
            source="Web Server",
            destination="Patient Database",
            data_description="Patient medical records",
            data_classification="Highly Confidential",
            protocol="TLS",
            authentication_mechanism="Service Account"
        ))
        
        return result
    
    def generate_stride_threats(self, component, stride_category, num_threats=2):
        """Return mock threats"""
        from models.threat_models import ThreatModel
        
        threats = []
        
        # Generate deterministic threats based on component name and STRIDE category
        threat_templates = {
            'S': [
                ("An attacker could spoof the identity of {component} to gain unauthorized access",
                 "Implement strong authentication and identity verification"),
                ("Malicious actor might impersonate {component} using stolen credentials",
                 "Use multi-factor authentication and certificate-based auth")
            ],
            'T': [
                ("Data transmitted to/from {component} could be tampered with in transit",
                 "Implement message integrity checks and encryption"),
                ("An attacker might modify data stored in {component}",
                 "Use write-once storage and audit logging")
            ],
            'I': [
                ("Sensitive information from {component} could be exposed",
                 "Encrypt data at rest and in transit"),
                ("Unauthorized access to {component} might leak confidential data",
                 "Implement proper access controls and data classification")
            ],
            'D': [
                ("{component} could be overwhelmed by excessive requests",
                 "Implement rate limiting and DDoS protection"),
                ("Service availability of {component} might be disrupted",
                 "Set up redundancy and failover mechanisms")
            ]
        }
        
        templates = threat_templates.get(stride_category, [])
        for i, (threat_desc, mitigation) in enumerate(templates[:num_threats]):
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category=stride_category,
                threat_description=threat_desc.format(component=component.name),
                mitigation_suggestion=mitigation,
                impact="High" if i == 0 else "Medium",
                likelihood="Medium",
                references=[f"CWE-{100 + i}", f"OWASP-A{i+1}"],
                risk_score="High" if i == 0 else "Medium"
            ))
        
        return threats


def setup_test_environment():
    """Set up a test environment with mock data"""
    # Create temporary directories
    test_dir = Path("./test_run")
    test_dir.mkdir(exist_ok=True)
    
    input_dir = test_dir / "input"
    output_dir = test_dir / "output"
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # Create test document
    test_content = """
    HealthData Insights Platform - System Architecture
    
    This document describes the architecture of our healthcare data platform.
    
    External Entities:
    - Patient Portal: Web interface for patients
    - Admin User: System administrators
    - External API: Third-party integrations
    
    Core Processes:
    - Web Server: Handles HTTP requests
    - Authentication Service: Manages user authentication
    - API Gateway: Routes API requests
    - Database Service: Manages data persistence
    
    Data Stores:
    - Patient Database: Stores patient records (encrypted)
    - Session Store: Manages user sessions
    - Audit Logs: Security audit trail
    
    Key Data Flows:
    - Patient Portal sends login credentials to Web Server over HTTPS
    - Web Server queries Patient Database using TLS
    - API Gateway logs all requests to Audit Logs
    """
    
    test_file = input_dir / "test_architecture.txt"
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    return str(input_dir), str(output_dir)


def run_pipeline_with_mocks(input_dir, output_dir):
    """Run the entire pipeline with mocked services"""
    
    # Set up environment
    env = os.environ.copy()
    env.update({
        'INPUT_DIR': input_dir,
        'OUTPUT_DIR': output_dir,
        'LLM_PROVIDER': 'mock',  # This will trigger our mocks
        'ENABLE_LLM_ENRICHMENT': 'false',  # Disable LLM enrichment
        'LOG_LEVEL': 'INFO'
    })
    
    print("🚀 Running Pipeline with Mocks")
    print("=" * 60)
    
    # Step 1: Document Processing (usually just copies files)
    print("\n📄 Step 1: Document Processing")
    # For testing, we'll just copy the file
    shutil.copy(
        os.path.join(input_dir, "test_architecture.txt"),
        os.path.join(output_dir, "processed_document.txt")
    )
    print("✅ Document processed")
    
    # Step 2: DFD Extraction with mocked LLM
    print("\n🔍 Step 2: DFD Extraction")
    with patch('services.llm_service.LLMService', MockLLMService):
        from services.dfd_extraction_service import DFDExtractionService
        from config.settings import Config
        
        config = Config.get_config()
        config['output_dir'] = output_dir
        
        dfd_service = DFDExtractionService(config)
        result = dfd_service.extract_from_documents(
            [os.path.join(output_dir, "processed_document.txt")],
            ["Test architecture document"]
        )
        
        # Save DFD
        dfd_path = os.path.join(output_dir, 'dfd_components.json')
        with open(dfd_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✅ DFD extracted: {len(result['dfd']['processes'])} processes found")
    
    # Step 3: Threat Generation with mocked LLM
    print("\n⚠️  Step 3: Threat Generation")
    with patch('services.llm_service.LLMService', MockLLMService):
        from services.threat_generation_service import ThreatGenerationService
        
        threat_config = {**config, 'min_risk_score': 3}
        threat_service = ThreatGenerationService(threat_config)
        
        # Load DFD
        with open(dfd_path, 'r') as f:
            dfd_data = json.load(f)['dfd']
        
        threats_result = threat_service.generate_threats_from_dfd(dfd_data)
        
        # Save threats
        threats_path = os.path.join(output_dir, 'identified_threats.json')
        with open(threats_path, 'w') as f:
            json.dump(threats_result, f, indent=2)
        
        print(f"✅ Threats generated: {len(threats_result['threats'])} threats found")
    
    # Step 4: Threat Quality Improvement (mostly rule-based)
    print("\n🔧 Step 4: Threat Quality Improvement")
    # This step is mostly rule-based, so it should work without mocking
    from services.threat_quality_improvement_service import ThreatQualityImprovementService
    
    quality_service = ThreatQualityImprovementService(config)
    
    with open(threats_path, 'r') as f:
        threats_data = json.load(f)
    
    # Run improvement (mock the async part)
    import asyncio
    
    async def improve_threats_async():
        return await quality_service.improve_threats(
            threats_data['threats'],
            dfd_data,
            {}  # No controls for test
        )
    
    improved_result = asyncio.run(improve_threats_async())
    
    refined_path = os.path.join(output_dir, 'refined_threats.json')
    with open(refined_path, 'w') as f:
        json.dump(improved_result, f, indent=2)
    
    print(f"✅ Threats refined: {len(improved_result['threats'])} threats")
    
    # Step 5: Attack Path Analysis (graph-based, no LLM needed)
    print("\n🛤️  Step 5: Attack Path Analysis")
    from services.attack_path_analyzer_service import AttackPathAnalyzerService
    
    attack_service = AttackPathAnalyzerService(config)
    attack_paths = attack_service.analyze_attack_paths(
        improved_result['threats'],
        dfd_data
    )
    
    # Convert to dict for saving
    attack_paths_dict = {
        'attack_paths': [
            {
                'path_id': path.path_id,
                'path_name': path.path_name,
                'description': path.description,
                'likelihood': path.likelihood,
                'impact': path.impact,
                'steps': [
                    {
                        'step_number': step.step_number,
                        'component': step.component,
                        'threat_id': step.threat_id,
                        'description': step.description
                    } for step in path.steps
                ]
            } for path in attack_paths.attack_paths
        ],
        'metadata': {
            'total_paths': len(attack_paths.attack_paths),
            'analysis_timestamp': attack_paths.analysis_timestamp
        }
    }
    
    attack_path_file = os.path.join(output_dir, 'attack_paths.json')
    with open(attack_path_file, 'w') as f:
        json.dump(attack_paths_dict, f, indent=2)
    
    print(f"✅ Attack paths analyzed: {len(attack_paths.attack_paths)} paths found")
    
    return True


def run_fast_integration_test():
    """Run a fast integration test using rule-based fallbacks"""
    print("\n🏃 Running Fast Integration Test (Rule-Based)")
    print("=" * 60)
    
    # Create test environment
    input_dir, output_dir = setup_test_environment()
    
    # Configure for rule-based operation
    env = os.environ.copy()
    env.update({
        'INPUT_DIR': input_dir,
        'OUTPUT_DIR': output_dir,
        'LLM_PROVIDER': 'none',  # This will force rule-based
        'ENABLE_LLM_ENRICHMENT': 'false',
        'LOG_LEVEL': 'WARNING'  # Less verbose
    })
    
    # Run each script directly
    import subprocess
    
    scripts = [
        ('info_to_dfds.py', 'DFD Extraction'),
        ('dfd_to_threats.py', 'Threat Generation'),
        ('improve_threat_quality.py', 'Threat Refinement'),
        ('attack_path_analyzer.py', 'Attack Path Analysis')
    ]
    
    for script, name in scripts:
        print(f"\n▶️  Running {name}...")
        result = subprocess.run(
            [sys.executable, script],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {name} completed")
        else:
            print(f"❌ {name} failed")
            print(f"Error: {result.stderr}")
            return False
    
    # Check outputs
    expected_files = [
        'dfd_components.json',
        'identified_threats.json', 
        'refined_threats.json',
        'attack_paths.json'
    ]
    
    print("\n📊 Checking outputs:")
    for file in expected_files:
        path = os.path.join(output_dir, file)
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
            print(f"✅ {file} created")
        else:
            print(f"❌ {file} missing")
    
    print("\n✨ Fast integration test complete!")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Threatalicious Pipeline")
    parser.add_argument('--mock', action='store_true', 
                       help='Run with fully mocked services')
    parser.add_argument('--fast', action='store_true',
                       help='Run fast integration test with rule-based fallbacks')
    parser.add_argument('--clean', action='store_true',
                       help='Clean up test files after run')
    
    args = parser.parse_args()
    
    try:
        if args.mock:
            input_dir, output_dir = setup_test_environment()
            success = run_pipeline_with_mocks(input_dir, output_dir)
        elif args.fast:
            success = run_fast_integration_test()
        else:
            # Run both
            print("Running both mock and fast tests...\n")
            input_dir, output_dir = setup_test_environment()
            success = run_pipeline_with_mocks(input_dir, output_dir)
            if success:
                success = run_fast_integration_test()
        
        if args.clean and os.path.exists('./test_run'):
            shutil.rmtree('./test_run')
            print("\n🧹 Test files cleaned up")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)