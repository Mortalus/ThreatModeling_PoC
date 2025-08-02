"""
Rule-based threat generator for fallback when LLM is unavailable.
"""
import logging
from typing import List, Dict, Any
from models.threat_models import ThreatModel, ComponentAnalysis

logger = logging.getLogger(__name__)

class RuleBasedThreatGenerator:
    """Improved fallback threat generator using predefined rules."""
    
    def __init__(self, stride_definitions: Dict[str, tuple]):
        self.stride_definitions = stride_definitions
    
    def generate_threats(self, component: ComponentAnalysis, stride_category: str) -> List[ThreatModel]:
        """Generate rule-based threats for a component and specific STRIDE category."""
        component_type = component.type
        component_name = component.name
        details = component.details
        
        threat_generators = {
            'S': self._generate_spoofing_threats,
            'T': self._generate_tampering_threats,
            'R': self._generate_repudiation_threats,
            'I': self._generate_information_disclosure_threats,
            'D': self._generate_dos_threats,
            'E': self._generate_elevation_threats
        }
        
        generator = threat_generators.get(stride_category)
        if generator:
            return generator(component_name, component_type, details)
        
        return []
    
    def _generate_spoofing_threats(self, name: str, comp_type: str, details: Dict) -> List[ThreatModel]:
        """Generate spoofing threats."""
        threats = []
        
        if comp_type == 'External Entity':
            threats.append(ThreatModel(
                component_name=name,
                stride_category='S',
                threat_description=f'An attacker could impersonate the {name} entity using stolen credentials or by exploiting weak authentication mechanisms to gain unauthorized system access.',
                mitigation_suggestion='Implement multi-factor authentication, certificate-based authentication, and regular credential rotation policies.',
                impact='High',
                likelihood='Medium',
                references=['CWE-287: Improper Authentication', 'OWASP A07:2021 – Identification and Authentication Failures'],
                risk_score='High'
            ))
        elif comp_type == 'Process':
            threats.append(ThreatModel(
                component_name=name,
                stride_category='S',
                threat_description=f'An attacker could spoof the identity of the {name} process to other system components, potentially bypassing security controls.',
                mitigation_suggestion='Implement process authentication, code signing, and service-to-service authentication mechanisms.',
                impact='Medium',
                likelihood='Low',
                references=['CWE-346: Origin Validation Error', 'NIST SP 800-63B'],
                risk_score='Medium'
            ))
        
        return threats
    
    def _generate_tampering_threats(self, name: str, comp_type: str, details: Dict) -> List[ThreatModel]:
        """Generate tampering threats."""
        threats = []
        
        if comp_type == 'Data Store':
            threats.append(ThreatModel(
                component_name=name,
                stride_category='T',
                threat_description=f'An attacker with database access could modify or corrupt critical data in {name}, leading to data integrity issues and business disruption.',
                mitigation_suggestion='Implement database access controls, audit logging, data integrity constraints, and regular backup verification.',
                impact='High',
                likelihood='Medium',
                references=['CWE-89: SQL Injection', 'OWASP A03:2021 – Injection'],
                risk_score='High'
            ))
        elif comp_type == 'Data Flow':
            source = details.get('source', 'source')
            dest = details.get('destination', 'destination')
            threats.append(ThreatModel(
                component_name=name,
                stride_category='T',
                threat_description=f'An attacker could intercept and modify data transmitted between {source} and {dest} through man-in-the-middle attacks.',
                mitigation_suggestion='Use TLS encryption, implement message authentication codes (MAC), and validate data integrity at endpoints.',
                impact='High',
                likelihood='Medium',
                references=['CWE-345: Insufficient Verification of Data Authenticity', 'OWASP A02:2021 – Cryptographic Failures'],
                risk_score='High'
            ))
        
        return threats
    
    def _generate_repudiation_threats(self, name: str, comp_type: str, details: Dict) -> List[ThreatModel]:
        """Generate repudiation threats."""
        threats = []
        
        if comp_type in ['Process', 'Data Store']:
            threats.append(ThreatModel(
                component_name=name,
                stride_category='R',
                threat_description=f'Users or administrators could deny performing critical actions in {name} due to insufficient audit logging and non-repudiation controls.',
                mitigation_suggestion='Implement comprehensive audit logging, digital signatures for critical transactions, and tamper-evident log storage.',
                impact='Medium',
                likelihood='Low',
                references=['CWE-778: Insufficient Logging', 'NIST SP 800-92'],
                risk_score='Medium'
            ))
        
        return threats
    
    def _generate_information_disclosure_threats(self, name: str, comp_type: str, details: Dict) -> List[ThreatModel]:
        """Generate information disclosure threats."""
        threats = []
        
        if comp_type == 'Data Store':
            threats.append(ThreatModel(
                component_name=name,
                stride_category='I',
                threat_description=f'Unauthorized access to {name} could result in exposure of sensitive data through inadequate access controls or data breaches.',
                mitigation_suggestion='Implement role-based access control, data encryption at rest, data classification, and regular access reviews.',
                impact='Critical',
                likelihood='Medium',
                references=['CWE-200: Exposure of Sensitive Information', 'OWASP A01:2021 – Broken Access Control'],
                risk_score='Critical'
            ))
        elif comp_type == 'Data Flow':
            threats.append(ThreatModel(
                component_name=name,
                stride_category='I',
                threat_description=f'Sensitive data transmitted through {name} could be intercepted by attackers through network sniffing or inadequate encryption.',
                mitigation_suggestion='Use strong encryption in transit (TLS 1.3), implement proper key management, and avoid transmitting sensitive data when possible.',
                impact='High',
                likelihood='Medium',
                references=['CWE-319: Cleartext Transmission of Sensitive Information', 'OWASP A02:2021 – Cryptographic Failures'],
                risk_score='High'
            ))
        
        return threats
    
    def _generate_dos_threats(self, name: str, comp_type: str, details: Dict) -> List[ThreatModel]:
        """Generate denial of service threats."""
        threats = []
        
        if comp_type in ['Process', 'Data Store']:
            threats.append(ThreatModel(
                component_name=name,
                stride_category='D',
                threat_description=f'An attacker could overwhelm {name} with excessive requests or resource consumption, causing service unavailability for legitimate users.',
                mitigation_suggestion='Implement rate limiting, resource quotas, DDoS protection, and proper capacity planning with monitoring.',
                impact='Medium',
                likelihood='Medium',
                references=['CWE-400: Uncontrolled Resource Consumption', 'OWASP A06:2021 – Vulnerable and Outdated Components'],
                risk_score='Medium'
            ))
        
        return threats
    
    def _generate_elevation_threats(self, name: str, comp_type: str, details: Dict) -> List[ThreatModel]:
        """Generate privilege escalation threats."""
        threats = []
        
        if comp_type == 'Process':
            threats.append(ThreatModel(
                component_name=name,
                stride_category='E',
                threat_description=f'An attacker could exploit vulnerabilities in {name} to gain elevated privileges beyond their authorized access level.',
                mitigation_suggestion='Run processes with least privilege, implement proper input validation, use sandboxing, and regular security updates.',
                impact='Critical',
                likelihood='Low',
                references=['CWE-269: Improper Privilege Management', 'OWASP A01:2021 – Broken Access Control'],
                risk_score='High'
            ))
        
        return threats