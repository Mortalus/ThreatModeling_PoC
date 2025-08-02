"""
Service for deduplicating and filtering threats.
"""
import difflib
import logging
from typing import List, Dict, Set
from models.threat_models import ThreatModel

logger = logging.getLogger(__name__)

class ThreatDeduplicationService:
    """Service for deduplicating and filtering threats."""
    
    GENERIC_PHRASES = [
        'an attacker could',
        'unauthorized access',
        'malicious user might',
        'potential security risk',
        'vulnerability may exist'
    ]
    
    MIN_DESCRIPTION_LENGTH = 50
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
    
    def deduplicate_threats(self, threats: List[ThreatModel]) -> List[ThreatModel]:
        """Remove duplicate threats based on semantic similarity."""
        unique_threats = []
        processed_indices: Set[int] = set()
        
        for i, threat in enumerate(threats):
            if i in processed_indices:
                continue
            
            # Find similar threats
            similar_threats = [threat]
            for j, other_threat in enumerate(threats[i+1:], i+1):
                if j not in processed_indices and self._are_similar_threats(threat, other_threat):
                    similar_threats.append(other_threat)
                    processed_indices.add(j)
            
            # Keep the threat with highest risk score
            risk_order = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
            best_threat = max(similar_threats, 
                             key=lambda t: risk_order.get(t.risk_score, 0))
            
            unique_threats.append(best_threat)
            processed_indices.add(i)
        
        return unique_threats
    
    def filter_quality_threats(self, threats: List[ThreatModel]) -> List[ThreatModel]:
        """Filter out low-quality or generic threats."""
        quality_threats = []
        
        for threat in threats:
            description = threat.threat_description.lower()
            
            # Skip if too short
            if len(description) < self.MIN_DESCRIPTION_LENGTH:
                continue
            
            # Skip if too generic (more than 2 generic phrases)
            generic_count = sum(1 for phrase in self.GENERIC_PHRASES if phrase in description)
            if generic_count > 2:
                continue
            
            # Skip if mitigation is too vague
            mitigation = threat.mitigation_suggestion
            if len(mitigation) < 30 or 'implement security measures' in mitigation.lower():
                continue
            
            quality_threats.append(threat)
        
        return quality_threats
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        import re
        text = re.sub(r'\s+', ' ', text.lower().strip())
        text = re.sub(r'\b(an?|the)\b', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    def _are_similar_threats(self, threat1: ThreatModel, threat2: ThreatModel) -> bool:
        """Check if two threats are semantically similar."""
        desc1 = self._normalize_text(threat1.threat_description)
        desc2 = self._normalize_text(threat2.threat_description)
        
        # Same component and STRIDE category
        if (threat1.component_name == threat2.component_name and 
            threat1.stride_category == threat2.stride_category):
            
            similarity = difflib.SequenceMatcher(None, desc1, desc2).ratio()
            return similarity > self.similarity_threshold
        
        return False