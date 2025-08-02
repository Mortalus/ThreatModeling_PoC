"""
Service for generating threats using STRIDE methodology.
"""
import logging
from typing import List, Dict, Any, Optional
from models.threat_models import ThreatModel, DEFAULT_STRIDE_DEFINITIONS, MAX_THREATS_PER_COMPONENT
from services.llm_threat_service import LLMThreatService
from services.rule_based_threat_generator import RuleBasedThreatGenerator

logger = logging.getLogger(__name__)

class StrideThreatGenerator:
    """Generates threats using STRIDE methodology."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stride_definitions = self._load_stride_definitions()
        self.llm_service = LLMThreatService(config, self.stride_definitions)
        self.rule_generator = RuleBasedThreatGenerator(self.stride_definitions)
    
    def _load_stride_definitions(self) -> Dict[str, tuple]:
        """Load STRIDE definitions from file or use defaults."""
        import os
        import json
        
        stride_config_path = os.path.join(self.config.get('output_dir', './output'), "stride_config.json")
        if os.path.exists(stride_config_path):
            try:
                with open(stride_config_path, 'r', encoding='utf-8') as f:
                    custom_stride = json.load(f)
                logger.info(f"Loaded custom STRIDE definitions from '{stride_config_path}'")
                return {k: (v[0], v[1]) if isinstance(v, list) else v for k, v in custom_stride.items()}
            except Exception as e:
                logger.warning(f"Failed to load custom STRIDE definitions: {e}. Using defaults.")
        
        return DEFAULT_STRIDE_DEFINITIONS
    
    def generate_threats_for_component(self, component: 'ComponentAnalysis') -> List[ThreatModel]:
        """Generate threats for a single component."""
        component_name = component.name
        component_type = component.type
        
        logger.info(f"Analyzing component: {component_name} ({component_type})")
        
        # Get applicable STRIDE categories and max threats
        applicable_categories = component.applicable_stride
        max_threats = MAX_THREATS_PER_COMPONENT.get(component_type, 2)
        
        logger.info(f"  Applicable STRIDE categories: {applicable_categories}")
        
        all_threats = []
        
        # Analyze only applicable categories
        for cat_letter in applicable_categories:
            if cat_letter not in self.stride_definitions:
                continue
                
            cat_name, cat_def = self.stride_definitions[cat_letter]
            logger.info(f"  Analyzing {cat_name}")
            
            try:
                # Try LLM first if available
                if self.llm_service.is_available():
                    threats = self.llm_service.generate_threats(
                        component, cat_letter, cat_name, cat_def
                    )
                else:
                    # Fallback to rule-based
                    threats = self.rule_generator.generate_threats(
                        component, cat_letter
                    )
                
                # Limit threats per category to 1 for focus
                threats = threats[:1]
                all_threats.extend(threats)
                
            except Exception as e:
                logger.warning(f"    Error analyzing {cat_name}: {e}")
                continue
        
        # Limit total threats per component
        all_threats = all_threats[:max_threats]
        
        # Assign threat IDs if not present
        for i, threat in enumerate(all_threats):
            if not threat.threat_id:
                threat.threat_id = f"T{component_name[:3].upper()}{i:03d}"
        
        logger.info(f"  Generated {len(all_threats)} threat(s)")
        return all_threats
    
    def calculate_risk_score(self, impact: str, likelihood: str) -> str:
        """Calculate risk score based on impact and likelihood."""
        if impact == "High" and likelihood in ["Medium", "High"]:
            return "Critical"
        elif (impact == "High" and likelihood == "Low") or (impact == "Medium" and likelihood == "High"):
            return "High"
        elif (impact == "Medium" and likelihood in ["Medium", "Low"]) or (impact == "Low" and likelihood == "High"):
            return "Medium"
        else:
            return "Low"