#!/usr/bin/env python3
"""
DFD to Threats Generator Script - Enhanced Version with Async Support

This script analyzes DFD (Data Flow Diagram) components and generates realistic threats
using the STRIDE methodology with intelligent filtering and risk-based prioritization.

Key improvements:
- Async/sync processing modes
- Component-specific STRIDE mapping
- Risk-based component prioritization
- Advanced threat deduplication
- Quality filtering for realistic results
- Detailed progress tracking
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import services
try:
    from config.settings import Config
    from services.threat_generation_service import ThreatGenerationService
    base_config = Config.get_config()
    # Merge with threat-specific config
    config = {
        **base_config,
        'dfd_input_path': base_config.get('dfd_output_path', './output/dfd_components.json'),  # Map dfd_output_path to dfd_input_path
        'threats_output_path': base_config.get('threats_output_path', './output/identified_threats.json'),
        'min_risk_score': int(os.getenv('MIN_RISK_SCORE', '3')),
        'max_components_to_analyze': int(os.getenv('MAX_COMPONENTS_TO_ANALYZE', '20')),
        'similarity_threshold': float(os.getenv('SIMILARITY_THRESHOLD', '0.70')),
        'max_concurrent_calls': int(os.getenv('MAX_CONCURRENT_CALLS', '5')),
        'enable_async_processing': os.getenv('ENABLE_ASYNC', 'true').lower() == 'true',
        'force_rule_based': os.getenv('FORCE_RULE_BASED', 'false').lower() == 'true',
        'debug_mode': os.getenv('DEBUG_MODE', 'false').lower() == 'true',
        'scw_secret_key': base_config.get('scw_secret_key'),  # Ensure API key is passed
        'scw_api_url': base_config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
        'llm_provider': base_config.get('llm_provider', 'scaleway'),
        'llm_model': base_config.get('llm_model', 'llama-3.3-70b-instruct')
    }
except ImportError:
    # Fallback to simple config
    config = {
        'llm_provider': os.getenv('LLM_PROVIDER', 'scaleway'),
        'llm_model': os.getenv('LLM_MODEL', 'llama-3.3-70b-instruct'),
        'output_dir': os.getenv('OUTPUT_DIR', './output'),
        'dfd_input_path': os.getenv('DFD_OUTPUT_PATH', './output/dfd_components.json'),  # Use DFD_OUTPUT_PATH
        'threats_output_path': os.getenv('THREATS_OUTPUT_PATH', './output/identified_threats.json'),
        'min_risk_score': int(os.getenv('MIN_RISK_SCORE', '3')),
        'max_components_to_analyze': int(os.getenv('MAX_COMPONENTS_TO_ANALYZE', '20')),
        'similarity_threshold': float(os.getenv('SIMILARITY_THRESHOLD', '0.70')),
        'max_concurrent_calls': int(os.getenv('MAX_CONCURRENT_CALLS', '5')),
        'enable_async_processing': os.getenv('ENABLE_ASYNC', 'true').lower() == 'true',
        'force_rule_based': os.getenv('FORCE_RULE_BASED', 'false').lower() == 'true',
        'debug_mode': os.getenv('DEBUG_MODE', 'false').lower() == 'true',
        'scw_secret_key': os.getenv('SCW_SECRET_KEY') or os.getenv('SCW_API_KEY'),
        'scw_api_url': os.getenv('SCW_API_URL', 'https://api.scaleway.ai/v1')
    }

# Configure logging
log_level = config.get('log_level', os.getenv('LOG_LEVEL', 'INFO'))
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import utilities
try:
    from utils.progress_utils import write_progress, check_kill_signal
except ImportError:
    # Fallback implementations
    def write_progress(step: int, current: int, total: int, message: str, details: str = ""):
        """Write progress information to a file."""
        try:
            progress_data = {
                'step': step,
                'current': current,
                'total': total,
                'progress': round((current / total * 100) if total > 0 else 0, 1),
                'message': message,
                'details': details,
                'timestamp': datetime.now().isoformat()
            }
            
            progress_file = os.path.join(config['output_dir'], f'step_{step}_progress.json')
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Could not write progress: {e}")

    def check_kill_signal(step: int) -> bool:
        """Check if user requested to kill this step."""
        try:
            kill_file = os.path.join(config['output_dir'], f'step_{step}_kill.flag')
            if os.path.exists(kill_file):
                logger.info("Kill signal detected, stopping execution")
                return True
            return False
        except:
            return False

# Ensure directories exist
os.makedirs(config['output_dir'], exist_ok=True)

def load_dfd_data(filepath: str) -> Dict[str, Any]:
    """Load DFD data from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle nested structure
        if 'dfd' in data:
            logger.info("Found nested DFD structure, extracting 'dfd' content")
            return data['dfd']
        
        return data
    except FileNotFoundError:
        logger.error(f"DFD file not found at '{filepath}'")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from '{filepath}': {e}")
        raise

