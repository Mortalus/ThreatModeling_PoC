"""
Service for LLM interactions in DFD extraction.
"""
import json
import logging
from typing import Optional, Dict, Any
from models.dfd_models import SimpleDFDComponents, SimpleDataFlow
from services.rule_based_extractor import RuleBasedExtractor

logger = logging.getLogger(__name__)

# Conditional imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available")

try:
    import instructor
    INSTRUCTOR_AVAILABLE = True
except ImportError:
    INSTRUCTOR_AVAILABLE = False
    logger.warning("Instructor package not available")

class LLMService:
    """Service for LLM-based DFD extraction."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get('llm_provider', 'scaleway')
        self.model = config.get('llm_model', 'llama-3.3-70b-instruct')
        self.client = None
        self.raw_client = None
        self.rule_extractor = RuleBasedExtractor()
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the LLM client with fallback options."""
        try:
            if self.provider == "scaleway" and OPENAI_AVAILABLE:
                if not self.config.get('scw_secret_key'):
                    raise ValueError("SCW_SECRET_KEY required for Scaleway")
                
                self.raw_client = OpenAI(
                    base_url=self.config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
                    api_key=self.config['scw_secret_key']
                )
                
                if INSTRUCTOR_AVAILABLE:
                    self.client = instructor.from_openai(self.raw_client)
                    logger.info("✅ Scaleway client with instructor initialized")
                else:
                    logger.info("✅ Scaleway client initialized (no structured output)")
                
            else:
                logger.warning("❌ LLM client not available - will use rule-based extraction")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM client: {e}")
            self.client = None
            self.raw_client = None
    
    def extract_dfd_components(self, content: str, doc_analysis: Dict) -> Optional[SimpleDFDComponents]:
        """Extract DFD components using LLM with fallback."""
        if not self.raw_client:
            logger.warning("No LLM client available, using rule-based extraction")
            return self.rule_extractor.extract(content, doc_analysis)
        
        try:
            prompt = self._build_extraction_prompt(content, doc_analysis)
            
            # Try raw text extraction
            response = self.raw_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt + "\n\nRespond with valid JSON only."}],
                temperature=self.config.get('temperature', 0.2),
                max_tokens=self.config.get('max_tokens', 4096)
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean and parse JSON
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            data = json.loads(response_text)
            return self._dict_to_simple_components(data)
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return self.rule_extractor.extract(content, doc_analysis)
    
    def _build_extraction_prompt(self, content: str, doc_analysis: Dict) -> str:
        """Build extraction prompt."""
        return f"""You are an expert cybersecurity architect analyzing system documentation to extract Data Flow Diagram (DFD) components for threat modeling.

DOCUMENT ANALYSIS:
- Industry: {doc_analysis.get('industry_context', 'General')}
- Document Type: {doc_analysis.get('document_type', 'Technical')}
- Content Length: {len(content)} characters

EXTRACTION REQUIREMENTS:
1. **External Entities**: Users, administrators, external systems, third parties
2. **Processes**: Services, applications, servers, gateways that process data
3. **Assets**: Databases, data stores, file systems, caches that store data
4. **Trust Boundaries**: Security zones, network boundaries, privilege levels
5. **Data Flows**: Communication between components with security details

CRITICAL RULES:
- Every data flow source/destination MUST exist in the component lists
- Use consistent naming (avoid synonyms for the same component)
- Classify data appropriately: Public < Internal < Confidential < PII/PHI/PCI
- Include realistic security protocols and authentication mechanisms

DOCUMENT CONTENT:
{content[:4000]}{"..." if len(content) > 4000 else ""}

Extract comprehensive DFD components as JSON with the following structure:
{{
    "project_name": "descriptive project name",
    "project_version": "1.0",
    "industry_context": "industry or domain",
    "external_entities": ["list of external entities"],
    "processes": ["list of processes/services"],
    "assets": ["list of data stores/databases"],
    "trust_boundaries": ["list of security boundaries"],
    "data_flows": [
        {{
            "source": "source component name",
            "destination": "destination component name", 
            "data_description": "what data is transferred",
            "data_classification": "Public|Internal|Confidential|PII|PHI|PCI",
            "protocol": "HTTPS|HTTP|JDBC|API|etc",
            "authentication_mechanism": "JWT|OAuth|mTLS|API Key|etc",
            "trust_boundary_crossing": true/false,
            "encryption_in_transit": true/false
        }}
    ],
    "assumptions": ["assumptions made during extraction"],
    "confidence_notes": ["areas of uncertainty"]
}}"""
    
    def _dict_to_simple_components(self, data: Dict) -> SimpleDFDComponents:
        """Convert dictionary to SimpleDFDComponents."""
        result = SimpleDFDComponents()
        
        result.project_name = data.get('project_name', 'Unknown Project')
        result.project_version = data.get('project_version', '1.0')
        result.industry_context = data.get('industry_context', 'General')
        result.external_entities = data.get('external_entities', [])
        result.processes = data.get('processes', [])
        result.assets = data.get('assets', [])
        result.trust_boundaries = data.get('trust_boundaries', [])
        result.assumptions = data.get('assumptions', [])
        result.confidence_notes = data.get('confidence_notes', [])
        
        # Convert data flows
        for flow_data in data.get('data_flows', []):
            flow = SimpleDataFlow(
                source=flow_data.get('source', ''),
                destination=flow_data.get('destination', ''),
                data_description=flow_data.get('data_description', ''),
                data_classification=flow_data.get('data_classification', 'Internal'),
                protocol=flow_data.get('protocol', 'HTTPS'),
                authentication_mechanism=flow_data.get('authentication_mechanism', 'Unknown'),
                trust_boundary_crossing=flow_data.get('trust_boundary_crossing', False),
                encryption_in_transit=flow_data.get('encryption_in_transit', True)
            )
            result.data_flows.append(flow)
        
        return result