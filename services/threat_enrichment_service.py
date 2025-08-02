"""
Service for enriching and improving threat quality.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.threat_models import ThreatModel

logger = logging.getLogger(__name__)

class ThreatEnrichmentService:
    """Service for enriching threats with additional context."""
    
    def __init__(self, config: dict):
        self.config = config
        self.client_industry = config.get('client_industry', 'General')
    
    def enrich_threat(self, threat: Dict[str, Any], flow_details: Optional[Dict], 
                     dfd_data: Dict) -> Dict[str, Any]:
        """Enrich a single threat with calculated fields and assessments."""
        # Upgrade impact based on data classification
        if flow_details and flow_details.get("data_classification") in ["PII", "PHI", "PCI", "Confidential"]:
            current_impact = threat.get("impact", "Medium")
            if current_impact == "Medium":
                threat["impact"] = "High"
            elif current_impact == "High":
                threat["impact"] = "Critical"
        
        # Calculate derived fields
        threat["risk_score"] = self.calculate_risk_score(
            threat.get("impact", "Medium"), 
            threat.get("likelihood", "Medium")
        )
        
        # Calculate residual risk
        current_likelihood = threat.get("likelihood", "Medium")
        mitigated_likelihood = {
            "High": "Medium",
            "Medium": "Low",
            "Low": "Low"
        }.get(current_likelihood, "Low")
        
        threat["residual_risk_score"] = self.calculate_risk_score(
            threat.get("impact", "Medium"), 
            mitigated_likelihood
        )
        
        # Assess exploitability and mitigation maturity
        threat["exploitability"] = self.assess_exploitability(threat, dfd_data)
        threat["mitigation_maturity"] = self.assess_mitigation_maturity(
            threat.get("mitigation_suggestion", "")
        )
        
        # Generate human-readable fields
        threat["justification"] = self.generate_justification(threat, flow_details)
        threat["risk_statement"] = self.generate_risk_statement(threat, flow_details)
        
        return threat
    
    def calculate_risk_score(self, impact: str, likelihood: str) -> str:
        """Calculate risk score based on impact and likelihood matrix."""
        impact_values = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        likelihood_values = {"High": 3, "Medium": 2, "Low": 1}
        
        impact_val = impact_values.get(impact, 1)
        likelihood_val = likelihood_values.get(likelihood, 1)
        score = impact_val * likelihood_val
        
        if score >= 9:
            return "Critical"
        elif score >= 6:
            return "High"
        elif score >= 3:
            return "Medium"
        else:
            return "Low"
    
    def assess_exploitability(self, threat: Dict, dfd_data: Dict) -> str:
        """Assess exploitability based on component exposure."""
        component_name = threat["component_name"]
        flows = dfd_data.get("data_flows", [])
        
        # Find corresponding flow
        flow = next((f for f in flows 
                    if f"{f.get('source', '')} to {f.get('destination', '')}" == component_name), None)
        
        if not flow:
            return "Medium"
        
        # Check if externally exposed
        if flow.get("source") == "U" or flow.get("destination") == "U":
            return "High"
        
        # Check protocol security
        protocol = flow.get("protocol", "").upper()
        if any(secure in protocol for secure in ["TLS", "HTTPS", "SSH", "SFTP"]):
            return "Medium"
        elif any(insecure in protocol for insecure in ["HTTP", "FTP", "TELNET"]):
            return "High"
        
        return "Low"
    
    def assess_mitigation_maturity(self, mitigation: str) -> str:
        """Assess the maturity level of proposed mitigation."""
        mitigation_lower = mitigation.lower()
        
        # Advanced mitigations
        advanced_keywords = ["end-to-end encryption", "certificate pinning", "zero trust", 
                           "hardware security module"]
        if any(keyword in mitigation_lower for keyword in advanced_keywords):
            return "Advanced"
        
        # Mature mitigations
        mature_keywords = ["mtls", "waf", "rate limiting", "secrets management", 
                         "multi-factor", "rbac"]
        if any(keyword in mitigation_lower for keyword in mature_keywords):
            return "Mature"
        
        # Immature mitigations
        immature_keywords = ["logging", "monitoring", "manual review", "periodic check"]
        if any(keyword in mitigation_lower for keyword in immature_keywords):
            return "Immature"
        
        return "Mature"
    
    def generate_justification(self, threat: Dict, flow_details: Optional[Dict]) -> str:
        """Generate justification for impact and likelihood ratings."""
        impact = threat.get('impact', 'Medium')
        likelihood = threat.get('likelihood', 'Medium')
        
        # Build impact justification
        impact_reasons = []
        if flow_details:
            data_classification = flow_details.get("data_classification", "Unclassified")
            if data_classification in ["PII", "PHI", "PCI", "Confidential"]:
                impact_reasons.append(f"handles {data_classification} data with regulatory implications")
            elif data_classification != "Unclassified":
                impact_reasons.append(f"processes {data_classification} data")
        
        if "database" in threat["component_name"].lower():
            impact_reasons.append("involves critical data storage")
        
        impact_justification = f"Impact rated {impact}"
        if impact_reasons:
            impact_justification += f" due to: {', '.join(impact_reasons)}"
        
        # Build likelihood justification
        likelihood_reasons = []
        if flow_details and flow_details.get("source") == "U":
            likelihood_reasons.append("internet-facing component increases attack surface")
        
        stride_category = threat.get("stride_category", "")
        if stride_category in ["S", "T"]:
            likelihood_reasons.append("authentication/integrity threats are commonly exploited")
        
        likelihood_justification = f"Likelihood rated {likelihood}"
        if likelihood_reasons:
            likelihood_justification += f" because: {', '.join(likelihood_reasons)}"
        
        return f"{impact_justification}. {likelihood_justification}."
    
    def generate_risk_statement(self, threat: Dict, flow_details: Optional[Dict]) -> str:
        """Generate business-contextualized risk statement."""
        impact_descriptions = {
            "Critical": "severe financial loss (>$1M), major regulatory fines, and long-term reputational damage",
            "High": "significant financial loss (>$500K), regulatory fines, or reputational damage",
            "Medium": "moderate financial loss ($50K-$500K) or operational disruption",
            "Low": "minimal financial or operational impact"
        }
        
        component = threat["component_name"]
        impact = threat.get("impact", "Medium")
        
        risk_statement = f"Exploitation of '{threat['threat_description']}' in the '{component}' component could result in {impact_descriptions[impact]}."
        
        # Add industry-specific context
        if flow_details:
            data_classification = flow_details.get("data_classification", "")
            if self.client_industry == "Finance" and data_classification == "PCI":
                risk_statement += " This may result in PCI-DSS compliance violations."
            elif self.client_industry == "Healthcare" and data_classification == "PHI":
                risk_statement += " This may result in HIPAA regulatory violations."
        
        # Add mitigation impact
        if threat.get('residual_risk_score') != threat.get('risk_score'):
            risk_statement += f" Implementing the proposed mitigation is expected to reduce risk to '{threat.get('residual_risk_score', 'Medium')}' level."
        
        return risk_statement