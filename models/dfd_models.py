"""
Data models for DFD extraction and components.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class SimpleDataFlow:
    """Simple data flow model without Pydantic dependency."""
    source: str
    destination: str
    data_description: str = ""
    data_classification: str = "Internal"
    protocol: str = "HTTPS"
    authentication_mechanism: str = "Unknown"
    trust_boundary_crossing: bool = False
    encryption_in_transit: bool = True
    
    def to_dict(self):
        return {
            'source': self.source,
            'destination': self.destination,
            'data_description': self.data_description,
            'data_classification': self.data_classification,
            'protocol': self.protocol,
            'authentication_mechanism': self.authentication_mechanism,
            'trust_boundary_crossing': self.trust_boundary_crossing,
            'encryption_in_transit': self.encryption_in_transit
        }

@dataclass
class SimpleDFDComponents:
    """Simple DFD components model without Pydantic dependency."""
    project_name: str = "Unknown Project"
    project_version: str = "1.0"
    industry_context: str = "General"
    external_entities: List[str] = field(default_factory=list)
    processes: List[str] = field(default_factory=list)
    assets: List[str] = field(default_factory=list)
    trust_boundaries: List[str] = field(default_factory=list)
    data_flows: List[SimpleDataFlow] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    confidence_notes: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'project_name': self.project_name,
            'project_version': self.project_version,
            'industry_context': self.industry_context,
            'external_entities': self.external_entities,
            'processes': self.processes,
            'assets': self.assets,
            'trust_boundaries': self.trust_boundaries,
            'data_flows': [flow.to_dict() if hasattr(flow, 'to_dict') else flow for flow in self.data_flows],
            'assumptions': self.assumptions,
            'confidence_notes': self.confidence_notes
        }