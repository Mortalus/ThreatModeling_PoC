#!/usr/bin/env python3
"""
DFD to Threats Generator Script - Enhanced with Async Processing and Detailed Progress Display
Features:
- Async/sync processing modes
- Detailed LLM call logging with percentages
- Enhanced error handling without silent fallbacks
- Debug mode configuration
- Comprehensive progress tracking
"""
import os
import sys
import json
import logging
import time
import asyncio
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
    """Load DFD data from file with enhanced error handling."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle nested structure
        if 'dfd' in data:
            progress_logger.info("Found nested DFD structure, extracting 'dfd' content")
            return data['dfd']
        
        return data
    except FileNotFoundError:
        error_msg = f"DFD file not found at '{filepath}'"
        progress_logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"Error decoding JSON from '{filepath}': {e}"
        progress_logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error loading DFD data: {e}"
        progress_logger.error(error_msg)
        raise

def validate_configuration(config: Dict[str, Any]) -> None:
    """Validate configuration and log important settings."""
    progress_logger.info("🔧 Validating configuration...")
    
    # Log key configuration settings
    progress_logger.info(f"   LLM Provider: {config['llm_provider']}")
    progress_logger.info(f"   LLM Model: {config['llm_model']}")
    progress_logger.info(f"   Async Processing: {config.get('enable_async_processing', True)}")
    progress_logger.info(f"   Max Concurrent Calls: {config.get('max_concurrent_calls', 5)}")
    progress_logger.info(f"   Debug Mode: {config.get('debug_mode', False)}")
    progress_logger.info(f"   Force Rule-Based: {config.get('force_rule_based', False)}")
    progress_logger.info(f"   Detailed Logging: {config.get('detailed_llm_logging', True)}")
    
    # Validate async configuration
    validation_errors = Config.validate_async_config(config)
    if validation_errors:
        for error in validation_errors:
            progress_logger.error(f"❌ Configuration error: {error}")
        raise ValueError(f"Configuration validation failed: {', '.join(validation_errors)}")
    
    # Check API key if using Scaleway
    if config['llm_provider'] == 'scaleway' and not config.get('scw_secret_key'):
        if not config.get('debug_mode', False) and not config.get('force_rule_based', False):
            raise ValueError("SCW_SECRET_KEY required for Scaleway provider")
        else:
            progress_logger.warning("⚠️ No Scaleway API key found - debug/rule-based mode enabled")
    
    progress_logger.info("✅ Configuration validation successful")

def log_processing_mode(config: Dict[str, Any]) -> None:
    """Log the selected processing mode and its implications."""
    if config.get('force_rule_based', False):
        progress_logger.info("🔧 RULE-BASED MODE: Using rule-based extraction only")
    elif config.get('debug_mode', False):
        progress_logger.info("🐛 DEBUG MODE: LLM with rule-based fallback enabled")
    else:
        progress_logger.info("🚀 PRODUCTION MODE: LLM-only processing (no fallbacks)")
    
    if config.get('enable_async_processing', True):
        max_concurrent = config.get('max_concurrent_calls', 5)
        progress_logger.info(f"⚡ ASYNC MODE: Up to {max_concurrent} concurrent LLM calls")
    else:
        progress_logger.info("🔄 SYNC MODE: Sequential processing")

def calculate_total_components(dfd_data: Dict[str, Any]) -> int:
    """Calculate total number of components for progress tracking."""
    return (
        len(dfd_data.get('external_entities', [])) +
        len(dfd_data.get('processes', [])) +
        len(dfd_data.get('assets', [])) +
        len(dfd_data.get('data_flows', []))
    )

def print_summary(threats_count: int, risk_breakdown: Dict[str, int], config: Dict):
    """Print comprehensive summary with enhanced information."""
    if ProgressLogger:
        from utils.enhanced_progress import Colors
        print(f"\n{Colors.HEADER}=== Enhanced Threat Analysis Summary ==={Colors.ENDC}")
        print(f"Total realistic threats identified: {Colors.BOLD}{threats_count}{Colors.ENDC}")
        print(f"{Colors.FAIL}Critical threats: {risk_breakdown.get('Critical', 0)}{Colors.ENDC}")
        print(f"{Colors.WARNING}High threats: {risk_breakdown.get('High', 0)}{Colors.ENDC}")
        print(f"{Colors.CYAN}Medium threats: {risk_breakdown.get('Medium', 0)}{Colors.ENDC}")
        print(f"{Colors.GREEN}Low threats: {risk_breakdown.get('Low', 0)}{Colors.ENDC}")
        
        # Processing mode information
        processing_mode = "Async" if config.get('enable_async_processing', True) else "Sync"
        generation_method = "Rule-based" if config.get('force_rule_based', False) else "LLM"
        debug_mode = "Yes" if config.get('debug_mode', False) else "No"
        
        print(f"Processing mode: {Colors.BOLD}{processing_mode}{Colors.ENDC}")
        print(f"Generation method: {Colors.BOLD}{generation_method}{Colors.ENDC}")
        print(f"Debug mode: {Colors.BOLD}{debug_mode}{Colors.ENDC}")
        
        if config.get('enable_async_processing', True) and not config.get('force_rule_based', False):
            max_concurrent = config.get('max_concurrent_calls', 5)
            print(f"Max concurrent calls: {Colors.BOLD}{max_concurrent}{Colors.ENDC}")
    else:
        print(f"\n=== Enhanced Threat Analysis Summary ===")
        print(f"Total realistic threats identified: {threats_count}")
        print(f"Critical threats: {risk_breakdown.get('Critical', 0)}")
        print(f"High threats: {risk_breakdown.get('High', 0)}")
        print(f"Medium threats: {risk_breakdown.get('Medium', 0)}")
        print(f"Low threats: {risk_breakdown.get('Low', 0)}")
        
        processing_mode = "Async" if config.get('enable_async_processing', True) else "Sync"
        generation_method = "Rule-based" if config.get('force_rule_based', False) else "LLM"
        print(f"Processing mode: {processing_mode}")
        print(f"Generation method: {generation_method}")

def create_progress_callback(progress, total_components: int):
    """Create a progress callback function for threat generation."""
    def threat_progress_callback(current_component: int, total: int, component_name: str):
        # Map progress to 30-90% range
        prog = 30 + int((current_component / total) * 60)
        progress.update(prog, "Generating threats", f"Analyzing: {component_name[:30]}")
        
        # Check for kill signal
        if check_kill_signal(3):
            raise KeyboardInterrupt("User requested cancellation")
    
    return threat_progress_callback

def main():
    """Main execution function with enhanced error handling and progress tracking."""
    progress_logger.info("=== Starting Enhanced Threat Modeling Analysis ===")
    
    # Initialize progress tracker
    if ProgressTracker:
        progress = ProgressTracker(step=3, total_steps=100)
    else:
        # Fallback to write_progress
        def progress_update(current, message, details=""):
            write_progress(3, current, 100, message, details)
        progress = type('Progress', (), {
            'update': progress_update, 
            'complete': lambda m: None, 
            'fail': lambda e: None
        })()
    
    progress.update(0, "Initializing", "Loading threat analysis engine")
    
    start_time = time.time()
    
    try:
        # Validate configuration
        progress.update(5, "Validating config", "Checking settings and API keys")
        validate_configuration(threat_config)
        log_processing_mode(threat_config)
        
        # Initialize service
        progress.update(10, "Initializing service", "Setting up threat generation engine")
        threat_service = ThreatGenerationService(threat_config)
        
        # Load DFD data
        progress.update(15, "Loading DFD", "Reading component definitions")
        
        dfd_path = threat_config.get('dfd_input_path') or os.path.join(config['output_dir'], 'dfd_components.json')
        dfd_data = load_dfd_data(dfd_path)
        
        # Count components for progress tracking
        total_components = calculate_total_components(dfd_data)
        
        progress.update(20, "Components loaded", f"Found {total_components} components")
        progress_logger.info(f"Loaded {total_components} components from DFD")
        
        if check_kill_signal(3):
            progress.update(100, "Cancelled", "User requested stop")
            return 1
        
        # Generate threats with enhanced progress tracking
        progress.update(25, "Starting analysis", "Preparing threat generation")
        
        # Create progress callback for detailed tracking
        progress_callback = create_progress_callback(progress, total_components)
        
        # Set up detailed progress tracking in the service
        if hasattr(threat_service.threat_generator, 'set_progress_callback'):
            threat_service.threat_generator.set_progress_callback(progress_callback)
        
        # Execute threat generation (async or sync based on config)
        generation_start = time.time()
        
        if threat_config.get('enable_async_processing', True) and not threat_config.get('force_rule_based', False):
            progress_logger.info("⚡ Starting async threat generation")
            progress.update(30, "Async generation", "Starting concurrent threat analysis")
        else:
            progress_logger.info("🔄 Starting sync threat generation")
            progress.update(30, "Sync generation", "Starting sequential threat analysis")
        
        # Generate threats
        result = threat_service.generate_threats_from_dfd(dfd_data)
        
        generation_elapsed = time.time() - generation_start
        progress_logger.info(f"⏱️ Threat generation completed in {generation_elapsed:.1f} seconds")
        
        if not result or not result.get('threats'):
            error_msg = "No threats were generated!"
            progress_logger.error(error_msg)
            progress.fail(error_msg)
            return 1
        
        progress.update(90, "Validating results", "Checking threat quality")
        
        # Validate output structure
        threats = result.get('threats', [])
        for i, threat in enumerate(threats):
            if not isinstance(threat, dict):
                error_msg = f"Invalid threat structure at index {i}"
                progress_logger.error(error_msg)
                progress.fail(error_msg)
                return 1
            
            required_fields = ['component_name', 'stride_category', 'threat_description', 
                              'mitigation_suggestion', 'impact', 'likelihood']
            for field in required_fields:
                if field not in threat:
                    error_msg = f"Missing required field '{field}' in threat {i}"
                    progress_logger.error(error_msg)
                    progress.fail(error_msg)
                    return 1
        
        progress_logger.info("✅ Output validation successful")
        
        # Save results
        progress.update(95, "Saving results", "Writing to disk")
        
        output_path = threat_config.get('threats_output_path') or os.path.join(config['output_dir'], 'identified_threats.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        progress_logger.info(f"📁 Results saved to '{output_path}'")
        
        # Complete progress tracking
        total_elapsed = time.time() - start_time
        completion_message = f"Generated {len(threats)} threats in {total_elapsed:.1f}s"
        progress.complete(completion_message)
        
        # Print comprehensive summary
        print_summary(
            len(threats), 
            result['metadata']['risk_breakdown'],
            threat_config
        )
        
        # Log performance metrics
        metadata = result.get('metadata', {})
        progress_logger.info("📊 Performance Metrics:")
        progress_logger.info(f"   Total execution time: {total_elapsed:.1f}s")
        progress_logger.info(f"   Threat generation time: {generation_elapsed:.1f}s")
        progress_logger.info(f"   Components analyzed: {metadata.get('components_analyzed', 0)}")
        progress_logger.info(f"   Processing mode: {metadata.get('processing_mode', 'Unknown')}")
        progress_logger.info(f"   Generation method: {metadata.get('generation_method', 'Unknown')}")
        
        if threat_config.get('enable_async_processing', True):
            progress_logger.info(f"   Max concurrent calls: {metadata.get('max_concurrent_calls', 'N/A')}")
        
        return 0
        
    except KeyboardInterrupt:
        progress_logger.info("🛑 Process cancelled by user")
        if hasattr(progress, 'fail'):
            progress.fail("Cancelled by user")
        else:
            write_progress(3, 100, 100, "Cancelled", "Process stopped by user")
        return 1
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"Threat analysis failed after {elapsed:.1f}s: {e}"
        progress_logger.error(error_msg)
        
        if threat_config.get('verbose_error_reporting', True):
            import traceback
            progress_logger.error(f"Stack trace: {traceback.format_exc()}")
        
        if hasattr(progress, 'fail'):
            progress.fail(str(e))
        else:
            write_progress(3, 100, 100, "Failed", str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())