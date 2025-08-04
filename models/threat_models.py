"""
Data models for threat generation and analysis.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

class StrideCategory(Enum):
    """STRIDE threat categories."""
    SPOOFING = "S"
    TAMPERING = "T"
    REPUDIATION = "R"
    INFORMATION_DISCLOSURE = "I"
    DENIAL_OF_SERVICE = "D"
    ELEVATION_OF_PRIVILEGE = "E"

@dataclass
class ThreatModel:
    """Model for a security threat."""
    component_name: str
    stride_category: str
    threat_description: str
    mitigation_suggestion: str
    impact: str = "Medium"
    likelihood: str = "Medium"
    references: List[str] = field(default_factory=list)
    risk_score: str = "Medium"
    threat_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate threat ID if not provided."""
        if not self.threat_id:
            self.threat_id = f"THREAT-{uuid.uuid4().hex[:8].upper()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'threat_id': self.threat_id,
            'component_name': self.component_name,
            'stride_category': self.stride_category,
            'threat_description': self.threat_description,
            'mitigation_suggestion': self.mitigation_suggestion,
            'impact': self.impact,
            'likelihood': self.likelihood,
            'references': self.references,
            'risk_score': self.risk_score
        }

@dataclass
class ComponentAnalysis:
    """Analysis data for a component."""
    name: str
    type: str
    risk_score: int
    applicable_stride: List[str]
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.type}) [Risk: {self.risk_score}]"

# STRIDE definitions
DEFAULT_STRIDE_DEFINITIONS = {
    "S": ("Spoofing", "Illegitimately accessing systems or data by impersonating a user, process, or component."),
    "T": ("Tampering", "Unauthorized modification of data, either in transit or at rest."),  
    "R": ("Repudiation", "A user or system denying that they performed an action, often due to a lack of sufficient proof."),
    "I": ("Information Disclosure", "Exposing sensitive information to unauthorized individuals."),
    "D": ("Denial of Service", "Preventing legitimate users from accessing a system or service."),
    "E": ("Elevation of Privilege", "A user or process gaining rights beyond their authorized level.")
}

# Component-specific STRIDE mappings
COMPONENT_STRIDE_MAPPING = {
    'External Entity': ['S', 'R'],  # Primarily Spoofing and Repudiation concerns
    'Process': ['S', 'T', 'R', 'I', 'D', 'E'],  # All STRIDE categories
    'Data Store': ['T', 'R', 'I', 'D'],  # No Spoofing or Elevation typically
    'Data Flow': ['T', 'I', 'D'],  # Tampering, Info Disclosure, DoS
    'Trust Boundary': ['S', 'T', 'E'],  # Spoofing, Tampering, Elevation
    'Asset': ['T', 'I', 'D'],  # Similar to Data Store
    'Database': ['T', 'R', 'I', 'D'],  # Similar to Data Store
    'API': ['S', 'T', 'R', 'I', 'D', 'E'],  # All categories like Process
    'Service': ['S', 'T', 'R', 'I', 'D', 'E'],  # All categories
    'Network': ['T', 'I', 'D'],  # Similar to Data Flow
    'Unknown': ['S', 'T', 'I']  # Conservative default
}

# Risk-based threat limits per component type
MAX_THREATS_PER_COMPONENT = {
    'External Entity': 2,
    'Process': 3,
    'Data Store': 3,
    'Data Flow': 2,
    'Trust Boundary': 2,
    'Asset': 2,
    'Database': 3,
    'API': 3,
    'Service': 3,
    'Network': 2,
    'Unknown': 2
}

# Risk scoring matrices
RISK_MATRIX = {
    ('Critical', 'High'): 'Critical',
    ('Critical', 'Medium'): 'Critical', 
    ('Critical', 'Low'): 'High',
    ('High', 'High'): 'Critical',
    ('High', 'Medium'): 'High',
    ('High', 'Low'): 'Medium',
    ('Medium', 'High'): 'High',
    ('Medium', 'Medium'): 'Medium',
    ('Medium', 'Low'): 'Low',
    ('Low', 'High'): 'Medium',
    ('Low', 'Medium'): 'Low',
    ('Low', 'Low'): 'Low'
}

def calculate_risk_score(impact: str, likelihood: str) -> str:
    """Calculate risk score based on impact and likelihood."""
    return RISK_MATRIX.get((impact, likelihood), 'Medium')