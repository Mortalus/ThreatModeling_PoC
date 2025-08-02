#!/usr/bin/env python3
"""
DFD to Threats Generator Script - Improved Version

This script analyzes DFD (Data Flow Diagram) components and generates realistic threats
using the STRIDE methodology with intelligent filtering and risk-based prioritization.

Key improvements:
- Component-specific STRIDE mapping
- Risk-based component prioritization
- Advanced threat deduplication
- Quality filtering for realistic results
"""

import os
import json
import logging
import difflib
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import threading
import time
import sys

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def get_config():
    """Get configuration from environment with defaults."""
    return {
        'llm_provider': os.getenv('LLM_PROVIDER', 'scaleway'),
        'llm_model': os.getenv('LLM_MODEL', 'llama-3.3-70b-instruct'),
        'local_llm_endpoint': os.getenv('LOCAL_LLM_ENDPOINT', 'http://localhost:11434/api/generate'),
        'custom_system_prompt': os.getenv('CUSTOM_SYSTEM_PROMPT', ''),
        'timeout': int(os.getenv('PIPELINE_TIMEOUT', '5000')),
        'input_dir': os.getenv('INPUT_DIR', './input_documents'),
        'output_dir': os.getenv('OUTPUT_DIR', './output'),
        'dfd_input_path': os.getenv('DFD_INPUT_PATH', './output/dfd_components.json'),
        'threats_output_path': os.getenv('THREATS_OUTPUT_PATH', './output/identified_threats.json'),
        'scw_api_url': os.getenv('SCW_API_URL', 'https://api.scaleway.ai/v1'),
        'scw_secret_key': os.getenv('SCW_SECRET_KEY') or os.getenv('SCW_API_KEY') or os.getenv('SCALEWAY_API_KEY'),
        'max_tokens': int(os.getenv('MAX_TOKENS', '2048')),
        'temperature': float(os.getenv('TEMPERATURE', '0.4')),
        'max_workers': int(os.getenv('MAX_WORKERS', '1')),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'max_components_to_analyze': int(os.getenv('MAX_COMPONENTS_TO_ANALYZE', '20')),
        'min_risk_score': int(os.getenv('MIN_RISK_SCORE', '3'))
    }

# Get configuration
config = get_config()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config['log_level']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs(config['output_dir'], exist_ok=True)

# --- Component-Specific STRIDE Mappings ---
COMPONENT_STRIDE_MAPPING = {
    'External Entity': ['S'],  # Primarily Spoofing concerns
    'Process': ['S', 'T', 'R', 'I', 'D', 'E'],  # All STRIDE categories
    'Data Store': ['T', 'R', 'I', 'D'],  # No Spoofing or Elevation typically
    'Data Flow': ['T', 'I', 'D'],  # Tampering, Info Disclosure, DoS
}

# Risk-based threat limits per component type
MAX_THREATS_PER_COMPONENT = {
    'External Entity': 2,
    'Process': 3,
    'Data Store': 3,
    'Data Flow': 2
}

# Risk assessment keywords
HIGH_RISK_KEYWORDS = [
    'database', 'db', 'store', 'repository', 'cache',
    'authentication', 'auth', 'login', 'user',
    'payment', 'financial', 'money', 'transaction',
    'admin', 'management', 'control',
    'api', 'service', 'server',
    'external', 'third-party', 'internet'
]

TRUST_BOUNDARY_KEYWORDS = [
    'external', 'internet', 'public', 'client',
    'browser', 'mobile', 'api', 'web'
]

# --- Configuration ---
class LLMProvider(Enum):
    SCALEWAY = "scaleway"
    OLLAMA = "ollama"

# --- STRIDE Definitions ---
DEFAULT_STRIDE_DEFINITIONS = {
    "S": ("Spoofing", "Illegitimately accessing systems or data by impersonating a user, process, or component."),
    "T": ("Tampering", "Unauthorized modification of data, either in transit or at rest."),  
    "R": ("Repudiation", "A user or system denying that they performed an action, often due to a lack of sufficient proof."),
    "I": ("Information Disclosure", "Exposing sensitive information to unauthorized individuals."),
    "D": ("Denial of Service", "Preventing legitimate users from accessing a system or service."),
    "E": ("Elevation of Privilege", "A user or process gaining rights beyond their authorized level.")
}

