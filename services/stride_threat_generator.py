"""
STRIDE-based threat generator with LLM integration.
Enhanced with async support and detailed progress tracking.
"""
import logging
import asyncio
from typing import List, Dict, Any, Tuple
from models.threat_models import ThreatModel, ComponentAnalysis
from services.llm_threat_service import LLMThreatService

logger = logging.getLogger(__name__)

class StrideThreatGenerator:
    """STRIDE-based threat generator with async support."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stride_definitions = {
            'S': ('Spoofing', 'Impersonating someone or something else'),
            'T': ('Tampering', 'Modifying data or code'),
            'R': ('Repudiation', 'Claiming to have not performed an action'),
            'I': ('Information Disclosure', 'Exposing information to unauthorized individuals'),
            'D': ('Denial of Service', 'Denying or degrading service to valid users'),
            'E': ('Elevation of Privilege', 'Gaining capabilities without proper authorization')
        }
        
        # Component type to STRIDE category mappings
        self.component_stride_mappings = {
            'External Entity': ['S', 'R'],
            'Process': ['S', 'T', 'R', 'I', 'D', 'E'],
            'Data Store': ['T', 'R', 'I', 'D'],
            'Data Flow': ['T', 'I', 'D'],
            'Trust Boundary': ['S', 'T', 'E'],
            'Asset': ['T', 'I', 'D'],
            'Database': ['T', 'R', 'I', 'D'],
            'API': ['S', 'T', 'R', 'I', 'D', 'E'],
            'Service': ['S', 'T', 'R', 'I', 'D', 'E'],
            'Unknown': ['S', 'T', 'R', 'I', 'D', 'E']  # Default for unknown types
        }
        
        self.llm_service = LLMThreatService(config, self.stride_definitions)
    
    def set_expected_calls(self, count: int):
        """Set expected number of LLM calls for progress tracking."""
        self.llm_service.set_expected_calls(count)
    
    def get_stride_categories_for_component(self, component: ComponentAnalysis) -> Dict[str, Tuple[str, str]]:
        """Get applicable STRIDE categories for a component."""
        component_type = component.type
        
        # Get applicable STRIDE categories for this component type
        applicable_categories = self.component_stride_mappings.get(
            component_type, 
            self.component_stride_mappings['Unknown']
        )
        
        # Return dictionary with category details
        categories = {}
        for cat_letter in applicable_categories:
            cat_name, cat_def = self.stride_definitions[cat_letter]
            categories[cat_letter] = (cat_name, cat_def)
        
        return categories
    
    def generate_threats_for_component(self, component: ComponentAnalysis) -> List[ThreatModel]:
        """Generate threats for a single component using sync processing."""
        logger.info(f"Generating threats for component: {component.name} ({component.type})")
        
        # Get applicable STRIDE categories
        stride_categories = self.get_stride_categories_for_component(component)
        
        all_threats = []
        
        # Generate threats for each applicable STRIDE category
        for cat_letter, (cat_name, cat_def) in stride_categories.items():
            try:
                if self.llm_service.is_available():
                    # Use LLM for threat generation
                    threats = self.llm_service.generate_threats(component, cat_letter, cat_name, cat_def)
                else:
                    # Use rule-based generation as fallback
                    threats = self._generate_rule_based_threats(component, cat_letter, cat_name, cat_def)
                
                all_threats.extend(threats)
                
            except Exception as e:
                if self.config.get('debug_mode', False):
                    logger.warning(f"⚠️ Failed to generate {cat_name} threats for {component.name}: {e}")
                    # Try rule-based as fallback in debug mode
                    fallback_threats = self._generate_rule_based_threats(component, cat_letter, cat_name, cat_def)
                    all_threats.extend(fallback_threats)
                else:
                    logger.error(f"❌ Failed to generate {cat_name} threats for {component.name}: {e}")
                    raise
        
        logger.info(f"Generated {len(all_threats)} threats for {component.name}")
        return all_threats
    
    async def generate_threats_for_components_batch(self, component_categories: List[Tuple[ComponentAnalysis, str, str, str]]) -> List[ThreatModel]:
        """Generate threats for multiple component-category combinations using async processing."""
        logger.info(f"⚡ Starting batch threat generation for {len(component_categories)} tasks")
        
        if not self.config.get('enable_async_processing', True):
            # Fall back to sequential processing
            logger.info("🔄 Async disabled, using sequential processing")
            return self._generate_threats_sequential(component_categories)
        
        if not self.llm_service.is_available():
            logger.info("🔧 LLM not available, using rule-based generation")
            return self._generate_threats_rule_based_batch(component_categories)
        
        try:
            # Use the LLM service's batch processing
            return await self.llm_service.generate_threats_for_components_batch(component_categories)
        except Exception as e:
            if self.config.get('debug_mode', False):
                logger.warning(f"⚠️ Batch async generation failed: {e} - falling back to sequential")
                return self._generate_threats_sequential(component_categories)
            else:
                logger.error(f"❌ Batch async generation failed: {e}")
                raise
    
    def _generate_threats_sequential(self, component_categories: List[Tuple[ComponentAnalysis, str, str, str]]) -> List[ThreatModel]:
        """Generate threats sequentially for fallback scenarios."""
        all_threats = []
        
        for component, cat_letter, cat_name, cat_def in component_categories:
            try:
                if self.llm_service.is_available():
                    threats = self.llm_service.generate_threats(component, cat_letter, cat_name, cat_def)
                else:
                    threats = self._generate_rule_based_threats(component, cat_letter, cat_name, cat_def)
                
                all_threats.extend(threats)
                
            except Exception as e:
                if self.config.get('debug_mode', False):
                    logger.warning(f"⚠️ Failed to generate {cat_name} threats for {component.name}: {e}")
                    fallback_threats = self._generate_rule_based_threats(component, cat_letter, cat_name, cat_def)
                    all_threats.extend(fallback_threats)
                else:
                    logger.error(f"❌ Failed to generate {cat_name} threats for {component.name}: {e}")
                    raise
        
        return all_threats
    
    def _generate_threats_rule_based_batch(self, component_categories: List[Tuple[ComponentAnalysis, str, str, str]]) -> List[ThreatModel]:
        """Generate threats using rule-based approach for all component-category combinations."""
        all_threats = []
        
        for component, cat_letter, cat_name, cat_def in component_categories:
            threats = self._generate_rule_based_threats(component, cat_letter, cat_name, cat_def)
            all_threats.extend(threats)
        
        return all_threats
    
    def _generate_rule_based_threats(self, component: ComponentAnalysis, cat_letter: str, 
                                   cat_name: str, cat_def: str) -> List[ThreatModel]:
        """Generate basic rule-based threats as fallback."""
        logger.info(f"🔧 Generating rule-based {cat_name} threats for {component.name}")
        
        # Basic threat templates based on component type and STRIDE category
        threat_templates = {
            ('Process', 'S'): [
                "Attacker impersonates the {component} service to gain unauthorized access",
                "Malicious actor spoofs {component} identity to bypass authentication"
            ],
            ('Process', 'T'): [
                "Unauthorized modification of {component} logic or configuration",
                "Data tampering during {component} processing operations"
            ],
            ('Process', 'R'): [
                "Users deny performing actions through {component}",
                "Insufficient logging in {component} enables repudiation attacks"
            ],
            ('Process', 'I'): [
                "Sensitive data exposed through {component} error messages or logs",
                "Information leakage from {component} due to insufficient access controls"
            ],
            ('Process', 'D'): [
                "Resource exhaustion attacks against {component}",
                "Service disruption of {component} through malformed inputs"
            ],
            ('Process', 'E'): [
                "Privilege escalation through {component} vulnerabilities",
                "Unauthorized elevation of permissions via {component} exploitation"
            ],
            ('Data Store', 'T'): [
                "Unauthorized modification of data in {component}",
                "Data corruption attacks against {component}"
            ],
            ('Data Store', 'I'): [
                "Unauthorized access to sensitive data in {component}",
                "Data exposure from {component} due to weak access controls"
            ],
            ('Data Store', 'D'): [
                "Data unavailability due to {component} corruption or deletion",
                "Storage exhaustion attacks against {component}"
            ],
            ('External Entity', 'S'): [
                "Impersonation of {component} to gain system access",
                "Spoofing attacks targeting {component} identity verification"
            ],
            ('API', 'S'): [
                "API impersonation attacks against {component}",
                "Spoofed API calls to {component} bypassing authentication"
            ],
            ('API', 'T'): [
                "Request/response tampering in {component} communications",
                "Unauthorized modification of {component} API calls"
            ],
            ('API', 'I'): [
                "Sensitive data exposure through {component} API responses",
                "Information leakage via {component} error responses"
            ]
        }
        
        # Get appropriate threat templates
        key = (component.type, cat_letter)
        templates = threat_templates.get(key, [
            f"Generic {cat_name.lower()} threat against {component.type.lower()} {component.name}"
        ])
        
        threats = []
        for i, template in enumerate(templates[:2]):  # Limit to 2 threats per category
            threat_desc = template.format(component=component.name)
            
            # Assign risk based on component risk score and threat category
            risk_score = self._calculate_rule_based_risk(component, cat_letter)
            impact, likelihood = self._risk_score_to_impact_likelihood(risk_score)
            
            threat = ThreatModel(
                component_name=component.name,
                stride_category=cat_letter,
                threat_description=threat_desc,
                mitigation_suggestion=self._get_generic_mitigation(cat_letter, component.type),
                impact=impact,
                likelihood=likelihood,
                risk_score=risk_score
            )
            threats.append(threat)
        
        return threats
    
    def _calculate_rule_based_risk(self, component: ComponentAnalysis, cat_letter: str) -> str:
        """Calculate risk score for rule-based threats."""
        base_risk = component.risk_score
        
        # Adjust risk based on STRIDE category severity
        category_multipliers = {
            'S': 0.8,  # Spoofing - medium severity
            'T': 0.9,  # Tampering - high severity
            'R': 0.6,  # Repudiation - lower severity
            'I': 0.9,  # Information Disclosure - high severity
            'D': 0.8,  # Denial of Service - medium severity
            'E': 1.0   # Elevation of Privilege - highest severity
        }
        
        adjusted_risk = base_risk * category_multipliers.get(cat_letter, 0.8)
        
        if adjusted_risk >= 8:
            return 'Critical'
        elif adjusted_risk >= 6:
            return 'High'
        elif adjusted_risk >= 4:
            return 'Medium'
        else:
            return 'Low'
    
    def _risk_score_to_impact_likelihood(self, risk_score: str) -> Tuple[str, str]:
        """Convert risk score to impact and likelihood."""
        mappings = {
            'Critical': ('High', 'High'),
            'High': ('High', 'Medium'),
            'Medium': ('Medium', 'Medium'),
            'Low': ('Low', 'Medium')
        }
        return mappings.get(risk_score, ('Medium', 'Medium'))
    
    def _get_generic_mitigation(self, cat_letter: str, component_type: str) -> str:
        """Get generic mitigation suggestion based on STRIDE category."""
        mitigations = {
            'S': f"Implement strong authentication and identity verification for {component_type}",
            'T': f"Use integrity checks and input validation for {component_type}",
            'R': f"Implement comprehensive logging and audit trails for {component_type}",
            'I': f"Apply encryption and access controls to protect {component_type} data",
            'D': f"Implement rate limiting and resource monitoring for {component_type}",
            'E': f"Use principle of least privilege and regular security reviews for {component_type}"
        }
        return mitigations.get(cat_letter, f"Apply appropriate security controls for {component_type}")