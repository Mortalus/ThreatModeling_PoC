#!/usr/bin/env python3
"""
DFD to Threats Generator Script - Modularized Version
Uses modular services for threat generation from DFD components.
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config
from services.threat_generation_service import ThreatGenerationService
from utils.logging_utils import logger, setup_logging

# Get configuration
config = Config.get_config()

# Additional threat-specific configuration
threat_config = {
    **config,
    'min_risk_score': int(os.getenv('MIN_RISK_SCORE', '3')),
    'max_components_to_analyze': int(os.getenv('MAX_COMPONENTS_TO_ANALYZE', '20')),
    'similarity_threshold': float(os.getenv('SIMILARITY_THRESHOLD', '0.70')),
}

# Configure logging
setup_logging()

# Ensure directories exist
os.makedirs(config['output_dir'], exist_ok=True)

def write_progress(step: int, current: int, total: int, message: str, details: str = ""):
    """Write progress information to a file that the frontend can read."""
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

def print_summary(threats_count: int, risk_breakdown: Dict[str, int], config: Dict):
    """Print comprehensive summary."""
    print(f"\n=== Realistic Threat Analysis Summary ===")
    print(f"Total realistic threats identified: {threats_count}")
    print(f"Critical threats: {risk_breakdown.get('Critical', 0)}")
    print(f"High threats: {risk_breakdown.get('High', 0)}")
    print(f"Medium threats: {risk_breakdown.get('Medium', 0)}")
    print(f"Low threats: {risk_breakdown.get('Low', 0)}")
    print(f"Analysis method: {'LLM-based' if config.get('llm_provider') else 'Rule-based'}")

def main():
    """Main execution function."""
    logger.info("=== Starting Threat Modeling Analysis ===")
    
    # Initialize progress
    write_progress(3, 0, 100, "Initializing threat analysis", "Loading components")
    
    try:
        # Initialize service
        threat_service = ThreatGenerationService(threat_config)
        
        # Load DFD data
        write_progress(3, 10, 100, "Loading DFD data", "Reading component definitions")
        
        dfd_path = threat_config.get('dfd_input_path') or os.path.join(config['output_dir'], 'dfd_components.json')
        dfd_data = load_dfd_data(dfd_path)
        
        write_progress(3, 20, 100, "Components loaded", "Starting threat analysis")
        
        if check_kill_signal(3):
            write_progress(3, 100, 100, "Analysis cancelled", "User requested stop")
            return 1
        
        # Generate threats
        result = threat_service.generate_threats_from_dfd(dfd_data)
        
        if not result.get('threats'):
            logger.error("No threats were generated!")
            write_progress(3, 100, 100, "Failed", "No threats generated")
            return 1
        
        # Validate output structure
        for i, threat in enumerate(result['threats']):
            if not isinstance(threat, dict):
                logger.error(f"Invalid threat structure at index {i}")
                return 1
            
            required_fields = ['component_name', 'stride_category', 'threat_description', 
                              'mitigation_suggestion', 'impact', 'likelihood']
            for field in required_fields:
                if field not in threat:
                    logger.error(f"Missing required field '{field}' in threat {i}")
                    return 1
        
        logger.info("Output validation successful")
        
        # Save results
        write_progress(3, 98, 100, "Saving results", config.get('threats_output_path', ''))
        
        output_path = threat_config.get('threats_output_path') or os.path.join(config['output_dir'], 'identified_threats.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to '{output_path}'")
        write_progress(3, 100, 100, "Complete", f"Generated {len(result['threats'])} realistic threats")
        
        # Print summary
        print_summary(
            len(result['threats']), 
            result['metadata']['risk_breakdown'],
            threat_config
        )
        
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
        write_progress(3, 100, 100, "Failed", str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())