def load_stride_definitions() -> Dict[str, tuple]:
    """Load STRIDE definitions from file or use defaults."""
    stride_config_path = os.path.join(config['output_dir'], "stride_config.json")
    if os.path.exists(stride_config_path):
        try:
            with open(stride_config_path, 'r', encoding='utf-8') as f:
                custom_stride = json.load(f)
            logger.info(f"Loaded custom STRIDE definitions from '{stride_config_path}'")
            return {k: (v[0], v[1]) if isinstance(v, list) else v for k, v in custom_stride.items()}
        except Exception as e:
            logger.warning(f"Failed to load custom STRIDE definitions: {e}. Using defaults.")
    
    return DEFAULT_STRIDE_DEFINITIONS

# --- Helper Functions ---
def get_applicable_stride_categories(component_type: str) -> List[str]:
    """Get only the applicable STRIDE categories for a component type."""
    return COMPONENT_STRIDE_MAPPING.get(component_type, ['S', 'T', 'I'])  # Safe default

def should_analyze_component_for_stride(component_type: str, stride_category: str) -> bool:
    """Determine if a component should be analyzed for a specific STRIDE category."""
    applicable_categories = get_applicable_stride_categories(component_type)
    return stride_category in applicable_categories

def calculate_component_risk_score(component: Dict[str, Any]) -> int:
    """Calculate risk score for component prioritization."""
    score = 1  # Base score
    
    name = component.get('name', '').lower()
    comp_type = component.get('type', '').lower()
    details = str(component.get('details', {})).lower()
    
    # High-risk component types
    if comp_type == 'data store':
        score += 3
    elif comp_type == 'external entity':
        score += 2
    elif comp_type == 'process':
        score += 1
    
    # Check for high-risk keywords
    text_to_check = f"{name} {comp_type} {details}"
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in text_to_check:
            score += 2
            break
    
    # Trust boundary crossing
    for keyword in TRUST_BOUNDARY_KEYWORDS:
        if keyword in text_to_check:
            score += 2
            break
    
    # Data flows between different trust zones
    if comp_type == 'data flow':
        details_dict = component.get('details', {})
        source = str(details_dict.get('source', '')).lower()
        dest = str(details_dict.get('destination', '')).lower()
        
        # Cross-boundary flows are higher risk
        external_sources = ['external', 'client', 'browser', 'internet']
        internal_dests = ['database', 'server', 'internal', 'backend']
        
        if any(ext in source for ext in external_sources) and \
           any(int_dest in dest for int_dest in internal_dests):
            score += 3
    
    return min(score, 10)  # Cap at 10

def prioritize_components(components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prioritize components based on risk factors."""
    # Calculate scores and sort
    for component in components:
        component['_risk_score'] = calculate_component_risk_score(component)
    
    # Sort by risk score (highest first)
    components.sort(key=lambda x: x.get('_risk_score', 0), reverse=True)
    
    return components

def should_analyze_component(component: Dict[str, Any]) -> bool:
    """Determine if component should be analyzed based on risk."""
    risk_score = component.get('_risk_score', 0)
    return risk_score >= config['min_risk_score']

# --- LLM Client Factory ---
class LLMClient:
    def __init__(self):
        self.provider = LLMProvider(config['llm_provider'].lower())
        self.model = config['llm_model']
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the LLM client with error handling."""
        try:
            if self.provider == LLMProvider.SCALEWAY:
                if not config['scw_secret_key']:
                    logger.warning("No Scaleway API key found, LLM features will be disabled")
                    return
                
                try:
                    from openai import OpenAI
                    self.client = OpenAI(
                        base_url=config['scw_api_url'],
                        api_key=config['scw_secret_key']
                    )
                    logger.info("Scaleway client initialized successfully")
                except ImportError:
                    logger.warning("OpenAI library not available, LLM features will be disabled")
                    
            elif self.provider == LLMProvider.OLLAMA:
                logger.info("Ollama client configured")
            else:
                logger.error(f"Unsupported LLM provider: {self.provider}")
        
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.client = None
    
    def generate(self, prompt: str, json_mode: bool = True) -> str:
        """Generate text using the configured LLM provider."""
        if not self.client and self.provider == LLMProvider.SCALEWAY:
            raise Exception("LLM client not initialized")
            
        try:
            if self.provider == LLMProvider.SCALEWAY:
                messages = [{"role": "user", "content": prompt}]
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": config['max_tokens'],
                    "temperature": config['temperature']
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            
            elif self.provider == LLMProvider.OLLAMA:
                try:
                    import requests
                    
                    if json_mode:
                        prompt = prompt + "\n\nIMPORTANT: Output ONLY valid JSON, no other text."
                    
                    response = requests.post(
                        config['local_llm_endpoint'],
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": config['temperature'],
                                "num_predict": config['max_tokens'],
                            }
                        },
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        return response.json().get('response', '')
                    else:
                        raise Exception(f"Ollama API error: {response.status_code} {response.text}")
                        
                except ImportError:
                    raise Exception("Requests library not available for Ollama")
                
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise

