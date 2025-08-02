"""
Service for generating threats using LLM.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from models.threat_models import ThreatModel, ComponentAnalysis

logger = logging.getLogger(__name__)

# Conditional imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class LLMThreatService:
    """Service for LLM-based threat generation."""
    
    def __init__(self, config: Dict[str, Any], stride_definitions: Dict[str, tuple]):
        self.config = config
        self.stride_definitions = stride_definitions
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LLM client."""
        try:
            provider = self.config.get('llm_provider', 'scaleway')
            
            if provider == "scaleway" and OPENAI_AVAILABLE:
                if not self.config.get('scw_secret_key'):
                    logger.warning("No Scaleway API key found")
                    return
                
                self.client = OpenAI(
                    base_url=self.config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
                    api_key=self.config['scw_secret_key']
                )
                logger.info("Scaleway client initialized successfully")
                
            elif provider == "ollama":
                logger.info("Ollama client configured")
            else:
                logger.warning(f"Unsupported LLM provider: {provider}")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self.client is not None
    
    def generate_threats(self, component: ComponentAnalysis, cat_letter: str, 
                        cat_name: str, cat_def: str) -> List[ThreatModel]:
        """Generate threats using LLM."""
        if not self.client:
            return []
        
        prompt = self._build_threat_prompt(component, cat_letter, cat_name, cat_def)
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.get('llm_model', 'llama-3.3-70b-instruct'),
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.get('temperature', 0.4),
                max_tokens=self.config.get('max_tokens', 2048)
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean and parse response
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            data = json.loads(response_text)
            
            if isinstance(data, dict) and isinstance(data.get("threats"), list):
                threats = []
                for threat_data in data["threats"]:
                    threat = ThreatModel(
                        component_name=component.name,
                        stride_category=cat_letter,
                        threat_description=threat_data.get('threat_description', ''),
                        mitigation_suggestion=threat_data.get('mitigation_suggestion', ''),
                        impact=threat_data.get('impact', 'Medium'),
                        likelihood=threat_data.get('likelihood', 'Medium'),
                        references=threat_data.get('references', []),
                        risk_score=threat_data.get('risk_score', 'Medium')
                    )
                    threats.append(threat)
                
                return threats
                
        except Exception as e:
            logger.warning(f"LLM threat generation failed: {e}")
            
        return []
    
    def _build_threat_prompt(self, component: ComponentAnalysis, cat_letter: str, 
                            cat_name: str, cat_def: str) -> str:
        """Build prompt for threat generation."""
        component_info = {
            'name': component.name,
            'type': component.type,
            'details': component.details
        }
        
        return f"""
You are a cybersecurity architect specializing in realistic threat modeling. Analyze this DFD component and generate ONLY the 1-2 most realistic and significant threats for the specified STRIDE category.

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