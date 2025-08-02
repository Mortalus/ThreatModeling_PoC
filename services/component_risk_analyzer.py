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
        'authentication', 'auth', 'login', 'user',
        'payment', 'financial', 'money', 'transaction',
        'admin', 'management', 'control',
        'api', 'service', 'server',
        'external', 'third-party', 'internet'
    ]
    
    TRUST_BOUNDARY_KEYWORDS = [
        'external', 'internet', 'public', 'client',
        'browser', 'mobile', 'api', 'web'
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
            'data_flows': 'Data Flow'
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
        
        return components
    
    def _create_component_analysis(self, item: Any, component_type: str, key: str) -> Optional[ComponentAnalysis]:
        """Create ComponentAnalysis from raw component data."""
        if isinstance(item, str):
            name = item
            details = {"identifier": item}
        elif isinstance(item, dict):
            # Handle data flows specially
            if key == 'data_flows' and 'source' in item and 'destination' in item:
                name = f"{item['source']} → {item['destination']}"
            else:
                name = item.get('name', item.get('source', item.get('destination', 'Unknown')))
            details = item
        else:
            return None
        
        risk_score = self.calculate_component_risk_score(name, component_type, details)
        applicable_stride = self.get_applicable_stride_categories(component_type)
        
        return ComponentAnalysis(
            name=name,
            type=component_type,
            risk_score=risk_score,
            applicable_stride=applicable_stride,
            details=details
        )
    
    def calculate_component_risk_score(self, name: str, comp_type: str, details: Dict) -> int:
        """Calculate risk score for component prioritization."""
        score = 1  # Base score
        
        name_lower = name.lower()
        details_str = str(details).lower()
        
        # High-risk component types
        if comp_type == 'Data Store':
            score += 3
        elif comp_type == 'External Entity':
            score += 2
        elif comp_type == 'Process':
            score += 1
        
        # Check for high-risk keywords
        text_to_check = f"{name_lower} {comp_type.lower()} {details_str}"
        for keyword in self.HIGH_RISK_KEYWORDS:
            if keyword in text_to_check:
                score += 2
                break
        
        # Trust boundary crossing
        for keyword in self.TRUST_BOUNDARY_KEYWORDS:
            if keyword in text_to_check:
                score += 2
                break
        
        # Data flows between different trust zones
        if comp_type == 'Data Flow' and isinstance(details, dict):
            source = str(details.get('source', '')).lower()
            dest = str(details.get('destination', '')).lower()
            
            # Cross-boundary flows are higher risk
            external_sources = ['external', 'client', 'browser', 'internet']
            internal_dests = ['database', 'server', 'internal', 'backend']
            
            if any(ext in source for ext in external_sources) and \
               any(int_dest in dest for int_dest in internal_dests):
                score += 3
        
        return min(score, 10)  # Cap at 10
    
    def prioritize_components(self, components: List[ComponentAnalysis]) -> List[ComponentAnalysis]:
        """Prioritize components based on risk factors."""
        # Sort by risk score (highest first)
        components.sort(key=lambda x: x.risk_score, reverse=True)
        return components
    
    def should_analyze_component(self, component: ComponentAnalysis) -> bool:
        """Determine if component should be analyzed based on risk."""
        return component.risk_score >= self.min_risk_score
    
    def get_applicable_stride_categories(self, component_type: str) -> List[str]:
        """Get only the applicable STRIDE categories for a component type."""
        return COMPONENT_STRIDE_MAPPING.get(component_type, ['S', 'T', 'I'])