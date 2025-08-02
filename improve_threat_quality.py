#!/usr/bin/env python3
"""
Threat Quality Improvement Script - Modularized Version
Uses modular services for threat refinement and enrichment.
"""
import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config
from services.threat_quality_improvement_service import ThreatQualityImprovementService
from utils.logging_utils import logger, setup_logging
from utils.progress_utils import write_progress, check_kill_signal, cleanup_progress_file

# Get configuration
config = Config.get_config()

# Additional threat quality specific configuration
quality_config = {
    **config,
    'controls_input_path': os.getenv('CONTROLS_INPUT_PATH', ''),
    'client_industry': os.getenv('CLIENT_INDUSTRY', 'Generic'),
    'api_timeout': int(os.getenv('API_TIMEOUT', '30')),
}

# Configure logging
setup_logging()

# Ensure directories exist
Config.ensure_directories(config['output_dir'])

def load_json_file(file_path: str, default: Any = None) -> Any:
    """Load JSON file with error handling."""
    try:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Successfully loaded {file_path}")
            return data
        else:
            logger.warning(f"File not found: {file_path}")
            return default
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        if default is not None:
            return default
        raise
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        if default is not None:
            return default
        raise

def load_controls(file_path: str) -> Dict[str, Any]:
    """Load security controls configuration."""
    default_controls = {
        "https_enabled": False,
        "tls_version": "1.2",
        "mtls_enabled": False,
        "secrets_manager": False,
        "waf_enabled": False,
        "rate_limiting": False,
        "centralized_logging": False
    }
    
    if not file_path:
        file_path = os.path.join(config['output_dir'], "controls.json")
    
    return load_json_file(file_path, default_controls)

async def main():
    """Main execution function."""
    logger.info("=== Starting Threat Quality Improvement ===")
    write_progress(4, 0, 100, "Starting threat refinement", "Initializing pipeline")
    
    try:
        # Initialize service
        improvement_service = ThreatQualityImprovementService(quality_config)
        
        # Load input data
        logger.info("Loading input data...")
        write_progress(4, 2, 100, "Loading data", "Reading threat and DFD files")
        
        # Load threats
        threats_path = quality_config.get('threats_input_path') or os.path.join(config['output_dir'], 'identified_threats.json')
        threats_data = load_json_file(threats_path, {"threats": []})
        threats = threats_data.get("threats", [])
        
        if not threats:
            raise ValueError(f"No threats found in {threats_path}")
        
        # Load DFD data
        dfd_path = quality_config.get('dfd_input_path') or os.path.join(config['output_dir'], 'dfd_components.json')
        dfd_data = load_json_file(dfd_path, {})
        
        # Handle nested structure
        if 'dfd' in dfd_data:
            dfd_data = dfd_data['dfd']
        
        # Load controls
        controls = load_controls(quality_config.get('controls_input_path'))
        
        logger.info(f"Loaded {len(threats)} initial threats")
        write_progress(4, 5, 100, "Data loaded", f"Found {len(threats)} threats to refine")
        
        if check_kill_signal(4):
            return False
        
        # Run threat improvement
        result = await improvement_service.improve_threats(threats, dfd_data, controls)
        
        if check_kill_signal(4):
            return False
        
        # Save results
        write_progress(4, 95, 100, "Saving results", "Writing refined threats")
        
        output_path = quality_config.get('refined_threats_output_path') or \
                     os.path.join(config['output_dir'], 'refined_threats.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved refined threats to: {output_path}")
        
        # Save summary report
        summary_path = os.path.join(config['output_dir'], "refinement_summary.json")
        summary = {
            "statistics": result['metadata']['statistics'],
            "risk_distribution": result['metadata']['risk_distribution'],
            "suppression_reasons": {
                "controls_applied": result['metadata']['statistics']['suppressed_count'],
                "threats_deduplicated": result['metadata']['statistics']['deduplicated_count']
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Saved refinement summary to: {summary_path}")
        
        # Log statistics
        stats = result['metadata']['statistics']
        logger.info("=== Processing Statistics ===")
        logger.info(f"Original threats: {stats['original_count']}")
        logger.info(f"Suppressed threats: {stats['suppressed_count']}")
        logger.info(f"Deduplicated threats: {stats['deduplicated_count']}")
        logger.info(f"Final threats: {stats['final_count']}")
        logger.info("=== Risk Distribution ===")
        risk_dist = result['metadata']['risk_distribution']
        logger.info(f"Critical: {risk_dist['critical']}")
        logger.info(f"High: {risk_dist['high']}")
        logger.info(f"Medium: {risk_dist['medium']}")
        logger.info(f"Low: {risk_dist['low']}")
        
        write_progress(4, 100, 100, "Complete", f"Refined {len(result['threats'])} threats")
        cleanup_progress_file(4)
        
        return True
        
    except Exception as e:
        logger.error(f"Threat refinement failed: {e}")
        write_progress(4, 100, 100, "Failed", str(e))
        return False

def run_threat_quality_improvement():
    """Synchronous wrapper for running the threat quality improvement."""
    try:
        # Handle different async environments
        try:
            loop = asyncio.get_running_loop()
            # If we get here, we're in an async context
            try:
                import nest_asyncio
                nest_asyncio.apply()
                success = loop.run_until_complete(main())
            except ImportError:
                # Fallback: create a new loop in a thread
                import threading
                result = [None]
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result[0] = new_loop.run_until_complete(main())
                    new_loop.close()
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                success = result[0]
        except RuntimeError:
            # No existing event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(main())
            loop.close()
    except Exception as e:
        logger.error(f"Failed to run threat quality improvement: {e}")
        success = False
    
    return success

if __name__ == "__main__":
    logger.info("--- Starting Threat Quality Improvement Script ---")
    
    try:
        success = run_threat_quality_improvement()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        sys.exit(1)