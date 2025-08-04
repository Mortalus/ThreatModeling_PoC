"""
Service for threat deduplication and quality filtering.
"""
import logging
import re
import difflib
from typing import List, Dict, Any, Set
from models.threat_models import ThreatModel

logger = logging.getLogger(__name__)

class ThreatDeduplicationService:
    """Service for deduplicating and filtering threats."""
    
    # Generic phrases that indicate low-quality threats
    GENERIC_PHRASES = [
        'an attacker could',
        'unauthorized access',
        'malicious user might',
        'potential security risk',
        'vulnerability may exist',
        'security vulnerability',
        'could be exploited',
        'might be compromised'
    ]
    
    # Minimum description lengths
    MIN_DESCRIPTION_LENGTH = 50
    MIN_MITIGATION_LENGTH = 30
    
    def __init__(self, similarity_threshold: float = 0.70):
        self.similarity_threshold = similarity_threshold
    
    def deduplicate_threats(self, threats: List[ThreatModel]) -> List[ThreatModel]:
        """Remove duplicate threats based on semantic similarity."""
        if not threats:
            return []
        
        unique_threats = []
        processed_indices: Set[int] = set()
        
        for i, threat in enumerate(threats):
            if i in processed_indices:
                continue
            
            # Find similar threats
            similar_threats = [threat]
            similar_indices = [i]
            
            for j, other_threat in enumerate(threats[i+1:], i+1):
                if j not in processed_indices and self._are_similar_threats(threat, other_threat):
                    similar_threats.append(other_threat)
                    similar_indices.append(j)
                    processed_indices.add(j)
            
            # Keep the threat with highest risk score
            best_threat = self._select_best_threat(similar_threats)
            unique_threats.append(best_threat)
            
            # Mark all similar threats as processed
            for idx in similar_indices:
                processed_indices.add(idx)
            
            if len(similar_threats) > 1:
                logger.debug(f"Merged {len(similar_threats)} similar threats for {threat.component_name}")
        
        logger.info(f"Deduplication: {len(threats)} → {len(unique_threats)} threats")
        return unique_threats
    
    def filter_quality_threats(self, threats: List[ThreatModel]) -> List[ThreatModel]:
        """Filter out low-quality or generic threats."""
        quality_threats = []
        
        for threat in threats:
            if self._is_quality_threat(threat):
                quality_threats.append(threat)
            else:
                logger.debug(f"Filtered out low-quality threat: {threat.component_name} - {threat.stride_category}")
        
        logger.info(f"Quality filtering: {len(threats)} → {len(quality_threats)} threats")
        return quality_threats
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common articles
        text = re.sub(r'\b(an?|the)\b', '', text)
        
        # Remove punctuation for comparison
        text = re.sub(r'[^\w\s]', '', text)
        
        return text
    
    def _are_similar_threats(self, threat1: ThreatModel, threat2: ThreatModel) -> bool:
        """Check if two threats are semantically similar."""
        # Must be same component and STRIDE category
        if (threat1.component_name != threat2.component_name or 
            threat1.stride_category != threat2.stride_category):
            return False
        
        # Normalize descriptions
        desc1 = self._normalize_text(threat1.threat_description)
        desc2 = self._normalize_text(threat2.threat_description)
        
        # Calculate similarity
        similarity = difflib.SequenceMatcher(None, desc1, desc2).ratio()
        
        # Also check mitigation similarity
        mit1 = self._normalize_text(threat1.mitigation_suggestion)
        mit2 = self._normalize_text(threat2.mitigation_suggestion)
        mit_similarity = difflib.SequenceMatcher(None, mit1, mit2).ratio()
        
        # Consider threats similar if descriptions OR mitigations are very similar
        return (similarity > self.similarity_threshold or 
                mit_similarity > self.similarity_threshold + 0.1)
    
    def _select_best_threat(self, threats: List[ThreatModel]) -> ThreatModel:
        """Select the best threat from a group of similar threats."""
        if len(threats) == 1:
            return threats[0]
        
        # Risk score priority
        risk_order = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
        
        # Sort by multiple criteria
        def threat_score(threat):
            return (
                risk_order.get(threat.risk_score, 0),  # Risk score
                len(threat.threat_description),         # Description length
                len(threat.references),                 # Number of references
                len(threat.mitigation_suggestion)       # Mitigation detail
            )
        
        return max(threats, key=threat_score)
    
    def _is_quality_threat(self, threat: ThreatModel) -> bool:
        """Check if a threat meets quality standards."""
        description = threat.threat_description.lower()
        mitigation = threat.mitigation_suggestion.lower()
        
        # Check description length
        if len(threat.threat_description) < self.MIN_DESCRIPTION_LENGTH:
            return False
        
        # Check mitigation length
        if len(threat.mitigation_suggestion) < self.MIN_MITIGATION_LENGTH:
            return False
        
        # Check for too many generic phrases
        generic_count = sum(1 for phrase in self.GENERIC_PHRASES if phrase in description)
        if generic_count > 2:
            return False
        
        # Check if mitigation is too vague
        vague_mitigations = [
            'implement security measures',
            'follow best practices',
            'use proper security',
            'apply security controls',
            'ensure security'
        ]
        
        if any(vague in mitigation for vague in vague_mitigations):
            return False
        
        # Check for actual specific content
        # Should have at least some technical terms or specific actions
        technical_indicators = [
            'encrypt', 'authenticate', 'validate', 'sanitize', 'authorization',
            'tls', 'ssl', 'certificate', 'token', 'session', 'audit', 'log',
            'firewall', 'ids', 'ips', 'waf', 'rate limit', 'throttle',
            'input validation', 'output encoding', 'parameterized', 'prepared statement',
            'least privilege', 'role-based', 'multi-factor', '2fa', 'mfa'
        ]
        
        has_technical_content = any(term in description.lower() or term in mitigation.lower() 
                                   for term in technical_indicators)
        
        if not has_technical_content:
            return False
        
        return True