"""
Rule-based DFD extraction service as fallback when LLM is unavailable.
"""
import re
import logging
from typing import Dict, Any
from models.dfd_models import SimpleDFDComponents, SimpleDataFlow

logger = logging.getLogger(__name__)

class RuleBasedExtractor:
    """Rule-based DFD extractor as fallback."""
    
    def extract(self, content: str, doc_analysis: Dict) -> SimpleDFDComponents:
        """Extract DFD components using rule-based patterns."""
        logger.info("Using rule-based extraction as fallback")
        
        result = SimpleDFDComponents()
        result.project_name = "Extracted Project"
        result.industry_context = doc_analysis.get('industry_context', 'General')
        
        content_lower = content.lower()
        
        # Extract entities using patterns
        entity_patterns = [
            r'\b(user|customer|client|admin|administrator|operator)\b',
            r'\b(external (?:system|service|api|user))\b',
            r'\b(third.?party|payment processor|vendor)\b'
        ]
        
        process_patterns = [
            r'\b(web server|application server|api server|service)\b',
            r'\b(gateway|proxy|load balancer|firewall)\b',
            r'\b(authentication service|session manager)\b'
        ]
        
        asset_patterns = [
            r'\b(database|db|data store|storage)\b',
            r'\b(cache|repository|file system)\b',
            r'\b(log|audit trail|backup)\b'
        ]
        
        # Extract using patterns
        for pattern in entity_patterns:
            matches = re.findall(pattern, content_lower)
            for match in set(matches):
                clean_match = match.strip().title()
                if clean_match not in result.external_entities:
                    result.external_entities.append(clean_match)
        
        for pattern in process_patterns:
            matches = re.findall(pattern, content_lower)
            for match in set(matches):
                clean_match = match.strip().title()
                if clean_match not in result.processes:
                    result.processes.append(clean_match)
        
        for pattern in asset_patterns:
            matches = re.findall(pattern, content_lower)
            for match in set(matches):
                clean_match = match.strip().title()
                if clean_match not in result.assets:
                    result.assets.append(clean_match)
        
        # Add default components if none found
        if not result.external_entities:
            result.external_entities = ["User", "Administrator"]
        if not result.processes:
            result.processes = ["Web Server", "Application Server"]
        if not result.assets:
            result.assets = ["Database", "File Storage"]
        
        # Add basic trust boundaries
        result.trust_boundaries = ["External to Internal", "DMZ to Application", "Application to Data"]
        
        # Add basic data flows
        if len(result.external_entities) > 0 and len(result.processes) > 0:
            flow = SimpleDataFlow(
                source=result.external_entities[0],
                destination=result.processes[0],
                data_description="User requests and authentication data",
                data_classification="Internal",
                protocol="HTTPS",
                authentication_mechanism="Session Token"
            )
            result.data_flows.append(flow)
        
        if len(result.processes) > 0 and len(result.assets) > 0:
            flow = SimpleDataFlow(
                source=result.processes[0],
                destination=result.assets[0],
                data_description="Application data and user information",
                data_classification="Confidential",
                protocol="JDBC",
                authentication_mechanism="Database Credentials"
            )
            result.data_flows.append(flow)
        
        result.assumptions = ["Rule-based extraction used", "Limited detail available"]
        result.confidence_notes = ["Manual review recommended"]
        
        return result