#!/usr/bin/env python3
"""
LLM Threat Modeling Pipeline
============================
Automated pipeline for converting extracted document information into 
high-quality threat models using STRIDE methodology.

Pipeline Steps:
1. info_to_dfds.py - Convert extracted JSON to DFD components
2. dfd_to_threats.py - Apply STRIDE analysis with LLM + web search + Qdrant
3. improve_threat_quality.py - Refine and enrich threat data
"""

import json
import subprocess
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'pipeline_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ThreatModelingPipeline:
    """Main pipeline orchestrator for threat modeling workflow."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize pipeline with optional configuration."""
        self.config = self._load_config(config_path) if config_path else {}
        self.working_dir = Path(self.config.get('working_dir', './pipeline_output'))
        self.working_dir.mkdir(exist_ok=True)
        
        # Script paths
        self.scripts = {
            'info_to_dfds': self.config.get('info_to_dfds_path', './info_to_dfds.py'),
            'dfd_to_threats': self.config.get('dfd_to_threats_path', './dfd_to_threats.py'),
            'improve_threat_quality': self.config.get('improve_threat_quality_path', './improve_threat_quality.py')
        }
        
        # Validate scripts exist
        self._validate_scripts()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _validate_scripts(self):
        """Ensure all required scripts exist."""
        for name, path in self.scripts.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"Required script not found: {name} at {path}")
    
    def _save_intermediate(self, data: Dict[str, Any], step_name: str) -> str:
        """Save intermediate results for debugging and tracking."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.working_dir / f"{step_name}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {step_name} output to {filename}")
        return str(filename)
    
    def run_step(self, script_name: str, input_file: str, output_file: str, 
                 additional_args: list = None) -> bool:
        """Execute a pipeline step and handle errors."""
        script_path = self.scripts[script_name]
        cmd = [sys.executable, script_path, input_file, output_file]
        
        if additional_args:
            cmd.extend(additional_args)
        
        logger.info(f"Running {script_name}: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"{script_name} completed successfully")
            if result.stdout:
                logger.debug(f"Output: {result.stdout}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"{script_name} failed with exit code {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
            return False
    
    def step1_info_to_dfds(self, input_json: str) -> Optional[str]:
        """
        Step 1: Convert extracted information to DFD components.
        
        Input: JSON with extracted document information
        Output: JSON with DFD components (entities, assets, processes, flows)
        """
        logger.info("=== Step 1: Converting info to DFD components ===")
        
        output_file = self.working_dir / "dfd_output.json"
        
        if self.run_step('info_to_dfds', input_json, str(output_file)):
            # Validate output structure
            try:
                with open(output_file, 'r') as f:
                    dfd_data = json.load(f)
                
                required_keys = ['project_name', 'external_entities', 'assets', 
                               'processes', 'data_flows']
                missing = [k for k in required_keys if k not in dfd_data]
                
                if missing:
                    logger.warning(f"DFD output missing keys: {missing}")
                else:
                    logger.info("DFD structure validated successfully")
                
                self._save_intermediate(dfd_data, "step1_dfd")
                return str(output_file)
                
            except Exception as e:
                logger.error(f"Failed to validate DFD output: {e}")
                return None
        
        return None
    
    def step2_dfd_to_threats(self, dfd_json: str) -> Optional[str]:
        """
        Step 2: Apply STRIDE analysis to generate threats.
        
        Uses LLM with web search and Qdrant knowledge base.
        Input: DFD JSON from step 1
        Output: JSON with STRIDE-based threats
        """
        logger.info("=== Step 2: Generating threats with STRIDE ===")
        
        output_file = self.working_dir / "threats_output.json"
        
        # Additional args for Qdrant connection if configured
        additional_args = []
        if self.config.get('qdrant_url'):
            additional_args.extend(['--qdrant-url', self.config['qdrant_url']])
        if self.config.get('qdrant_collection'):
            additional_args.extend(['--collection', self.config['qdrant_collection']])
        
        if self.run_step('dfd_to_threats', dfd_json, str(output_file), additional_args):
            try:
                with open(output_file, 'r') as f:
                    threats_data = json.load(f)
                
                threat_count = len(threats_data.get('threats', []))
                logger.info(f"Generated {threat_count} threats")
                
                # Log threat distribution by STRIDE category
                stride_counts = {}
                for threat in threats_data.get('threats', []):
                    category = threat.get('stride_category', 'Unknown')
                    stride_counts[category] = stride_counts.get(category, 0) + 1
                
                logger.info(f"STRIDE distribution: {stride_counts}")
                
                self._save_intermediate(threats_data, "step2_threats")
                return str(output_file)
                
            except Exception as e:
                logger.error(f"Failed to process threats output: {e}")
                return None
        
        return None
    
    def step3_improve_threat_quality(self, threats_json: str, dfd_json: str) -> Optional[str]:
        """
        Step 3: Refine and enrich threat data.
        
        - Deduplicates similar threats
        - Standardizes component names
        - Suppresses irrelevant threats
        - Adds business risk context
        
        Input: Threats JSON from step 2, DFD JSON from step 1
        Output: Enhanced threats JSON with summary
        """
        logger.info("=== Step 3: Improving threat quality ===")
        
        output_file = self.working_dir / "enhanced_threats_output.json"
        summary_file = self.working_dir / "threat_summary.json"
        
        # Pass both threats and original DFD data
        additional_args = ['--dfd-file', dfd_json, '--summary-file', str(summary_file)]
        
        if self.run_step('improve_threat_quality', threats_json, str(output_file), additional_args):
            try:
                # Load and log results
                with open(output_file, 'r') as f:
                    enhanced_threats = json.load(f)
                
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
                
                logger.info(f"Enhanced threats count: {len(enhanced_threats.get('threats', []))}")
                logger.info(f"Summary: {summary}")
                
                self._save_intermediate(enhanced_threats, "step3_enhanced_threats")
                self._save_intermediate(summary, "step3_summary")
                
                return str(output_file)
                
            except Exception as e:
                logger.error(f"Failed to process enhanced threats: {e}")
                return None
        
        return None
    
    def run_pipeline(self, input_json: str) -> Dict[str, Any]:
        """
        Execute the complete threat modeling pipeline.
        
        Args:
            input_json: Path to initial extracted information JSON
            
        Returns:
            Dictionary with pipeline results and file paths
        """
        logger.info(f"Starting threat modeling pipeline with input: {input_json}")
        start_time = datetime.now()
        
        results = {
            'status': 'failed',
            'start_time': start_time.isoformat(),
            'steps': {}
        }
        
        try:
            # Step 1: Convert to DFD
            dfd_output = self.step1_info_to_dfds(input_json)
            results['steps']['info_to_dfds'] = {
                'status': 'completed' if dfd_output else 'failed',
                'output': dfd_output
            }
            
            if not dfd_output:
                logger.error("Pipeline failed at Step 1")
                return results
            
            # Step 2: Generate threats
            threats_output = self.step2_dfd_to_threats(dfd_output)
            results['steps']['dfd_to_threats'] = {
                'status': 'completed' if threats_output else 'failed',
                'output': threats_output
            }
            
            if not threats_output:
                logger.error("Pipeline failed at Step 2")
                return results
            
            # Step 3: Improve threat quality
            enhanced_output = self.step3_improve_threat_quality(threats_output, dfd_output)
            results['steps']['improve_threat_quality'] = {
                'status': 'completed' if enhanced_output else 'failed',
                'output': enhanced_output
            }
            
            if enhanced_output:
                results['status'] = 'completed'
                results['final_output'] = enhanced_output
            else:
                logger.error("Pipeline failed at Step 3")
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            results['error'] = str(e)
        
        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            results['end_time'] = end_time.isoformat()
            results['duration_seconds'] = duration
            
            # Save pipeline results
            results_file = self._save_intermediate(results, "pipeline_results")
            results['results_file'] = results_file
            
            logger.info(f"Pipeline completed in {duration:.2f} seconds")
            logger.info(f"Final status: {results['status']}")
        
        return results


def main():
    """Main entry point for the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description='LLM Threat Modeling Pipeline')
    parser.add_argument('input_json', help='Path to input JSON with extracted information')
    parser.add_argument('--config', help='Path to pipeline configuration JSON')
    parser.add_argument('--output-dir', help='Directory for pipeline outputs')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = ThreatModelingPipeline(config_path=args.config)
    
    if args.output_dir:
        pipeline.working_dir = Path(args.output_dir)
        pipeline.working_dir.mkdir(exist_ok=True)
    
    # Run pipeline
    results = pipeline.run_pipeline(args.input_json)
    
    # Print summary
    print("\n=== Pipeline Summary ===")
    print(f"Status: {results['status']}")
    print(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")
    
    if results['status'] == 'completed':
        print(f"Final output: {results.get('final_output')}")
        print(f"Results saved to: {results.get('results_file')}")
    else:
        print("Pipeline failed. Check logs for details.")
        if 'error' in results:
            print(f"Error: {results['error']}")
    
    # Exit with appropriate code
    sys.exit(0 if results['status'] == 'completed' else 1)


if __name__ == '__main__':
    main()