# --- Rule-based Threat Generator (Fallback) ---
class RuleBasedThreatGenerator:
    """Improved fallback threat generator using predefined rules."""
    
    def __init__(self):
        self.stride_definitions = load_stride_definitions()
    
    def generate_threats_for_component(self, component: Dict[str, Any], stride_category: str) -> List[Dict[str, Any]]:
        """Generate rule-based threats for a component and specific STRIDE category."""
        component_type = component.get('type', 'Unknown')
        component_name = component.get('name', 'Unknown')
        
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
            return generator(component_name, component_type, component.get('details', {}))
        
        return []
    
    def _generate_spoofing_threats(self, name: str, comp_type: str, details: Dict) -> List[Dict[str, Any]]:
        """Generate spoofing threats."""
        if comp_type == 'External Entity':
            return [{
                'component_name': name,
                'stride_category': 'S',
                'threat_description': f'An attacker could impersonate the {name} entity using stolen credentials or by exploiting weak authentication mechanisms to gain unauthorized system access.',
                'mitigation_suggestion': 'Implement multi-factor authentication, certificate-based authentication, and regular credential rotation policies.',
                'impact': 'High',
                'likelihood': 'Medium',
                'references': ['CWE-287: Improper Authentication', 'OWASP A07:2021 – Identification and Authentication Failures'],
                'risk_score': 'High'
            }]
        elif comp_type == 'Process':
            return [{
                'component_name': name,
                'stride_category': 'S',
                'threat_description': f'An attacker could spoof the identity of the {name} process to other system components, potentially bypassing security controls.',
                'mitigation_suggestion': 'Implement process authentication, code signing, and service-to-service authentication mechanisms.',
                'impact': 'Medium',
                'likelihood': 'Low',
                'references': ['CWE-346: Origin Validation Error', 'NIST SP 800-63B'],
                'risk_score': 'Medium'
            }]
        return []
    
    def _generate_tampering_threats(self, name: str, comp_type: str, details: Dict) -> List[Dict[str, Any]]:
        """Generate tampering threats."""
        if comp_type == 'Data Store':
            return [{
                'component_name': name,
                'stride_category': 'T',
                'threat_description': f'An attacker with database access could modify or corrupt critical data in {name}, leading to data integrity issues and business disruption.',
                'mitigation_suggestion': 'Implement database access controls, audit logging, data integrity constraints, and regular backup verification.',
                'impact': 'High',
                'likelihood': 'Medium',
                'references': ['CWE-89: SQL Injection', 'OWASP A03:2021 – Injection'],
                'risk_score': 'High'
            }]
        elif comp_type == 'Data Flow':
            source = details.get('source', 'source')
            dest = details.get('destination', 'destination')
            return [{
                'component_name': name,
                'stride_category': 'T',
                'threat_description': f'An attacker could intercept and modify data transmitted between {source} and {dest} through man-in-the-middle attacks.',
                'mitigation_suggestion': 'Use TLS encryption, implement message authentication codes (MAC), and validate data integrity at endpoints.',
                'impact': 'High',
                'likelihood': 'Medium',
                'references': ['CWE-345: Insufficient Verification of Data Authenticity', 'OWASP A02:2021 – Cryptographic Failures'],
                'risk_score': 'High'
            }]
        return []
    
    def _generate_repudiation_threats(self, name: str, comp_type: str, details: Dict) -> List[Dict[str, Any]]:
        """Generate repudiation threats."""
        if comp_type in ['Process', 'Data Store']:
            return [{
                'component_name': name,
                'stride_category': 'R',
                'threat_description': f'Users or administrators could deny performing critical actions in {name} due to insufficient audit logging and non-repudiation controls.',
                'mitigation_suggestion': 'Implement comprehensive audit logging, digital signatures for critical transactions, and tamper-evident log storage.',
                'impact': 'Medium',
                'likelihood': 'Low',
                'references': ['CWE-778: Insufficient Logging', 'NIST SP 800-92'],
                'risk_score': 'Medium'
            }]
        return []
    
    def _generate_information_disclosure_threats(self, name: str, comp_type: str, details: Dict) -> List[Dict[str, Any]]:
        """Generate information disclosure threats."""
        if comp_type == 'Data Store':
            return [{
                'component_name': name,
                'stride_category': 'I',
                'threat_description': f'Unauthorized access to {name} could result in exposure of sensitive data through inadequate access controls or data breaches.',
                'mitigation_suggestion': 'Implement role-based access control, data encryption at rest, data classification, and regular access reviews.',
                'impact': 'Critical',
                'likelihood': 'Medium',
                'references': ['CWE-200: Exposure of Sensitive Information', 'OWASP A01:2021 – Broken Access Control'],
                'risk_score': 'Critical'
            }]
        elif comp_type == 'Data Flow':
            return [{
                'component_name': name,
                'stride_category': 'I',
                'threat_description': f'Sensitive data transmitted through {name} could be intercepted by attackers through network sniffing or inadequate encryption.',
                'mitigation_suggestion': 'Use strong encryption in transit (TLS 1.3), implement proper key management, and avoid transmitting sensitive data when possible.',
                'impact': 'High',
                'likelihood': 'Medium',
                'references': ['CWE-319: Cleartext Transmission of Sensitive Information', 'OWASP A02:2021 – Cryptographic Failures'],
                'risk_score': 'High'
            }]
        return []
    
    def _generate_dos_threats(self, name: str, comp_type: str, details: Dict) -> List[Dict[str, Any]]:
        """Generate denial of service threats."""
        if comp_type in ['Process', 'Data Store']:
            return [{
                'component_name': name,
                'stride_category': 'D',
                'threat_description': f'An attacker could overwhelm {name} with excessive requests or resource consumption, causing service unavailability for legitimate users.',
                'mitigation_suggestion': 'Implement rate limiting, resource quotas, DDoS protection, and proper capacity planning with monitoring.',
                'impact': 'Medium',
                'likelihood': 'Medium',
                'references': ['CWE-400: Uncontrolled Resource Consumption', 'OWASP A06:2021 – Vulnerable and Outdated Components'],
                'risk_score': 'Medium'
            }]
        return []
    
    def _generate_elevation_threats(self, name: str, comp_type: str, details: Dict) -> List[Dict[str, Any]]:
        """Generate privilege escalation threats."""
        if comp_type == 'Process':
            return [{
                'component_name': name,
                'stride_category': 'E',
                'threat_description': f'An attacker could exploit vulnerabilities in {name} to gain elevated privileges beyond their authorized access level.',
                'mitigation_suggestion': 'Run processes with least privilege, implement proper input validation, use sandboxing, and regular security updates.',
                'impact': 'Critical',
                'likelihood': 'Low',
                'references': ['CWE-269: Improper Privilege Management', 'OWASP A01:2021 – Broken Access Control'],
                'risk_score': 'High'
            }]
        return []

