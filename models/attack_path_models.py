"""
Data models for attack path analysis.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class AttackStep:
    """Model for a single step in an attack path."""
    step_number: int
    component: str
    threat_id: str
    threat_description: str
    stride_category: str
    technique_id: Optional[str] = None
    prerequisites: List[str] = field(default_factory=list)
    enables: List[str] = field(default_factory=list)
    required_access: Optional[str] = None
    detection_difficulty: Optional[str] = None

@dataclass
class AttackPath:
    """Model for a complete attack path."""
    path_id: str
    scenario_name: str
    entry_point: str
    target_asset: str
    path_steps: List[AttackStep]
    total_steps: int
    combined_likelihood: str
    combined_impact: str
    path_feasibility: str = "Realistic"
    attacker_profile: str = "Cybercriminal"
    time_to_compromise: str = "Days"
    key_chokepoints: List[str] = field(default_factory=list)
    detection_opportunities: List[str] = field(default_factory=list)
    required_resources: List[str] = field(default_factory=list)
    path_complexity: str = "Medium"

@dataclass
class AttackPathAnalysis:
    """Complete attack path analysis results."""
    attack_paths: List[AttackPath]
    critical_scenarios: List[str]
    defense_priorities: List[Dict[str, Any]]
    threat_coverage: Dict[str, Any] = field(default_factory=dict)
    vector_store_insights: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ThreatStats:
    """Statistics for threat processing."""
    original_count: int = 0
    suppressed_count: int = 0
    deduplicated_count: int = 0
    final_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0