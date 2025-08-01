#!/usr/bin/env python3
"""
DFD to Threats Generator Script

This script analyzes DFD (Data Flow Diagram) components and generates threats
using the STRIDE methodology. Compatible with the threat modeling pipeline.

Fixed version with improved error handling and compatibility.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
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
        'max_workers': int(os.getenv('MAX_WORKERS', '1')),  # Sequential for stability
        'log_level': os.getenv('LOG_LEVEL', 'INFO')
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

# --- Configuration ---
class LLMProvider(Enum):
    SCALEWAY = "scaleway"
    OLLAMA = "ollama"

# --- Simple data classes (avoiding Pydantic for compatibility) ---
class Threat:
    def __init__(self, component_name: str, stride_category: str, threat_description: str,
                 mitigation_suggestion: str, impact: str, likelihood: str, 
                 references: List[str] = None, risk_score: str = "Medium"):
        self.component_name = component_name
        self.stride_category = stride_category
        self.threat_description = threat_description
        self.mitigation_suggestion = mitigation_suggestion
        self.impact = impact
        self.likelihood = likelihood
        self.references = references or []
        self.risk_score = risk_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'component_name': self.component_name,
            'stride_category': self.stride_category,
            'threat_description': self.threat_description,
            'mitigation_suggestion': self.mitigation_suggestion,
            'impact': self.impact,
            'likelihood': self.likelihood,
            'references': self.references,
            'risk_score': self.risk_score
        }

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
                
                # Try to import OpenAI
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
                # For Ollama, we'll validate later when making requests
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
                # For Ollama, use requests if available
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
            # Convert to expected format
            return {k: (v[0], v[1]) if isinstance(v, list) else v for k, v in custom_stride.items()}
        except Exception as e:
            logger.warning(f"Failed to load custom STRIDE definitions: {e}. Using defaults.")
    
    return DEFAULT_STRIDE_DEFINITIONS

# --- Rule-based Threat Generator (Fallback) ---
class RuleBasedThreatGenerator:
    """Fallback threat generator using predefined rules."""
    
    def __init__(self):
        self.stride_definitions = load_stride_definitions()
    
    def generate_threats_for_component(self, component: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate rule-based threats for a component."""
        threats = []
        component_type = component.get('type', 'Unknown')
        component_name = component.get('name', 'Unknown')
        
        if component_type == 'External Entity':
            threats.extend(self._generate_external_entity_threats(component_name))
        elif component_type == 'Process':
            threats.extend(self._generate_process_threats(component_name))
        elif component_type == 'Data Store':
            threats.extend(self._generate_data_store_threats(component_name))
        elif component_type == 'Data Flow':
            threats.extend(self._generate_data_flow_threats(component))
        
        return threats
    
    def _generate_external_entity_threats(self, name: str) -> List[Dict[str, Any]]:
        """Generate threats for external entities."""
        return [
            {
                'component_name': name,
                'stride_category': 'S',
                'threat_description': f'An attacker could impersonate the {name} entity to gain unauthorized access.',
                'mitigation_suggestion': 'Implement strong authentication mechanisms such as multi-factor authentication or certificates.',
                'impact': 'High',
                'likelihood': 'Medium',
                'references': ['CWE-287: Improper Authentication', 'OWASP A07:2021 – Identification and Authentication Failures'],
                'risk_score': 'High'
            }
        ]
    
    def _generate_process_threats(self, name: str) -> List[Dict[str, Any]]:
        """Generate threats for processes."""
        return [
            {
                'component_name': name,
                'stride_category': 'T',
                'threat_description': f'An attacker could tamper with the {name} process, modifying its behavior or data.',
                'mitigation_suggestion': 'Implement input validation, code signing, and integrity checks.',
                'impact': 'High',
                'likelihood': 'Medium',
                'references': ['CWE-20: Improper Input Validation', 'OWASP A03:2021 – Injection'],
                'risk_score': 'High'
            },
            {
                'component_name': name,
                'stride_category': 'E',
                'threat_description': f'An attacker could exploit vulnerabilities in {name} to gain elevated privileges.',
                'mitigation_suggestion': 'Run processes with least privilege and implement proper access controls.',
                'impact': 'Critical',
                'likelihood': 'Low',
                'references': ['CWE-269: Improper Privilege Management', 'OWASP A01:2021 – Broken Access Control'],
                'risk_score': 'High'
            }
        ]
    
    def _generate_data_store_threats(self, name: str) -> List[Dict[str, Any]]:
        """Generate threats for data stores."""
        return [
            {
                'component_name': name,
                'stride_category': 'I',
                'threat_description': f'Unauthorized access to {name} could result in sensitive data disclosure.',
                'mitigation_suggestion': 'Implement database access controls, encryption at rest, and audit logging.',
                'impact': 'Critical',
                'likelihood': 'Medium',
                'references': ['CWE-200: Exposure of Sensitive Information', 'OWASP A01:2021 – Broken Access Control'],
                'risk_score': 'Critical'
            },
            {
                'component_name': name,
                'stride_category': 'T',
                'threat_description': f'An attacker could modify or corrupt data stored in {name}.',
                'mitigation_suggestion': 'Implement database integrity constraints and backup procedures.',
                'impact': 'High',
                'likelihood': 'Low',
                'references': ['CWE-89: SQL Injection', 'OWASP A03:2021 – Injection'],
                'risk_score': 'Medium'
            }
        ]
    
    def _generate_data_flow_threats(self, component: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate threats for data flows."""
        details = component.get('details', {})
        source = details.get('source', 'Unknown')
        destination = details.get('destination', 'Unknown')
        component_name = f"{source} → {destination}"
        
        return [
            {
                'component_name': component_name,
                'stride_category': 'I',
                'threat_description': f'Data transmitted between {source} and {destination} could be intercepted.',
                'mitigation_suggestion': 'Use encryption in transit (TLS/HTTPS) and implement secure communication protocols.',
                'impact': 'High',
                'likelihood': 'Medium',
                'references': ['CWE-319: Cleartext Transmission of Sensitive Information', 'OWASP A02:2021 – Cryptographic Failures'],
                'risk_score': 'High'
            },
            {
                'component_name': component_name,
                'stride_category': 'T',
                'threat_description': f'An attacker could intercept and modify data between {source} and {destination}.',
                'mitigation_suggestion': 'Implement message integrity checks and use authenticated encryption.',
                'impact': 'High',
                'likelihood': 'Medium',
                'references': ['CWE-345: Insufficient Verification of Data Authenticity', 'OWASP A02:2021 – Cryptographic Failures'],
                'risk_score': 'High'
            }
        ]

# --- Threat Analysis ---
class ThreatAnalyzer:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client
        self.stride_definitions = load_stride_definitions()
        self.rule_generator = RuleBasedThreatGenerator()
        self.threat_prompt_template = """
You are a cybersecurity architect specializing in threat modeling using the STRIDE methodology.
Your task is to generate 1-2 specific threats for a given DFD component, focusing ONLY on a single STRIDE category.

**DFD Component to Analyze:**
{component_info}

**STRIDE Category to Focus On:**
- **{stride_category} ({stride_name}):** {stride_definition}

**Instructions:**
1. Generate 1-2 distinct and realistic threats for the component that fall **strictly** under the '{stride_name}' category.
2. Be specific and relate the threat directly to the component's type and details.
3. Provide actionable mitigation suggestions based on industry best practices.
4. Provide a realistic risk assessment (Impact, Likelihood, Score).
5. Include relevant security references or standards.
6. Output ONLY a valid JSON object with a single key "threats", containing a list of threat objects.

**JSON Schema:**
{{
  "threats": [
    {{
      "component_name": "string",
      "stride_category": "{stride_category}",
      "threat_description": "string (be specific and detailed)",
      "mitigation_suggestion": "string (actionable recommendations)",
      "impact": "Low|Medium|High",
      "likelihood": "Low|Medium|High",
      "references": ["string (security standards, best practices)"],
      "risk_score": "Critical|High|Medium|Low"
    }}
  ]
}}

**Example for reference:**
If analyzing a Database component for Information Disclosure:
- Threat: SQL injection allowing unauthorized data access
- Mitigation: Input validation, parameterized queries, least privilege access
- Impact: High (sensitive data exposure)
- Likelihood: Medium (common attack vector)
- Risk Score: High
"""
    
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
    
    def analyze_component(self, component: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze a single component for all STRIDE categories."""
        component_name = component.get("name", component.get("details", {}).get("name", component.get("type", "Unknown")))
        
        logger.info(f"Analyzing component: {component_name}")
        
        # If LLM is not available, use rule-based generation
        if not self.llm or not self.llm.client:
            logger.info(f"  Using rule-based threat generation")
            return self.rule_generator.generate_threats_for_component(component)
        
        # Use LLM-based generation
        component_str = json.dumps(component, indent=2)
        all_threats = []
        
        for cat_letter, (cat_name, cat_def) in self.stride_definitions.items():
            logger.info(f"  Generating threats for STRIDE category: {cat_name}")
            
            prompt = self.threat_prompt_template.format(
                component_info=component_str,
                stride_category=cat_letter,
                stride_name=cat_name,
                stride_definition=cat_def
            )
            
            try:
                response = self.llm.generate(prompt, json_mode=True)
                
                # Clean response if needed
                response = response.strip()
                if response.startswith("```json"):
                    response = response[7:]
                if response.endswith("```"):
                    response = response[:-3]
                
                data = json.loads(response)
                
                if isinstance(data, dict) and isinstance(data.get("threats"), list):
                    threats = data["threats"]
                    
                    # Post-process threats
                    for threat in threats:
                        # Ensure component name
                        if not threat.get('component_name'):
                            threat['component_name'] = component_name
                        
                        # Recalculate risk score
                        threat['risk_score'] = self.calculate_risk_score(
                            threat.get('impact', 'Low'),
                            threat.get('likelihood', 'Low')
                        )
                        
                        # Ensure references is a list
                        if not isinstance(threat.get('references'), list):
                            threat['references'] = []
                        
                        # Add default references if none provided
                        if not threat['references']:
                            threat['references'] = [
                                "OWASP Top 10",
                                "NIST Cybersecurity Framework",
                                f"STRIDE {cat_name} category best practices"
                            ]
                    
                    all_threats.extend(threats)
                    logger.info(f"    Generated {len(threats)} threat(s)")
                else:
                    logger.warning(f"    Invalid response format for {cat_name}")
                
            except json.JSONDecodeError as e:
                logger.warning(f"    JSON decode error for {cat_name}: {e}")
                logger.info(f"    Falling back to rule-based generation for this category")
                # Fall back to rule-based for this category
                if cat_letter in ['S', 'T', 'I']:  # Most important categories
                    fallback_threats = self.rule_generator.generate_threats_for_component(component)
                    category_threats = [t for t in fallback_threats if t.get('stride_category') == cat_letter]
                    all_threats.extend(category_threats)
                    
            except Exception as e:
                logger.warning(f"    Error generating threats for {cat_name}: {e}")
                # Continue with other categories
                continue
        
        return all_threats

# --- Main Functions ---
def load_dfd_data(filepath: str) -> Dict[str, Any]:
    """Load DFD data from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle nested structure - check if 'dfd' key exists
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
    
    # Map of component types to their expected structure
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
                    # Handle different data structures
                    if isinstance(item, str):
                        # Simple string identifier
                        components.append({
                            "type": component_type,
                            "name": item,
                            "details": {"identifier": item}
                        })
                    elif isinstance(item, dict):
                        # Complex object with properties
                        component = {
                            "type": component_type,
                            "name": item.get('name', item.get('source', item.get('destination', 'Unknown'))),
                            "details": item
                        }
                        # For data flows, create a more descriptive name
                        if key == 'data_flows' and 'source' in item and 'destination' in item:
                            component['name'] = f"{item['source']} → {item['destination']}"
                        components.append(component)
    
    return components

def deduplicate_threats(threats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate threats based on description."""
    unique_threats = []
    seen_descriptions = set()
    
    for threat in threats:
        desc = threat.get('threat_description', '')
        # Create a simplified version for comparison
        simplified_desc = desc.lower().strip()
        if simplified_desc and simplified_desc not in seen_descriptions:
            seen_descriptions.add(simplified_desc)
            unique_threats.append(threat)
    
    return unique_threats

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
    """Main execution function."""
    logger.info("=== Starting Threat Modeling Analysis ===")
    
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
        
        analyzer = ThreatAnalyzer(llm_client)
    except Exception as e:
        logger.warning(f"Failed to initialize LLM services: {e}")
        logger.info("Continuing with rule-based threat generation")
        analyzer = ThreatAnalyzer(None)
    
    # Load DFD data
    try:
        write_progress(3, 10, 100, "Loading DFD data", "Reading component definitions")
        dfd_data = load_dfd_data(config['dfd_input_path'])
        components = extract_components(dfd_data)
        logger.info(f"Found {len(components)} components to analyze")
        
        # Log component types for debugging
        component_types = {}
        for comp in components:
            comp_type = comp.get('type', 'Unknown')
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
        
        logger.info("Component breakdown:")
        for comp_type, count in component_types.items():
            logger.info(f"  - {comp_type}: {count}")
        
        write_progress(3, 20, 100, "Components loaded", f"Found {len(components)} components")
    
    except Exception as e:
        logger.error(f"Failed to load or parse DFD data: {e}")
        write_progress(3, 0, 100, "Failed", f"Error: {str(e)}")
        return 1
    
    # Analyze components sequentially for stability
    logger.info("Analyzing components sequentially for stability")
    all_threats = []
    
    # Calculate progress steps
    total_steps = len(components) * len(DEFAULT_STRIDE_DEFINITIONS)  # Each component analyzed for each STRIDE category
    current_step = 0
    base_progress = 20
    analysis_progress_range = 70  # 20-90% for analysis
    
    for i, component in enumerate(components):
        try:
            # Check for kill signal
            if check_kill_signal(3):
                write_progress(3, current_step, total_steps, "Analysis cancelled", "User requested stop")
                return 1
            
            component_name = component.get('name', 'Unknown')
            logger.info(f"Analyzing component {i+1}/{len(components)}: {component_name}")
            
            # Update progress at component level
            component_progress = base_progress + int((i / len(components)) * analysis_progress_range)
            write_progress(
                3, 
                component_progress, 
                100, 
                f"Analyzing component {i+1}/{len(components)}", 
                f"Processing: {component_name}"
            )
            
            threats = analyzer.analyze_component(component)
            all_threats.extend(threats)
            
            # Update step counter
            current_step += len(DEFAULT_STRIDE_DEFINITIONS)
            
            # Small delay to avoid overwhelming the API
            if llm_client and llm_client.client:
                time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error analyzing component {component_name}: {e}")
            continue
    
    # Post-process results
    write_progress(3, 90, 100, "Post-processing threats", "Removing duplicates")
    all_threats = deduplicate_threats(all_threats)
    logger.info(f"Generated {len(all_threats)} unique threats")
    
    if not all_threats:
        logger.error("No threats were generated!")
        write_progress(3, 100, 100, "Failed", "No threats generated")
        return 1
    
    # Sort by risk score
    write_progress(3, 95, 100, "Finalizing results", "Sorting by risk score")
    risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    all_threats.sort(key=lambda t: risk_order.get(t.get('risk_score', 'Low'), 0), reverse=True)
    
    # Create output
    output = {
        "threats": all_threats,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "source_dfd": os.path.basename(config['dfd_input_path']),
            "llm_provider": config['llm_provider'],
            "llm_model": config['llm_model'],
            "total_threats": len(all_threats),
            "components_analyzed": len(components),
            "generation_method": "LLM" if (llm_client and llm_client.client) else "Rule-based",
            "dfd_structure": {
                "project_name": dfd_data.get('project_name', 'Unknown'),
                "industry_context": dfd_data.get('industry_context', 'Unknown')
            }
        }
    }
    
    # Validate basic structure
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
        write_progress(3, 100, 100, "Complete", f"Generated {len(all_threats)} threats")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        write_progress(3, 100, 100, "Failed", f"Save error: {str(e)}")
        return 1
    
    logger.info("=== Threat Modeling Analysis Complete ===")
    
    # Print summary
    print(f"\nSummary:")
    print(f"- Components analyzed: {len(components)}")
    print(f"- Total threats identified: {len(all_threats)}")
    print(f"- Critical threats: {sum(1 for t in all_threats if t.get('risk_score') == 'Critical')}")
    print(f"- High threats: {sum(1 for t in all_threats if t.get('risk_score') == 'High')}")
    print(f"- Medium threats: {sum(1 for t in all_threats if t.get('risk_score') == 'Medium')}")
    print(f"- Low threats: {sum(1 for t in all_threats if t.get('risk_score') == 'Low')}")
    
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