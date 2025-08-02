"""
Main service for orchestrating threat generation from DFD.
"""
import os
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any
from models.threat_models import ThreatModel, ComponentAnalysis
from services.component_risk_analyzer import ComponentRiskAnalyzer
from services.stride_threat_generator import StrideThreatGenerator
from services.threat_deduplication_service import ThreatDeduplicationService

logger = logging.getLogger(__name__)

class ThreatGenerationService:
    """Main service for threat generation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_analyzer = ComponentRiskAnalyzer(
            min_risk_score=config.get('min_risk_score', 3)
        )
        self.threat_generator = StrideThreatGenerator(config)
        self.dedup_service = ThreatDeduplicationService(
            similarity_threshold=config.get('similarity_threshold', 0.70)
        )
    
    def generate_threats_from_dfd(self, dfd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate threats from DFD data."""
        logger.info("=== Starting Realistic Threat Modeling Analysis ===")
        
        # Extract and analyze components
        components = self.risk_analyzer.analyze_components(dfd_data)
        
        # Filter to only analyze high-risk components
        high_risk_components = [
            c for c in components 
            if self.risk_analyzer.should_analyze_component(c)
        ]
        
        # Limit total components to analyze
        max_components = self.config.get('max_components_to_analyze', 20)
        if len(high_risk_components) > max_components:
            logger.info(f"Limiting analysis to top {max_components} highest risk components")
            high_risk_components = high_risk_components[:max_components]
        
        logger.info(f"Total components: {len(components)}")
        logger.info(f"High-risk components to analyze: {len(high_risk_components)}")
        
        # Log component breakdown
        self._log_component_breakdown(components)
        
        # Generate threats for each component
        all_threats = []
        
        for i, component in enumerate(high_risk_components):
            logger.info(f"Analyzing component {i+1}/{len(high_risk_components)}: {component.name}")
            
            threats = self.threat_generator.generate_threats_for_component(component)
            all_threats.extend(threats)
            
            # Rate limiting for better quality if using LLM
            if self.config.get('llm_provider') and i < len(high_risk_components) - 1:
                time.sleep(1)
        
        logger.info(f"Generated {len(all_threats)} initial threats")
        
        # Deduplicate threats
        all_threats = self.dedup_service.deduplicate_threats(all_threats)
        logger.info(f"After deduplication: {len(all_threats)} threats")
        
        # Filter low-quality threats
        all_threats = self.dedup_service.filter_quality_threats(all_threats)
        logger.info(f"After quality filtering: {len(all_threats)} threats")
        
        # Sort by risk score
        risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        all_threats.sort(key=lambda t: risk_order.get(t.risk_score, 0), reverse=True)
        
        # Create output structure
        return self._create_output(all_threats, dfd_data, components, high_risk_components)
    
    def _log_component_breakdown(self, components: List[ComponentAnalysis]):
        """Log component type breakdown."""
        component_types = {}
        for comp in components:
            comp_type = comp.type
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
        
        logger.info("Component breakdown:")
        for comp_type, count in component_types.items():
            logger.info(f"  - {comp_type}: {count}")
    
    def _create_output(self, threats: List[ThreatModel], dfd_data: Dict, 
                      all_components: List[ComponentAnalysis], 
                      analyzed_components: List[ComponentAnalysis]) -> Dict[str, Any]:
        """Create comprehensive output structure."""
        # Convert threats to dictionaries
        threat_dicts = [threat.to_dict() for threat in threats]
        
        # Calculate risk breakdown
        risk_breakdown = {
            "Critical": sum(1 for t in threats if t.risk_score == 'Critical'),
            "High": sum(1 for t in threats if t.risk_score == 'High'),
            "Medium": sum(1 for t in threats if t.risk_score == 'Medium'),
            "Low": sum(1 for t in threats if t.risk_score == 'Low')
        }
        
        return {
            "threats": threat_dicts,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_dfd": os.path.basename(self.config.get('dfd_input_path', '')),
                "llm_provider": self.config.get('llm_provider', 'unknown'),
                "llm_model": self.config.get('llm_model', 'unknown'),
                "total_threats": len(threats),
                "total_components": len(all_components),
                "components_analyzed": len(analyzed_components),
                "generation_method": "LLM" if self.threat_generator.llm_service.is_available() else "Rule-based",
                "analysis_approach": "Risk-based with STRIDE filtering",
                "min_risk_score": self.config.get('min_risk_score', 3),
                "max_components_analyzed": self.config.get('max_components_to_analyze', 20),
                "risk_breakdown": risk_breakdown,
                "dfd_structure": {
                    "project_name": dfd_data.get('project_name', 'Unknown'),
                    "industry_context": dfd_data.get('industry_context', 'Unknown')
                }
            }
        }