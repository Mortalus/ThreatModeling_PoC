#!/usr/bin/env python3
"""
DFD to Threats Generator Script - With Enhanced Progress Display
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config
from services.threat_generation_service import ThreatGenerationService
from utils.logging_utils import logger, setup_logging

# Import enhanced progress system
try:
    from utils.enhanced_progress import ProgressTracker, ProgressLogger, check_kill_signal
except ImportError:
    # Fallback to original if enhanced not available
    from utils.progress_utils import write_progress, check_kill_signal, cleanup_progress_file
    ProgressTracker = None
    ProgressLogger = None

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

# Use enhanced logger if available
if ProgressLogger:
    progress_logger = ProgressLogger("threat-gen")
else:
    progress_logger = logger

# Ensure directories exist
os.makedirs(config['output_dir'], exist_ok=True)

def load_dfd_data(filepath: str) -> Dict[str, Any]:
    """Load DFD data from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle nested structure
        if 'dfd' in data:
            progress_logger.info("Found nested DFD structure, extracting 'dfd' content")
            return data['dfd']
        
        return data
    except FileNotFoundError:
        progress_logger.error(f"DFD file not found at '{filepath}'")
        raise
    except json.JSONDecodeError as e:
        progress_logger.error(f"Error decoding JSON from '{filepath}': {e}")
        raise

def print_summary(threats_count: int, risk_breakdown: Dict[str, int], config: Dict):
    """Print comprehensive summary with color."""
    if ProgressLogger:
        from utils.enhanced_progress import Colors
        print(f"\n{Colors.HEADER}=== Realistic Threat Analysis Summary ==={Colors.ENDC}")
        print(f"Total realistic threats identified: {Colors.BOLD}{threats_count}{Colors.ENDC}")
        print(f"{Colors.FAIL}Critical threats: {risk_breakdown.get('Critical', 0)}{Colors.ENDC}")
        print(f"{Colors.WARNING}High threats: {risk_breakdown.get('High', 0)}{Colors.ENDC}")
        print(f"{Colors.CYAN}Medium threats: {risk_breakdown.get('Medium', 0)}{Colors.ENDC}")
        print(f"{Colors.GREEN}Low threats: {risk_breakdown.get('Low', 0)}{Colors.ENDC}")
        print(f"Analysis method: {Colors.BOLD}{'LLM-based' if config.get('llm_provider') else 'Rule-based'}{Colors.ENDC}")
    else:
        print(f"\n=== Realistic Threat Analysis Summary ===")
        print(f"Total realistic threats identified: {threats_count}")
        print(f"Critical threats: {risk_breakdown.get('Critical', 0)}")
        print(f"High threats: {risk_breakdown.get('High', 0)}")
        print(f"Medium threats: {risk_breakdown.get('Medium', 0)}")
        print(f"Low threats: {risk_breakdown.get('Low', 0)}")
        print(f"Analysis method: {'LLM-based' if config.get('llm_provider') else 'Rule-based'}")

def main():
    """Main execution function."""
    progress_logger.info("=== Starting Threat Modeling Analysis ===")
    
    # Initialize progress tracker
    if ProgressTracker:
        progress = ProgressTracker(step=3, total_steps=100)
    else:
        # Fallback to write_progress
        def progress_update(current, message, details=""):
            write_progress(3, current, 100, message, details)
        progress = type('Progress', (), {'update': progress_update, 'complete': lambda m: None, 'fail': lambda e: None})()
    
    progress.update(0, "Initializing", "Loading threat analysis engine")
    
    try:
        # Initialize service
        threat_service = ThreatGenerationService(threat_config)
        
        # Load DFD data
        progress.update(10, "Loading DFD", "Reading component definitions")
        
        dfd_path = threat_config.get('dfd_input_path') or os.path.join(config['output_dir'], 'dfd_components.json')
        dfd_data = load_dfd_data(dfd_path)
        
        # Count components for progress tracking
        total_components = (
            len(dfd_data.get('external_entities', [])) +
            len(dfd_data.get('processes', [])) +
            len(dfd_data.get('assets', [])) +
            len(dfd_data.get('data_flows', []))
        )
        
        progress.update(20, "Components loaded", f"Found {total_components} components")
        progress_logger.info(f"Loaded {total_components} components from DFD")
        
        if check_kill_signal(3):
            progress.update(100, "Cancelled", "User requested stop")
            return 1
        
        # Generate threats with detailed progress
        progress.update(30, "Analyzing components", "Calculating risk scores")
        
        # Create a custom progress callback
        def threat_progress_callback(current_component: int, total: int, component_name: str):
            prog = 30 + int((current_component / total) * 60)  # 30-90% range
            progress.update(prog, "Generating threats", f"Analyzing: {component_name[:30]}")
        
        # Monkey-patch the progress callback if possible
        original_method = threat_service.generate_threats_from_dfd
        
        def wrapped_generate(dfd_data):
            result = original_method(dfd_data)
            # Simulate progress during generation
            components = []
            for key in ['external_entities', 'processes', 'assets']:
                if key in dfd_data:
                    for idx, comp in enumerate(dfd_data[key]):
                        name = comp if isinstance(comp, str) else comp.get('name', 'Unknown')
                        threat_progress_callback(len(components), total_components, name)
                        components.append(comp)
                        
                        if check_kill_signal(3):
                            return None
            return result
        
        result = wrapped_generate(dfd_data)
        
        if not result or not result.get('threats'):
            progress_logger.error("No threats were generated!")
            progress.fail("No threats generated")
            return 1
        
        progress.update(90, "Validating results", "Checking threat quality")
        
        # Validate output structure
        for i, threat in enumerate(result['threats']):
            if not isinstance(threat, dict):
                progress_logger.error(f"Invalid threat structure at index {i}")
                progress.fail(f"Invalid threat structure at index {i}")
                return 1
            
            required_fields = ['component_name', 'stride_category', 'threat_description', 
                              'mitigation_suggestion', 'impact', 'likelihood']
            for field in required_fields:
                if field not in threat:
                    progress_logger.error(f"Missing required field '{field}' in threat {i}")
                    progress.fail(f"Missing field: {field}")
                    return 1
        
        progress_logger.success("Output validation successful")
        
        # Save results
        progress.update(98, "Saving results", "Writing to disk")
        
        output_path = threat_config.get('threats_output_path') or os.path.join(config['output_dir'], 'identified_threats.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        progress_logger.success(f"Results saved to '{output_path}'")
        progress.complete(f"Generated {len(result['threats'])} threats")
        
        # Print summary
        print_summary(
            len(result['threats']), 
            result['metadata']['risk_breakdown'],
            threat_config
        )
        
        return 0
        
    except Exception as e:
        progress_logger.error(f"Threat analysis failed: {e}")
        if hasattr(progress, 'fail'):
            progress.fail(str(e))
        else:
            write_progress(3, 100, 100, "Failed", str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())