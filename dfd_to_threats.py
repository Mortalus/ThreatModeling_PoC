#!/usr/bin/env python3
"""
DFD to Threats Generator Script - Original Version with Progress Updates

This script analyzes DFD (Data Flow Diagram) components and generates realistic threats
using the STRIDE methodology with intelligent filtering and risk-based prioritization.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# --- Progress Tracking ---
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
            'timestamp': datetime.now().isoformat(),
            'status': 'running'
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

# --- STRIDE Definitions ---
DEFAULT_STRIDE_DEFINITIONS = {
    "S": ("Spoofing", "Illegitimately accessing systems or data by impersonating a user, process, or component."),
    "T": ("Tampering", "Unauthorized modification of data, either in transit or at rest."),  
    "R": ("Repudiation", "A user or system denying that they performed an action, often due to a lack of sufficient proof."),
    "I": ("Information Disclosure", "Exposing sensitive information to unauthorized individuals."),
    "D": ("Denial of Service", "Preventing legitimate users from accessing a system or service."),
    "E": ("Elevation of Privilege", "A user or process gaining rights beyond their authorized level.")
}

# --- LLM Client ---
class LLMClient:
    def __init__(self):
        self.provider = config['llm_provider'].lower()
        self.model = config['llm_model']
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the LLM client with error handling."""
        try:
            if self.provider == 'scaleway':
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
                    
            elif self.provider == 'ollama':
                logger.info("Ollama client configured")
            else:
                logger.error(f"Unsupported LLM provider: {self.provider}")
        
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.client = None
    
    def generate(self, prompt: str, json_mode: bool = True) -> str:
        """Generate text using the configured LLM provider."""
        if not self.client and self.provider == 'scaleway':
            raise Exception("LLM client not initialized")
            
        try:
            if self.provider == 'scaleway':
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
            
            elif self.provider == 'ollama':
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

# --- Threat Analyzer ---
class ThreatAnalyzer:
    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client
        self.stride_definitions = DEFAULT_STRIDE_DEFINITIONS
        
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
        """Analyze component with STRIDE methodology."""
        component_name = component.get("name", "Unknown")
        component_type = component.get("type", "Unknown")
        
        logger.info(f"Analyzing component: {component_name} ({component_type})")
        
        # Get applicable STRIDE categories for this component type
        applicable_categories = COMPONENT_STRIDE_MAPPING.get(component_type, ['S', 'T', 'I'])
        max_threats = MAX_THREATS_PER_COMPONENT.get(component_type, 2)
        
        all_threats = []
        
        # Analyze only applicable categories
        for cat_letter in applicable_categories:
            if cat_letter not in self.stride_definitions:
                continue
                
            cat_name, cat_def = self.stride_definitions[cat_letter]
            
            try:
                if self.llm and self.llm.client:
                    threats = self._analyze_with_llm(component, cat_letter, cat_name, cat_def)
                else:
                    threats = self._analyze_with_rules(component, cat_letter)
                
                # Limit threats per category
                threats = threats[:1]
                all_threats.extend(threats)
                
            except Exception as e:
                logger.warning(f"Error analyzing {cat_name}: {e}")
                continue
        
        # Limit total threats per component
        all_threats = all_threats[:max_threats]
        
        return all_threats
    
    def _analyze_with_llm(self, component: Dict[str, Any], cat_letter: str, 
                         cat_name: str, cat_def: str) -> List[Dict[str, Any]]:
        """Analyze with LLM."""
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
        
        # Parse response
        try:
            data = json.loads(response)
            
            if isinstance(data, dict) and isinstance(data.get("threats"), list):
                return data["threats"]
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response for {component_name}")
        
        return []
    
    def _analyze_with_rules(self, component: Dict[str, Any], cat_letter: str) -> List[Dict[str, Any]]:
        """Simple rule-based threat generation."""
        component_name = component.get("name", "Unknown")
        component_type = component.get("type", "Unknown")
        
        if cat_letter == 'S' and component_type == 'External Entity':
            return [{
                'component_name': component_name,
                'stride_category': 'S',
                'threat_description': f'An attacker could impersonate {component_name} to gain unauthorized access.',
                'mitigation_suggestion': 'Implement multi-factor authentication.',
                'impact': 'High',
                'likelihood': 'Medium',
                'risk_score': 'High',
                'references': ['OWASP A07:2021']
            }]
        elif cat_letter == 'I' and component_type == 'Data Store':
            return [{
                'component_name': component_name,
                'stride_category': 'I',
                'threat_description': f'Sensitive data in {component_name} could be exposed.',
                'mitigation_suggestion': 'Implement encryption at rest and access controls.',
                'impact': 'Critical',
                'likelihood': 'Medium',
                'risk_score': 'Critical',
                'references': ['OWASP A01:2021']
            }]
        
        return []

# --- Helper Functions ---
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
    
    return min(score, 10)  # Cap at 10

def prioritize_components(components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prioritize components based on risk factors."""
    # Calculate scores
    for component in components:
        component['_risk_score'] = calculate_component_risk_score(component)
    
    # Sort by risk score (highest first)
    components.sort(key=lambda x: x.get('_risk_score', 0), reverse=True)
    
    return components

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

def main():
    """Main execution function."""
    logger.info("=== Starting Realistic Threat Modeling Analysis ===")
    
    # Initialize progress
    write_progress(3, 0, 100, "Initializing threat analysis", "Loading components")
    
    # Initialize LLM client
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
        
        # Prioritize components by risk
        components = prioritize_components(components)
        
        # Filter to only analyze high-risk components
        high_risk_components = [c for c in components if c.get('_risk_score', 0) >= config['min_risk_score']]
        
        # Limit total components to analyze
        max_components = config['max_components_to_analyze']
        if len(high_risk_components) > max_components:
            logger.info(f"Limiting analysis to top {max_components} highest risk components")
            high_risk_components = high_risk_components[:max_components]
        
        logger.info(f"Total components: {len(components)}")
        logger.info(f"High-risk components to analyze: {len(high_risk_components)}")
        
        write_progress(3, 20, 100, "Components loaded", f"Found {len(high_risk_components)} high-risk components")
    
    except Exception as e:
        logger.error(f"Failed to load or parse DFD data: {e}")
        write_progress(3, 0, 100, "Failed", f"Error: {str(e)}")
        return 1
    
    # Analyze components
    logger.info("Analyzing components for threats")
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
            
            # Small delay for LLM rate limiting
            if llm_client and llm_client.client:
                time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error analyzing component {component_name}: {e}")
            continue
    
    logger.info(f"Generated {len(all_threats)} threats")
    
    if not all_threats:
        logger.error("No threats were generated!")
        write_progress(3, 100, 100, "Failed", "No threats generated")
        return 1
    
    # Create output
    write_progress(3, 95, 100, "Finalizing results", "Creating output")
    
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
    print(f"\n=== Threat Analysis Summary ===")
    print(f"Total components in DFD: {len(components)}")
    print(f"High-risk components analyzed: {len(high_risk_components)}")
    print(f"Total threats identified: {len(all_threats)}")
    print(f"Critical threats: {risk_breakdown['Critical']}")
    print(f"High threats: {risk_breakdown['High']}")
    print(f"Medium threats: {risk_breakdown['Medium']}")
    print(f"Low threats: {risk_breakdown['Low']}")
    print(f"Analysis method: {output['metadata']['generation_method']}")
    
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