def main():
    """Main execution function."""
    logger.info("=== Starting DFD to Threats Analysis ===")
    
    # Initialize progress
    write_progress(3, 0, 100, "Initializing threat analysis", "Loading components")
    
    try:
        # Check for modular service availability
        use_modular = True
        try:
            threat_service = ThreatGenerationService(config)
            logger.info("Using modular threat generation service")
        except (ImportError, Exception) as e:
            logger.warning(f"Modular services not available: {e}")
            logger.info("Falling back to built-in implementation")
            use_modular = False
        
        # Load DFD data
        write_progress(3, 10, 100, "Loading DFD data", "Reading component definitions")
        
        # Use dfd_input_path which now maps to dfd_output_path from step 2
        dfd_path = config.get('dfd_input_path', './output/dfd_components.json')
        
        logger.info(f"Loading DFD data from: {dfd_path}")
        dfd_data = load_dfd_data(dfd_path)
        
        # Log DFD info
        component_count = (
            len(dfd_data.get('external_entities', [])) +
            len(dfd_data.get('processes', [])) +
            len(dfd_data.get('assets', [])) +
            len(dfd_data.get('data_stores', [])) +
            len(dfd_data.get('data_flows', []))
        )
        
        logger.info(f"Loaded DFD with {component_count} components")
        logger.info(f"Project: {dfd_data.get('project_name', 'Unknown')}")
        logger.info(f"Industry: {dfd_data.get('industry_context', 'Unknown')}")
        
        write_progress(3, 20, 100, "Components loaded", f"Found {component_count} components")
        
        # Check for kill signal
        if check_kill_signal(3):
            write_progress(3, 100, 100, "Cancelled", "Process stopped by user")
            return 1
        
        # Generate threats
        write_progress(3, 30, 100, "Generating threats", "Analyzing components")
        
        if use_modular:
            # Use modular service
            result = threat_service.generate_threats_from_dfd(dfd_data)
        else:
            # Fallback to simple implementation
            logger.info("Using simplified threat generation")
            
            # Simple threat generation logic
            threats = []
            components = []
            
            # Extract all components
            for entity in dfd_data.get('external_entities', []):
                components.append({'name': entity, 'type': 'External Entity'})
            for process in dfd_data.get('processes', []):
                components.append({'name': process, 'type': 'Process'})
            for store in dfd_data.get('assets', []) + dfd_data.get('data_stores', []):
                components.append({'name': store, 'type': 'Data Store'})
            for flow in dfd_data.get('data_flows', []):
                if isinstance(flow, dict):
                    name = f"{flow.get('source', 'Unknown')} → {flow.get('destination', 'Unknown')}"
                    components.append({'name': name, 'type': 'Data Flow', 'details': flow})
            
            # Generate simple threats for each component
            for i, comp in enumerate(components):
                write_progress(3, 30 + int((i / len(components)) * 50), 100, 
                             f"Analyzing component {i+1}/{len(components)}", comp['name'])
                
                # Check for kill signal
                if check_kill_signal(3):
                    write_progress(3, 100, 100, "Cancelled", "Process stopped by user")
                    return 1
                
                # Simple STRIDE-based threat
                if comp['type'] == 'External Entity':
                    threats.append({
                        'component_name': comp['name'],
                        'stride_category': 'S',
                        'threat_description': f'An attacker could impersonate {comp["name"]} to gain unauthorized access.',
                        'mitigation_suggestion': 'Implement strong authentication mechanisms.',
                        'impact': 'High',
                        'likelihood': 'Medium',
                        'risk_score': 'High',
                        'references': ['OWASP A07:2021']
                    })
                elif comp['type'] == 'Data Store':
                    threats.append({
                        'component_name': comp['name'],
                        'stride_category': 'I',
                        'threat_description': f'Unauthorized access to {comp["name"]} could expose sensitive data.',
                        'mitigation_suggestion': 'Implement encryption at rest and access controls.',
                        'impact': 'Critical',
                        'likelihood': 'Medium',
                        'risk_score': 'Critical',
                        'references': ['OWASP A01:2021']
                    })
            
            result = {
                'threats': threats,
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'total_threats': len(threats),
                    'total_components': len(components),
                    'generation_method': 'Simplified',
                    'dfd_structure': {
                        'project_name': dfd_data.get('project_name', 'Unknown'),
                        'industry_context': dfd_data.get('industry_context', 'Unknown')
                    }
                }
            }
        
        if not result or not result.get('threats'):
            logger.error("No threats were generated!")
            write_progress(3, 100, 100, "Failed", "No threats generated")
            return 1
        
        # Save results
        write_progress(3, 90, 100, "Saving results", config['threats_output_path'])
        
        with open(config['threats_output_path'], 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to '{config['threats_output_path']}'")
        write_progress(3, 100, 100, "Complete", f"Generated {len(result['threats'])} threats")
        
        # Print summary
        print(f"\n=== Threat Analysis Summary ===")
        print(f"Total threats identified: {len(result['threats'])}")
        print(f"Analysis method: {result['metadata'].get('generation_method', 'Unknown')}")
        
        # Clean up progress file
        try:
            progress_file = os.path.join(config['output_dir'], 'step_3_progress.json')
            if os.path.exists(progress_file):
                os.remove(progress_file)
        except:
            pass
        
        return 0
        
    except Exception as e:
        logger.error(f"Threat analysis failed: {e}")
        if config.get('debug_mode', False):
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
        write_progress(3, 100, 100, "Failed", str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())