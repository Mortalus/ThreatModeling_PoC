"""
Service for analyzing component risk and prioritization.
"""
import logging
from typing import List, Dict, Any, Optional
from models.threat_models import ComponentAnalysis, COMPONENT_STRIDE_MAPPING

logger = logging.getLogger(__name__)

class ComponentRiskAnalyzer:
    """Analyzes and prioritizes components based on risk factors."""
    
    # Risk assessment keywords
    HIGH_RISK_KEYWORDS = [
        'database', 'db', 'store', 'repository', 'cache',
        'authentication', 'auth', 'login', 'user', 'credential',
        'payment', 'financial', 'money', 'transaction', 'billing',
        'admin', 'management', 'control', 'configuration',
        'api', 'service', 'server', 'endpoint',
        'external', 'third-party', 'internet', 'public',
        'sensitive', 'confidential', 'secret', 'private',
        'key', 'token', 'certificate', 'password'
    ]
    
    TRUST_BOUNDARY_KEYWORDS = [
        'external', 'internet', 'public', 'client',
        'browser', 'mobile', 'api', 'web', 'cloud',
        'partner', 'vendor', 'customer', 'user'
    ]
    
    def __init__(self, min_risk_score: int = 3):
        self.min_risk_score = min_risk_score
    
    def analyze_components(self, dfd_data: Dict[str, Any]) -> List[ComponentAnalysis]:
        """Extract and analyze components from DFD data."""
        components = []
        
        component_mappings = {
            'external_entities': 'External Entity',
            'processes': 'Process', 
            'assets': 'Data Store',
            'data_stores': 'Data Store',
            'data_flows': 'Data Flow',
            'trust_boundaries': 'Trust Boundary'
        }
        
        for key, component_type in component_mappings.items():
            if key in dfd_data:
                items = dfd_data[key]
                if isinstance(items, list):
                    for item in items:
                        component = self._create_component_analysis(item, component_type, key)
                        if component:
                            components.append(component)
        
        # Prioritize by risk
        components = self.prioritize_components(components)
        
        logger.info(f"Analyzed {len(components)} components from DFD")
        return components
    
    def _create_component_analysis(self, item: Any, component_type: str, key: str) -> Optional[ComponentAnalysis]:
        """Create ComponentAnalysis from raw component data."""
        try:
            if isinstance(item, str):
                # Simple string component
                name = item
                details = {"identifier": item, "source_key": key}
            elif isinstance(item, dict):
                # Complex component with details
                name = item.get('name', item.get('source', item.get('destination', 'Unknown')))
                details = item.copy()
                details['source_key'] = key
                
                # For data flows, create descriptive name
                if key == 'data_flows' and 'source' in item and 'destination' in item:
                    name = f"{item['source']} → {item['destination']}"
            else:
                logger.warning(f"Unexpected component type: {type(item)}")
                return None
            
            # Calculate risk score
            risk_score = self.calculate_component_risk_score(name, component_type, details)
            
            # Get applicable STRIDE categories
            applicable_stride = COMPONENT_STRIDE_MAPPING.get(
                component_type, 
                ['S', 'T', 'I']  # Default categories
            )
            
            return ComponentAnalysis(
                name=name,
                type=component_type,
                risk_score=risk_score,
                applicable_stride=applicable_stride,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Error creating component analysis: {e}")
            return None
    
    def calculate_component_risk_score(self, name: str, comp_type: str, details: Dict) -> int:
        """Calculate risk score for component prioritization."""
        score = 1  # Base score
        
        name_lower = name.lower()
        comp_type_lower = comp_type.lower()
        details_str = str(details).lower()
        
        # High-risk component types
        if comp_type == 'Data Store':
            score += 3
        elif comp_type == 'External Entity':
            score += 2
        elif comp_type == 'Process':
            score += 1
        elif comp_type == 'Trust Boundary':
            score += 2
        
        # Check for high-risk keywords
        text_to_check = f"{name_lower} {comp_type_lower} {details_str}"
        
        # Count high-risk keyword matches
        high_risk_matches = sum(1 for keyword in self.HIGH_RISK_KEYWORDS if keyword in text_to_check)
        if high_risk_matches > 0:
            score += min(high_risk_matches, 3)  # Cap at 3 additional points
        
        # Trust boundary crossing
        trust_boundary_matches = sum(1 for keyword in self.TRUST_BOUNDARY_KEYWORDS if keyword in text_to_check)
        if trust_boundary_matches > 0:
            score += min(trust_boundary_matches, 2)  # Cap at 2 additional points
        
        # Data flows between different trust zones
        if comp_type == 'Data Flow':
            source = str(details.get('source', '')).lower()
            dest = str(details.get('destination', '')).lower()
            
            # Cross-boundary flows are higher risk
            external_sources = ['external', 'client', 'browser', 'internet', 'user', 'public']
            internal_dests = ['database', 'server', 'internal', 'backend', 'core', 'private']
            
            if any(ext in source for ext in external_sources) and \
               any(int_dest in dest for int_dest in internal_dests):
                score += 3
            elif any(ext in source for ext in external_sources) or \
                 any(ext in dest for ext in external_sources):
                score += 2
        
        # Special case for authentication/authorization components
        auth_keywords = ['auth', 'login', 'session', 'token', 'credential', 'password']
        if any(keyword in text_to_check for keyword in auth_keywords):
            score += 2
        
        # Cap score at 10
        return min(score, 10)
    
    def prioritize_components(self, components: List[ComponentAnalysis]) -> List[ComponentAnalysis]:
        """Prioritize components based on risk factors."""
        # Sort by risk score (highest first)
        components.sort(key=lambda x: x.risk_score, reverse=True)
        
        # Log top components
        if components:
            logger.info("Top 5 highest risk components:")
            for comp in components[:5]:
                logger.info(f"  - {comp.name} ({comp.type}) [Risk: {comp.risk_score}]")
        
        return components
    
    def should_analyze_component(self, component: ComponentAnalysis) -> bool:
        """Determine if component should be analyzed based on risk."""
        return component.risk_score >= self.min_risk_score