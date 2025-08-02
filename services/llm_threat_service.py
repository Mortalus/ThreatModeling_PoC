"""
Service for generating threats using LLM.
"""
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from models.threat_models import ThreatModel, ComponentAnalysis

logger = logging.getLogger(__name__)

# Conditional imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available")

class LLMThreatService:
    """Service for LLM-based threat generation."""
    
    def __init__(self, config: Dict[str, Any], stride_definitions: Dict[str, tuple]):
        self.config = config
        self.stride_definitions = stride_definitions
        self.client = None
        self.provider = config.get('llm_provider', 'scaleway')
        self.model = config.get('llm_model', 'llama-3.3-70b-instruct')
        self.ollama_endpoint = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LLM client."""
        try:
            if self.provider == "scaleway" and OPENAI_AVAILABLE:
                if not self.config.get('scw_secret_key'):
                    logger.warning("No Scaleway API key found")
                    return
                
                self.client = OpenAI(
                    base_url=self.config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
                    api_key=self.config['scw_secret_key']
                )
                logger.info("✅ Scaleway threat client initialized successfully")
                
            elif self.provider == "ollama":
                # For Ollama, we'll use direct HTTP requests
                self.ollama_endpoint = self.config.get('local_llm_endpoint', 'http://localhost:11434/api/generate')
                logger.info(f"✅ Ollama threat client configured for {self.ollama_endpoint}")
                logger.info(f"📊 Using model: {self.model}")
                
                # Test connection
                try:
                    test_url = self.ollama_endpoint.replace('/api/generate', '/api/tags')
                    response = requests.get(test_url, timeout=5)
                    if response.status_code == 200:
                        logger.info("✅ Ollama server is reachable for threat generation")
                    else:
                        logger.warning(f"⚠️ Ollama server returned status {response.status_code}")
                except Exception as e:
                    logger.warning(f"⚠️ Cannot reach Ollama server: {e}")
                
                # Mark as available for Ollama
                self.client = "ollama"  # Just a marker to indicate it's available
            else:
                logger.warning(f"❌ Unsupported LLM provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.client is not None
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call Ollama API directly."""
        try:
            logger.info(f"🤖 Calling Ollama for threat generation with model: {self.model}")
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.get('temperature', 0.2),
                    "num_predict": self.config.get('max_tokens', 2048),
                    "top_p": 0.95,
                    "seed": 42
                }
            }
            
            logger.info("⏳ Waiting for Ollama threat response...")
            response = requests.post(
                self.ollama_endpoint,
                json=payload,
                timeout=self.config.get('timeout', 300)
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                logger.info(f"✅ Received threat response: {len(response_text)} characters")
                return response_text
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out - consider increasing timeout")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama - is it running?")
            return None
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return None
    
    def generate_threats(self, component: ComponentAnalysis, cat_letter: str, 
                        cat_name: str, cat_def: str) -> List[ThreatModel]:
        """Generate threats using LLM."""
        if not self.is_available():
            logger.warning("LLM service not available for threat generation")
            return []
        
        prompt = self._build_threat_prompt(component, cat_letter, cat_name, cat_def)
        
        try:
            # Handle Ollama
            if self.client == "ollama":
                logger.info(f"🎯 Generating {cat_name} threats for {component.name} using Ollama")
                response_text = self._call_ollama(prompt)
                
                if response_text:
                    try:
                        # Clean and parse JSON response
                        response_text = response_text.strip()
                        
                        # Find JSON in the response
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            json_text = response_text[json_start:json_end]
                            data = json.loads(json_text)
                            threats = self._parse_threat_response(data, component.name, cat_letter)
                            logger.info(f"✅ Generated {len(threats)} {cat_name} threats")
                            return threats
                        else:
                            logger.error(f"No valid JSON found in Ollama response for {cat_name}")
                            return []
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Ollama threat response: {e}")
                        logger.debug(f"Response was: {response_text[:500]}...")
                        return []
                else:
                    logger.warning(f"No response from Ollama for {cat_name} threats")
                    return []
            
            # Handle Scaleway (original code)
            elif isinstance(self.client, OpenAI):
                logger.info(f"🎯 Generating {cat_name} threats for {component.name} using Scaleway")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a cybersecurity expert specializing in threat modeling."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.config.get('temperature', 0.2),
                    max_tokens=self.config.get('max_tokens', 2048)
                )
                
                response_text = response.choices[0].message.content.strip()
                
                # Parse JSON response
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                data = json.loads(response_text)
                threats = self._parse_threat_response(data, component.name, cat_letter)
                logger.info(f"✅ Generated {len(threats)} {cat_name} threats")
                return threats
                
        except Exception as e:
            logger.error(f"Failed to generate threats for {component.name}: {e}")
            return []
    
    def _build_threat_prompt(self, component: ComponentAnalysis, cat_letter: str, 
                           cat_name: str, cat_def: str) -> str:
        """Build threat generation prompt."""
        component_info = {
            'name': component.name,
            'type': component.type,
            'details': component.details
        }
        
        return f"""You are a cybersecurity architect specializing in realistic threat modeling. Analyze this DFD component and generate ONLY the 1-2 most realistic and significant threats for the specified STRIDE category.

**Component:**
{json.dumps(component_info, indent=2)}

**STRIDE Category:** {cat_letter} ({cat_name})
{cat_def}

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
      "component_name": "{component.name}",
      "stride_category": "{cat_letter}",
      "threat_description": "Specific, realistic threat description focusing on actual attack scenarios",
      "mitigation_suggestion": "Actionable, specific mitigation strategies with implementation details",
      "impact": "Low|Medium|High",
      "likelihood": "Low|Medium|High",
      "references": ["Relevant security standards or attack frameworks"],
      "risk_score": "Critical|High|Medium|Low"
    }}
  ]
}}"""
    
    def _parse_threat_response(self, data: Dict, component_name: str, 
                              cat_letter: str) -> List[ThreatModel]:
        """Parse LLM response into ThreatModel objects."""
        threats = []
        
        threat_list = data.get('threats', [])
        if not isinstance(threat_list, list):
            logger.error(f"Invalid threat response format: {data}")
            return threats
        
        for threat_data in threat_list:
            try:
                # Calculate risk score if not provided
                impact = threat_data.get('impact', 'Medium')
                likelihood = threat_data.get('likelihood', 'Medium')
                risk_score = threat_data.get('risk_score')
                
                if not risk_score:
                    # Simple risk calculation
                    risk_matrix = {
                        ('High', 'High'): 'Critical',
                        ('High', 'Medium'): 'High',
                        ('Medium', 'High'): 'High',
                        ('High', 'Low'): 'Medium',
                        ('Low', 'High'): 'Medium',
                        ('Medium', 'Medium'): 'Medium',
                        ('Medium', 'Low'): 'Low',
                        ('Low', 'Medium'): 'Low',
                        ('Low', 'Low'): 'Low'
                    }
                    risk_score = risk_matrix.get((impact, likelihood), 'Medium')
                
                threat = ThreatModel(
                    component_name=component_name,
                    stride_category=cat_letter,
                    threat_description=threat_data.get('threat_description', ''),
                    mitigation_suggestion=threat_data.get('mitigation_suggestion', ''),
                    impact=impact,
                    likelihood=likelihood,
                    references=threat_data.get('references', []),
                    risk_score=risk_score
                )
                threats.append(threat)
                
            except Exception as e:
                logger.error(f"Failed to parse threat: {e}")
                logger.debug(f"Threat data: {threat_data}")
        
        return threats