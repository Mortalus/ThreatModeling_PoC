"""
Service for text similarity matching without ML dependencies.
"""
import re
import difflib
from typing import List, Dict, Set

class SimpleSimilarityMatcher:
    """Simple text similarity matching without ML dependencies."""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two texts."""
        # Convert to lowercase and split into words
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def find_similar_threats(self, threats: List[Dict]) -> List[List[int]]:
        """Find groups of similar threats."""
        n = len(threats)
        similar_groups = []
        processed = set()
        
        for i in range(n):
            if i in processed:
                continue
            
            current_group = [i]
            threat_text_i = f"{threats[i].get('threat_description', '')} {threats[i].get('mitigation_suggestion', '')}"
            
            for j in range(i + 1, n):
                if j in processed:
                    continue
                
                threat_text_j = f"{threats[j].get('threat_description', '')} {threats[j].get('mitigation_suggestion', '')}"
                
                # Check if they're for the same component and have similar text
                if (threats[i].get('component_name') == threats[j].get('component_name') and
                    threats[i].get('stride_category') == threats[j].get('stride_category') and
                    self.calculate_similarity(threat_text_i, threat_text_j) >= self.threshold):
                    
                    current_group.append(j)
                    processed.add(j)
            
            if len(current_group) > 1:
                similar_groups.append(current_group)
            
            processed.add(i)
        
        return similar_groups
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        text = re.sub(r'\s+', ' ', text.lower().strip())
        text = re.sub(r'\b(an?|the)\b', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    def are_similar(self, text1: str, text2: str) -> bool:
        """Check if two texts are similar."""
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)
        
        similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        return similarity > self.threshold