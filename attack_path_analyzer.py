#!/usr/bin/env python3
"""
Attack Path Analysis Script - Modularized Version
Uses modular services for attack path analysis.
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config
from services.attack_path_analyzer_service import AttackPathAnalyzerService
from utils.logging_utils import logger, setup_logging
from utils.progress_utils import write_progress, check_kill_signal, cleanup_progress_file

# Get configuration
config = Config.get_config()

# Configure logging
setup_logging()

# Ensure directories exist
Config.ensure_directories(config['output_dir'])

def load_data(config: dict) -> Tuple[List[Dict], Dict]:
    """Load refined threats and DFD data with validation."""
    try:
        # Load threats
        threats_path = config.get('refined_threats_path') or \
                      os.path.join(config['output_dir'], 'refined_threats.json')
        
        logger.info(f"Loading threats from: {threats_path}")
        write_progress(5, 5, 100, "Loading data", "Reading threat files")
        
        with open(threats_path, 'r', encoding='utf-8') as f:
            threats_data = json.load(f)
        threats = threats_data.get('threats', [])
        
        # Load DFD data
        dfd_path = config.get('dfd_path') or \
                  os.path.join(config['output_dir'], 'dfd_components.json')
        
        logger.info(f"Loading DFD from: {dfd_path}")
        write_progress(5, 10, 100, "Loading data", "Reading DFD components")
        
        with open(dfd_path, 'r', encoding='utf-8') as f:
            dfd_data = json.load(f)
        
        # Handle nested DFD structure
        if 'dfd' in dfd_data:
            dfd_data = dfd_data['dfd']
        
        # Validate data
        if not threats:
            raise ValueError("No threats found in refined threats file")
        if not any([dfd_data.get('external_entities'), dfd_data.get('processes'), 
                   dfd_data.get('assets')]):
            raise ValueError("No components found in DFD file")
        
        logger.info(f"Loaded {len(threats)} threats and DFD with {len(dfd_data.get('data_flows', []))} flows")
        write_progress(5, 15, 100, "Data loaded", f"Found {len(threats)} threats")
        return threats, dfd_data
        
    except FileNotFoundError as e:
        logger.error(f"Required file not found: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in input files: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise

def convert_to_dict(obj):
    """Convert dataclass objects to dictionaries recursively."""
    if hasattr(obj, '__dict__'):
        return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [convert_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_to_dict(v) for k, v in obj.items()}
    else:
        return obj

def print_summary(results):
    """Print analysis summary."""
    print("\n" + "="*60)
    print("ATTACK PATH ANALYSIS SUMMARY")
    print("="*60)
    print(f"Total attack paths identified: {len(results.attack_paths)}")
    print(f"Critical scenarios: {len(results.critical_scenarios)}")
    print(f"Defense priorities: {len(results.defense_priorities)}")
    print(f"Threat coverage: {results.threat_coverage.get('coverage_percentage', 0):.1f}%")
    
    if results.critical_scenarios:
        print("\n📊 Top Critical Scenarios:")
        for i, scenario in enumerate(results.critical_scenarios[:3], 1):
            print(f"  {i}. {scenario}")
    
    if results.defense_priorities:
        print("\n🛡️ Top Defense Priorities:")
        for i, priority in enumerate(results.defense_priorities[:5], 1):
            print(f"  {i}. {priority['recommendation']}")
            print(f"     Priority: {priority['priority']} | Impact: {priority['impact']}")
    
    if results.attack_paths:
        print("\n🎯 Most Critical Attack Path:")
        path = results.attack_paths[0]
        print(f"  Scenario: {path.scenario_name}")
        print(f"  Entry: {path.entry_point} → Target: {path.target_asset}")
        print(f"  Steps: {path.total_steps} | Feasibility: {path.path_feasibility}")
        print(f"  Impact: {path.combined_impact} | Time: {path.time_to_compromise}")
    
    print("\n✅ Analysis completed successfully!")

def main():
    """Main execution function."""
    logger.info("=== Starting Attack Path Analysis ===")
    write_progress(5, 0, 100, "Initializing", "Starting attack path analysis")
    
    try:
        # Initialize service
        analyzer_service = AttackPathAnalyzerService(config)
        
        # Load data
        threats, dfd_data = load_data(config)
        
        if check_kill_signal(5):
            write_progress(5, 100, 100, "Cancelled", "Analysis cancelled by user")
            return 1
        
        # Run analysis
        write_progress(5, 20, 100, "Analyzing", "Building attack paths")
        results = analyzer_service.analyze_attack_paths(threats, dfd_data)
        
        if check_kill_signal(5):
            write_progress(5, 100, 100, "Cancelled", "Analysis cancelled by user")
            return 1
        
        # Convert to dict for JSON serialization
        output_data = convert_to_dict(results)
        
        # Save results
        write_progress(5, 99, 100, "Saving results", config.get('attack_paths_output', ''))
        
        output_path = config.get('attack_paths_output') or \
                     os.path.join(config['output_dir'], 'attack_paths.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Analysis complete. Results saved to {output_path}")
        
        # Print summary
        print_summary(results)
        
        write_progress(5, 100, 100, "Complete", f"Found {len(results.attack_paths)} attack paths")
        cleanup_progress_file(5)
        
        return 0
        
    except Exception as e:
        logger.error(f"Attack path analysis failed: {e}")
        write_progress(5, 100, 100, "Failed", str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())