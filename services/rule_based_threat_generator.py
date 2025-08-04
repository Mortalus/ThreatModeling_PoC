"""
Rule-based threat generator as fallback for LLM.
"""
import logging
from typing import List, Dict, Any, Tuple
from models.threat_models import ThreatModel, ComponentAnalysis

logger = logging.getLogger(__name__)

class RuleBasedThreatGenerator:
    """Rule-based fallback threat generator."""
    
    def __init__(self, stride_definitions: Dict[str, Tuple[str, str]]):
        self.stride_definitions = stride_definitions
    
    def generate_threats(self, component: ComponentAnalysis, 
                        cat_letter: str, cat_name: str, cat_def: str) -> List[ThreatModel]:
        """Generate rule-based threats for a component and STRIDE category."""
        threat_generators = {
            'S': self._generate_spoofing_threats,
            'T': self._generate_tampering_threats,
            'R': self._generate_repudiation_threats,
            'I': self._generate_information_disclosure_threats,
            'D': self._generate_dos_threats,
            'E': self._generate_elevation_threats
        }
        
        generator = threat_generators.get(cat_letter)
        if generator:
            threats = generator(component)
            logger.debug(f"Generated {len(threats)} rule-based {cat_name} threats for {component.name}")
            return threats
        
        return []
    
    def _generate_spoofing_threats(self, component: ComponentAnalysis) -> List[ThreatModel]:
        """Generate spoofing threats."""
        threats = []
        
        if component.type == 'External Entity':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='S',
                threat_description=f'An attacker could impersonate the {component.name} entity using stolen credentials or by exploiting weak authentication mechanisms to gain unauthorized system access.',
                mitigation_suggestion='Implement multi-factor authentication, certificate-based authentication, and regular credential rotation policies. Use mutual TLS for service-to-service authentication.',
                impact='High',
                likelihood='Medium',
                references=['CWE-287: Improper Authentication', 'OWASP A07:2021 – Identification and Authentication Failures'],
                risk_score='High'
            ))
            
        elif component.type == 'Process':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='S',
                threat_description=f'An attacker could spoof the identity of the {component.name} process to other system components, potentially bypassing security controls and gaining unauthorized access.',
                mitigation_suggestion='Implement process authentication using code signing, service-to-service authentication mechanisms, and use secure communication channels with mutual authentication.',
                impact='Medium',
                likelihood='Low',
                references=['CWE-346: Origin Validation Error', 'NIST SP 800-63B'],
                risk_score='Medium'
            ))
            
        elif component.type == 'API':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='S',
                threat_description=f'API clients could be spoofed to make unauthorized requests to {component.name}, potentially accessing sensitive data or functionality.',
                mitigation_suggestion='Implement API key authentication, OAuth 2.0 with proper token validation, rate limiting per client, and monitor for anomalous request patterns.',
                impact='High',
                likelihood='Medium',
                references=['OWASP API Security Top 10 - API2:2019', 'RFC 6749 - OAuth 2.0'],
                risk_score='High'
            ))
        
        return threats
    
    def _generate_tampering_threats(self, component: ComponentAnalysis) -> List[ThreatModel]:
        """Generate tampering threats."""
        threats = []
        
        if component.type == 'Data Store':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='T',
                threat_description=f'An attacker with database access could modify or corrupt critical data in {component.name}, leading to data integrity issues and potential business disruption.',
                mitigation_suggestion='Implement database access controls with least privilege, enable audit logging for all data modifications, use database integrity constraints, and maintain regular validated backups.',
                impact='High',
                likelihood='Medium',
                references=['CWE-89: SQL Injection', 'OWASP A03:2021 – Injection'],
                risk_score='High'
            ))
            
        elif component.type == 'Data Flow':
            source = component.details.get('source', 'source')
            dest = component.details.get('destination', 'destination')
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='T',
                threat_description=f'An attacker could intercept and modify data transmitted between {source} and {dest} through man-in-the-middle attacks, compromising data integrity.',
                mitigation_suggestion='Use TLS 1.3 encryption for all data in transit, implement message authentication codes (HMAC), validate data integrity at both endpoints, and use certificate pinning where appropriate.',
                impact='High',
                likelihood='Medium',
                references=['CWE-345: Insufficient Verification of Data Authenticity', 'OWASP A02:2021 – Cryptographic Failures'],
                risk_score='High'
            ))
            
        elif component.type == 'Process':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='T',
                threat_description=f'The {component.name} process could be compromised to modify its behavior or output, potentially affecting downstream components and data integrity.',
                mitigation_suggestion='Implement runtime application self-protection (RASP), use code integrity checks, deploy in immutable containers, and monitor for unauthorized process modifications.',
                impact='High',
                likelihood='Low',
                references=['CWE-494: Download of Code Without Integrity Check', 'NIST SP 800-190'],
                risk_score='Medium'
            ))
        
        return threats
    
    def _generate_repudiation_threats(self, component: ComponentAnalysis) -> List[ThreatModel]:
        """Generate repudiation threats."""
        threats = []
        
        if component.type in ['Process', 'Data Store']:
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='R',
                threat_description=f'Users or administrators could deny performing critical actions in {component.name} due to insufficient audit logging and non-repudiation controls.',
                mitigation_suggestion='Implement comprehensive audit logging with tamper-evident storage, use digital signatures for critical transactions, ensure logs include user identity, timestamp, and action details.',
                impact='Medium',
                likelihood='Low',
                references=['CWE-778: Insufficient Logging', 'NIST SP 800-92'],
                risk_score='Medium'
            ))
            
        elif component.type == 'External Entity':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='R',
                threat_description=f'The {component.name} entity could deny initiating transactions or requests, making it difficult to prove accountability in security incidents.',
                mitigation_suggestion='Implement transaction logging with cryptographic proof of origin, use blockchain or similar immutable ledger for critical operations, and maintain detailed access logs.',
                impact='Medium',
                likelihood='Medium',
                references=['ISO 27001 A.12.4.1', 'PCI DSS Requirement 10'],
                risk_score='Medium'
            ))
        
        return threats
    
    def _generate_information_disclosure_threats(self, component: ComponentAnalysis) -> List[ThreatModel]:
        """Generate information disclosure threats."""
        threats = []
        
        if component.type == 'Data Store':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='I',
                threat_description=f'Unauthorized access to {component.name} could result in exposure of sensitive data through inadequate access controls, misconfiguration, or data breaches.',
                mitigation_suggestion='Implement role-based access control (RBAC), encrypt data at rest using AES-256, classify and label sensitive data, conduct regular access reviews, and use data loss prevention (DLP) tools.',
                impact='Critical',
                likelihood='Medium',
                references=['CWE-200: Exposure of Sensitive Information', 'OWASP A01:2021 – Broken Access Control'],
                risk_score='Critical'
            ))
            
        elif component.type == 'Data Flow':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='I',
                threat_description=f'Sensitive data transmitted through {component.name} could be intercepted by attackers through network sniffing, SSL/TLS vulnerabilities, or inadequate encryption.',
                mitigation_suggestion='Use strong encryption in transit (TLS 1.3), implement perfect forward secrecy, avoid transmitting sensitive data when possible, and use VPN or dedicated secure channels for highly sensitive data.',
                impact='High',
                likelihood='Medium',
                references=['CWE-319: Cleartext Transmission of Sensitive Information', 'OWASP A02:2021 – Cryptographic Failures'],
                risk_score='High'
            ))
            
        elif component.type == 'Process':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='I',
                threat_description=f'The {component.name} process might expose sensitive information through error messages, logs, or debug interfaces accessible to unauthorized users.',
                mitigation_suggestion='Implement proper error handling without exposing system details, sanitize log outputs, disable debug interfaces in production, and use structured logging with classification.',
                impact='Medium',
                likelihood='Medium',
                references=['CWE-209: Information Exposure Through Error Messages', 'OWASP A05:2021 – Security Misconfiguration'],
                risk_score='Medium'
            ))
        
        return threats
    
    def _generate_dos_threats(self, component: ComponentAnalysis) -> List[ThreatModel]:
        """Generate denial of service threats."""
        threats = []
        
        if component.type in ['Process', 'Data Store', 'API']:
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='D',
                threat_description=f'An attacker could overwhelm {component.name} with excessive requests or resource consumption, causing service unavailability for legitimate users.',
                mitigation_suggestion='Implement rate limiting, request throttling, resource quotas, deploy DDoS protection, use circuit breakers, implement proper capacity planning with auto-scaling.',
                impact='Medium',
                likelihood='Medium',
                references=['CWE-400: Uncontrolled Resource Consumption', 'OWASP A06:2021 – Vulnerable and Outdated Components'],
                risk_score='Medium'
            ))
            
        elif component.type == 'Data Flow':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='D',
                threat_description=f'The data flow {component.name} could be disrupted through network attacks, causing communication failures and service degradation.',
                mitigation_suggestion='Implement redundant network paths, use message queuing for resilience, set appropriate timeouts and retries, monitor network health, and implement circuit breakers.',
                impact='Medium',
                likelihood='Low',
                references=['CWE-920: Improper Restriction of Power Consumption', 'RFC 4987 - TCP SYN Flooding'],
                risk_score='Low'
            ))
        
        return threats
    
    def _generate_elevation_threats(self, component: ComponentAnalysis) -> List[ThreatModel]:
        """Generate privilege escalation threats."""
        threats = []
        
        if component.type == 'Process':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='E',
                threat_description=f'An attacker could exploit vulnerabilities in {component.name} to gain elevated privileges beyond their authorized access level, potentially compromising the entire system.',
                mitigation_suggestion='Run processes with least privilege, implement proper input validation and sanitization, use sandboxing and containerization, apply security patches promptly, and use privilege separation.',
                impact='Critical',
                likelihood='Low',
                references=['CWE-269: Improper Privilege Management', 'OWASP A01:2021 – Broken Access Control'],
                risk_score='High'
            ))
            
        elif component.type == 'API':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='E',
                threat_description=f'Attackers could exploit authorization flaws in {component.name} API to access administrative functions or perform actions beyond their permissions.',
                mitigation_suggestion='Implement robust authorization checks for every API endpoint, use role-based access control (RBAC), validate user permissions on each request, and audit authorization decisions.',
                impact='High',
                likelihood='Medium',
                references=['OWASP API Security Top 10 - API5:2019', 'CWE-285: Improper Authorization'],
                risk_score='High'
            ))
            
        elif component.type == 'External Entity':
            threats.append(ThreatModel(
                component_name=component.name,
                stride_category='E',
                threat_description=f'A compromised {component.name} entity could attempt to escalate privileges through exploitation of trust relationships or authentication weaknesses.',
                mitigation_suggestion='Implement zero-trust architecture principles, validate all inputs from external entities, use principle of least privilege, and monitor for privilege escalation attempts.',
                impact='High',
                likelihood='Low',
                references=['NIST Zero Trust Architecture SP 800-207', 'CWE-250: Execution with Unnecessary Privileges'],
                risk_score='Medium'
            ))
        
        return threats