# --- Advanced Threat Processing ---
def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    import re
    text = re.sub(r'\s+', ' ', text.lower().strip())
    text = re.sub(r'\b(an?|the)\b', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text

def are_similar_threats(threat1: Dict, threat2: Dict, threshold: float = 0.7) -> bool:
    """Check if two threats are semantically similar."""
    desc1 = normalize_text(threat1.get('threat_description', ''))
    desc2 = normalize_text(threat2.get('threat_description', ''))
    
    # Same component and STRIDE category
    if (threat1.get('component_name') == threat2.get('component_name') and 
        threat1.get('stride_category') == threat2.get('stride_category')):
        
        similarity = difflib.SequenceMatcher(None, desc1, desc2).ratio()
        return similarity > threshold
    
    return False

def advanced_threat_deduplication(threats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Advanced deduplication based on semantic similarity."""
    unique_threats = []
    processed_indices: Set[int] = set()
    
    for i, threat in enumerate(threats):
        if i in processed_indices:
            continue
        
        # Find similar threats
        similar_threats = [threat]
        for j, other_threat in enumerate(threats[i+1:], i+1):
            if j not in processed_indices and are_similar_threats(threat, other_threat):
                similar_threats.append(other_threat)
                processed_indices.add(j)
        
        # Keep the threat with highest risk score
        risk_order = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
        best_threat = max(similar_threats, 
                         key=lambda t: risk_order.get(t.get('risk_score', 'Low'), 0))
        
        unique_threats.append(best_threat)
        processed_indices.add(i)
    
    return unique_threats

def filter_quality_threats(threats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out low-quality or generic threats."""
    GENERIC_PHRASES = [
        'an attacker could',
        'unauthorized access',
        'malicious user might',
        'potential security risk',
        'vulnerability may exist'
    ]
    
    MIN_DESCRIPTION_LENGTH = 50
    quality_threats = []
    
    for threat in threats:
        description = threat.get('threat_description', '').lower()
        
        # Skip if too short
        if len(description) < MIN_DESCRIPTION_LENGTH:
            continue
        
        # Skip if too generic (more than 2 generic phrases)
        generic_count = sum(1 for phrase in GENERIC_PHRASES if phrase in description)
        if generic_count > 2:
            continue
        
        # Skip if mitigation is too vague
        mitigation = threat.get('mitigation_suggestion', '')
        if len(mitigation) < 30 or 'implement security measures' in mitigation.lower():
            continue
        
        quality_threats.append(threat)
    
    return quality_threats

# --- Improved Threat Analyzer ---
class ImprovedThreatAnalyzer:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client
        self.stride_definitions = load_stride_definitions()
        self.rule_generator = RuleBasedThreatGenerator()
        
        # Focused prompt for realistic threat analysis
        self.threat_prompt_template = """
You are a cybersecurity architect specializing in realistic threat modeling. Analyze this DFD component and generate ONLY the 1-2 most realistic and significant threats for the specified STRIDE category.

**Component:**
{component_info}

**STRIDE Category:** {stride_category} ({stride_name})
{stride_definition}

**Requirements:**
1. Generate ONLY 1-2 threats that are:
   - Realistic and technically feasible
   - Specific to this component type and context
   - Significant business/security impact
   - Based on actual attack patterns
2. Avoid generic threats - be specific to the component's function
3. Focus on threats that cross trust boundaries or affect critical assets
4. Each threat must be distinct and actionable

**Output valid JSON only:**
{{
  "threats": [
    {{
      "component_name": "{component_name}",
      "stride_category": "{stride_category}",
      "threat_description": "Specific, realistic threat description focusing on actual attack scenarios",
      "mitigation_suggestion": "Actionable, specific mitigation strategies with implementation details",
      "impact": "Low|Medium|High",
      "likelihood": "Low|Medium|High",
      "references": ["Relevant security standards or attack frameworks"],
      "risk_score": "Critical|High|Medium|Low"
    }}
  ]
}}
"""
    
    def analyze_component(self, component: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze component with improved filtering and realistic threat generation."""
        component_name = component.get("name", "Unknown")
        component_type = component.get("type", "Unknown")
        
        logger.info(f"Analyzing component: {component_name} ({component_type})")
        
        # Get applicable STRIDE categories for this component type
        applicable_categories = get_applicable_stride_categories(component_type)
        max_threats = MAX_THREATS_PER_COMPONENT.get(component_type, 2)
        
        logger.info(f"  Applicable STRIDE categories: {applicable_categories}")
        
        all_threats = []
        
        # Analyze only applicable categories
        for cat_letter in applicable_categories:
            if cat_letter not in self.stride_definitions:
                continue
                
            cat_name, cat_def = self.stride_definitions[cat_letter]
            logger.info(f"  Analyzing {cat_name}")
            
            try:
                if self.llm and self.llm.client:
                    threats = self._analyze_with_llm(component, cat_letter, cat_name, cat_def)
                else:
                    threats = self._analyze_with_rules(component, cat_letter)
                
                # Limit threats per category to 1 for focus
                threats = threats[:1]
                all_threats.extend(threats)
                
            except Exception as e:
                logger.warning(f"    Error analyzing {cat_name}: {e}")
                continue
        
        # Limit total threats per component
        all_threats = all_threats[:max_threats]
        
        logger.info(f"  Generated {len(all_threats)} threat(s)")
        return all_threats
    
    def _analyze_with_llm(self, component: Dict[str, Any], cat_letter: str, 
                         cat_name: str, cat_def: str) -> List[Dict[str, Any]]:
        """Analyze with LLM using improved prompt."""
        component_str = json.dumps(component, indent=2)
        component_name = component.get("name", "Unknown")
        
        prompt = self.threat_prompt_template.format(
            component_info=component_str,
            component_name=component_name,
            stride_category=cat_letter,
            stride_name=cat_name,
            stride_definition=cat_def
        )
        
        response = self.llm.generate(prompt, json_mode=True)
        
        # Clean and parse response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        
        try:
            data = json.loads(response)
            
            if isinstance(data, dict) and isinstance(data.get("threats"), list):
                threats = data["threats"]
                
                # Post-process threats
                for threat in threats:
                    threat['component_name'] = component_name
                    threat['risk_score'] = self.calculate_risk_score(
                        threat.get('impact', 'Low'),
                        threat.get('likelihood', 'Low')
                    )
                    if not isinstance(threat.get('references'), list):
                        threat['references'] = [f"OWASP Top 10", f"STRIDE {cat_name}"]
                
                return threats
        except json.JSONDecodeError as e:
            logger.warning(f"    JSON decode error: {e}")
        
        return []
    
    def _analyze_with_rules(self, component: Dict[str, Any], cat_letter: str) -> List[Dict[str, Any]]:
        """Analyze with rules, filtered by category."""
        return self.rule_generator.generate_threats_for_component(component, cat_letter)
    
    def calculate_risk_score(self, impact: str, likelihood: str) -> str:
        """Calculate risk score based on impact and likelihood."""
        if impact == "High" and likelihood in ["Medium", "High"]:
            return "Critical"
        elif (impact == "High" and likelihood == "Low") or (impact == "Medium" and likelihood == "High"):
            return "High"
        elif (impact == "Medium" and likelihood in ["Medium", "Low"]) or (impact == "Low" and likelihood == "High"):
            return "Medium"
        else:
            return "Low"

# --- Main Functions ---
def load_dfd_data(filepath: str) -> Dict[str, Any]:
    """Load DFD data from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle nested structure
        if 'dfd' in data:
            logger.info("Found nested DFD structure, extracting 'dfd' content")
            return data['dfd']
        
        return data
    except FileNotFoundError:
        logger.error(f"DFD file not found at '{filepath}'")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from '{filepath}': {e}")
        raise

def extract_components(dfd_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract analyzable components from DFD data."""
    components = []
    
    component_mappings = {
        'external_entities': 'External Entity',
        'processes': 'Process', 
        'assets': 'Data Store',
        'data_stores': 'Data Store',
        'data_flows': 'Data Flow'
    }
    
    for key, component_type in component_mappings.items():
        if key in dfd_data:
            items = dfd_data[key]
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, str):
                        components.append({
                            "type": component_type,
                            "name": item,
                            "details": {"identifier": item}
                        })
                    elif isinstance(item, dict):
                        component = {
                            "type": component_type,
                            "name": item.get('name', item.get('source', item.get('destination', 'Unknown'))),
                            "details": item
                        }
                        # For data flows, create descriptive name
                        if key == 'data_flows' and 'source' in item and 'destination' in item:
                            component['name'] = f"{item['source']} → {item['destination']}"
                        components.append(component)
    
    return components

def write_progress(step: int, current: int, total: int, message: str, details: str = ""):
    """Write progress information to a file that the frontend can read."""
    try:
        progress_data = {
            'step': step,
            'current': current,
            'total': total,
            'progress': round((current / total * 100) if total > 0 else 0, 1),
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        progress_file = os.path.join(config['output_dir'], f'step_{step}_progress.json')
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
            
    except Exception as e:
        logger.warning(f"Could not write progress: {e}")

def check_kill_signal(step: int) -> bool:
    """Check if user requested to kill this step."""
    try:
        kill_file = os.path.join(config['output_dir'], f'step_{step}_kill.flag')
        if os.path.exists(kill_file):
            logger.info("Kill signal detected, stopping execution")
            return True
        return False
    except:
        return False

def main():
    """Improved main execution function with realistic threat generation."""
    logger.info("=== Starting Realistic Threat Modeling Analysis ===")
    
    # Initialize progress
    write_progress(3, 0, 100, "Initializing threat analysis", "Loading components")
    
    # Initialize clients
    llm_client = None
    try:
        llm_client = LLMClient()
        if llm_client.client:
            logger.info(f"Initialized LLM client: {config['llm_provider']} with model {config['llm_model']}")
        else:
            logger.info("LLM client not available, using rule-based generation")
        
        analyzer = ImprovedThreatAnalyzer(llm_client)
    except Exception as e:
        logger.warning(f"Failed to initialize LLM services: {e}")
        logger.info("Continuing with rule-based threat generation")
        analyzer = ImprovedThreatAnalyzer(None)
    
    # Load and prioritize components
    try:
        write_progress(3, 10, 100, "Loading DFD data", "Reading component definitions")
        dfd_data = load_dfd_data(config['dfd_input_path'])
        components = extract_components(dfd_data)
        
        # Prioritize components by risk
        components = prioritize_components(components)
        
        # Filter to only analyze high-risk components
        high_risk_components = [c for c in components if should_analyze_component(c)]
        
        # Limit total components to analyze
        max_components = config['max_components_to_analyze']
        if len(high_risk_components) > max_components:
            logger.info(f"Limiting analysis to top {max_components} highest risk components")
            high_risk_components = high_risk_components[:max_components]
        
        logger.info(f"Total components: {len(components)}")
        logger.info(f"High-risk components to analyze: {len(high_risk_components)}")
        
        # Log component breakdown
        component_types = {}
        for comp in components:
            comp_type = comp.get('type', 'Unknown')
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
        
        logger.info("Component breakdown:")
        for comp_type, count in component_types.items():
            logger.info(f"  - {comp_type}: {count}")
        
        # Log the components we're analyzing
        logger.info("Components selected for analysis:")
        for comp in high_risk_components[:10]:  # Log first 10
            logger.info(f"  - {comp.get('name')} ({comp.get('type')}) [Risk: {comp.get('_risk_score')}]")
        
        write_progress(3, 20, 100, "Components loaded", f"Found {len(high_risk_components)} high-risk components")
    
    except Exception as e:
        logger.error(f"Failed to load or parse DFD data: {e}")
        write_progress(3, 0, 100, "Failed", f"Error: {str(e)}")
        return 1
    
    # Analyze components
    logger.info("Analyzing components sequentially for stability and quality")
    all_threats = []
    base_progress = 20
    analysis_progress_range = 70  # 20-90% for analysis
    
    for i, component in enumerate(high_risk_components):
        try:
            # Check for kill signal
            if check_kill_signal(3):
                write_progress(3, 90, 100, "Analysis cancelled", "User requested stop")
                return 1
            
            component_name = component.get('name', 'Unknown')
            logger.info(f"Analyzing component {i+1}/{len(high_risk_components)}: {component_name}")
            
            # Update progress
            component_progress = base_progress + int((i / len(high_risk_components)) * analysis_progress_range)
            write_progress(
                3, 
                component_progress, 
                100, 
                f"Analyzing component {i+1}/{len(high_risk_components)}", 
                f"Processing: {component_name}"
            )
            
            threats = analyzer.analyze_component(component)
            all_threats.extend(threats)
            
            # Rate limiting for better quality
            if llm_client and llm_client.client:
                time.sleep(1)  # Longer delay for more thoughtful analysis
            
        except Exception as e:
            logger.error(f"Error analyzing component {component_name}: {e}")
            continue
    
    logger.info(f"Generated {len(all_threats)} initial threats")
    
    # Advanced post-processing
    write_progress(3, 90, 100, "Post-processing threats", "Removing duplicates")
    all_threats = advanced_threat_deduplication(all_threats)
    logger.info(f"After deduplication: {len(all_threats)} threats")
    
    write_progress(3, 93, 100, "Post-processing threats", "Quality filtering")
    all_threats = filter_quality_threats(all_threats)
    logger.info(f"After quality filtering: {len(all_threats)} threats")
    
    if not all_threats:
        logger.error("No threats were generated!")
        write_progress(3, 100, 100, "Failed", "No threats generated")
        return 1
    
    # Sort by risk score
    write_progress(3, 95, 100, "Finalizing results", "Sorting by risk score")
    risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    all_threats.sort(key=lambda t: risk_order.get(t.get('risk_score', 'Low'), 0), reverse=True)
    
    # Create comprehensive output
    risk_breakdown = {
        "Critical": sum(1 for t in all_threats if t.get('risk_score') == 'Critical'),
        "High": sum(1 for t in all_threats if t.get('risk_score') == 'High'),
        "Medium": sum(1 for t in all_threats if t.get('risk_score') == 'Medium'),
        "Low": sum(1 for t in all_threats if t.get('risk_score') == 'Low')
    }
    
    output = {
        "threats": all_threats,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "source_dfd": os.path.basename(config['dfd_input_path']),
            "llm_provider": config['llm_provider'],
            "llm_model": config['llm_model'],
            "total_threats": len(all_threats),
            "total_components": len(components),
            "components_analyzed": len(high_risk_components),
            "generation_method": "LLM" if (llm_client and llm_client.client) else "Rule-based",
            "analysis_approach": "Risk-based with STRIDE filtering",
            "min_risk_score": config['min_risk_score'],
            "max_components_analyzed": config['max_components_to_analyze'],
            "risk_breakdown": risk_breakdown,
            "dfd_structure": {
                "project_name": dfd_data.get('project_name', 'Unknown'),
                "industry_context": dfd_data.get('industry_context', 'Unknown')
            }
        }
    }
    
    # Validate output structure
    if not isinstance(output.get('threats'), list):
        logger.error("Invalid output structure - threats must be a list")
        return 1
    
    for i, threat in enumerate(output['threats']):
        if not isinstance(threat, dict):
            logger.error(f"Invalid threat structure at index {i}")
            return 1
        
        required_fields = ['component_name', 'stride_category', 'threat_description', 
                          'mitigation_suggestion', 'impact', 'likelihood']
        for field in required_fields:
            if field not in threat:
                logger.error(f"Missing required field '{field}' in threat {i}")
                return 1
    
    logger.info("Output validation successful")
    
    # Save results
    try:
        write_progress(3, 98, 100, "Saving results", config['threats_output_path'])
        with open(config['threats_output_path'], 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to '{config['threats_output_path']}'")
        write_progress(3, 100, 100, "Complete", f"Generated {len(all_threats)} realistic threats")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        write_progress(3, 100, 100, "Failed", f"Save error: {str(e)}")
        return 1
    
    logger.info("=== Realistic Threat Modeling Analysis Complete ===")
    
    # Print comprehensive summary
    print(f"\n=== Realistic Threat Analysis Summary ===")
    print(f"Total components in DFD: {len(components)}")
    print(f"High-risk components analyzed: {len(high_risk_components)}")
    print(f"Total realistic threats identified: {len(all_threats)}")
    print(f"Critical threats: {risk_breakdown['Critical']}")
    print(f"High threats: {risk_breakdown['High']}")
    print(f"Medium threats: {risk_breakdown['Medium']}")
    print(f"Low threats: {risk_breakdown['Low']}")
    print(f"Analysis method: {'LLM-based' if (llm_client and llm_client.client) else 'Rule-based'}")
    print(f"Average threats per component: {len(all_threats) / len(high_risk_components):.1f}")
    
    # Clean up progress file
    try:
        progress_file = os.path.join(config['output_dir'], f'step_3_progress.json')
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except:
        pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())