"""
Service for suppressing threats based on controls and relevance.
"""
import logging
from typing import List, Dict, Set
from services.external_data_service import ExternalDataService

logger = logging.getLogger(__name__)

class ThreatSuppressionService:
    """Service for suppressing irrelevant threats."""
    
    def __init__(self, config: dict):
        self.config = config
        self.external_data = ExternalDataService(config)
    
    def suppress_threats(self, threats: List[Dict], controls: Dict, 
                        dfd_data: Dict, kev_catalog: Set[str]) -> Tuple[List[Dict], int]:
        """Suppress threats based on implemented controls and CVE relevance."""
        active_threats = []
        suppressed_count = 0
        
        for threat in threats:
            suppress = False
            component = threat["component_name"]
            
            # Control-based suppression
            if controls.get("mtls_enabled") and "spoof" in threat["threat_description"].lower():
                logger.info(f"Suppressing spoofing threat for '{component}' due to mTLS control")
                suppress = True
                suppressed_count += 1
            
            if controls.get("secrets_manager") and any(keyword in threat["threat_description"].lower() 
                                                    for keyword in ["cleartext", "hardcoded", "plain text"]):
                logger.info(f"Suppressing credential threat for '{component}' due to secrets manager")
                suppress = True
                suppressed_count += 1
            
            if controls.get("waf_enabled") and "injection" in threat["threat_description"].lower():
                logger.info(f"Suppressing injection threat for '{component}' due to WAF")
                suppress = True
                suppressed_count += 1
            
            # CVE relevance filtering
            if not suppress and threat.get("references"):
                relevant_references = []
                for ref in threat["references"]:
                    if ref.startswith("CVE-"):
                        if self.external_data.check_cve_relevance(ref, kev_catalog):
                            relevant_references.append(ref)
                        else:
                            logger.debug(f"Filtering out irrelevant CVE: {ref}")
                    else:
                        relevant_references.append(ref)
                
                # Suppress if all CVE references were irrelevant
                if threat["references"] and not relevant_references and \
                   all(ref.startswith("CVE-") for ref in threat["references"]):
                    logger.info(f"Suppressing threat for '{component}' - all CVE references were irrelevant")
                    suppress = True
                    suppressed_count += 1
                else:
                    threat["references"] = relevant_references
            
            if not suppress:
                active_threats.append(threat)
        
        return active_threats, suppressed_count