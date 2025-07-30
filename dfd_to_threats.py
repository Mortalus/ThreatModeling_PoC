# --- Dependencies ---
# pip install openai pydantic python-dotenv qdrant-client requests ollama

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import ollama

# Load environment variables
load_dotenv()

# --- Configuration ---
class LLMProvider(Enum):
    SCALEWAY = "scaleway"
    OLLAMA = "ollama"

# LLM Configuration
LLM_PROVIDER = LLMProvider(os.getenv("LLM_PROVIDER", "scaleway").lower())
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-instruct")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
SCALEWAY_API_KEY = os.getenv("SCALEWAY_API_KEY", os.getenv("SCW_API_KEY"))
SCALEWAY_PROJECT_ID = os.getenv("SCALEWAY_PROJECT_ID", "4a8fd76b-8606-46e6-afe6-617ce8eeb948")

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "homebase")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "threat_models")
QDRANT_USE_GRPC = os.getenv("QDRANT_USE_GRPC", "false").lower() == "true"
ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"

# File paths
INPUT_DIR = os.getenv("INPUT_DIR", "./output")
DFD_INPUT_PATH = os.getenv("DFD_INPUT_PATH", os.path.join(INPUT_DIR, "dfd_components.json"))
THREATS_OUTPUT_PATH = os.getenv("THREATS_OUTPUT_PATH", os.path.join(INPUT_DIR, "identified_threats.json"))
STRIDE_CONFIG_PATH = os.getenv("STRIDE_CONFIG_PATH", "stride_config.json")

# Model parameters
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.4"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))  # Number of parallel workers

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs(INPUT_DIR, exist_ok=True)

# --- Pydantic Models ---
class Threat(BaseModel):
    component_name: str
    stride_category: str
    threat_description: str
    mitigation_suggestion: str
    impact: str = Field(pattern="^(Low|Medium|High)$")
    likelihood: str = Field(pattern="^(Low|Medium|High)$")
    references: List[str]
    risk_score: str = Field(pattern="^(Critical|High|Medium|Low)$")

class ThreatsOutput(BaseModel):
    threats: List[Threat]
    metadata: Dict[str, Any]

# --- LLM Client Factory ---
class LLMClient:
    def __init__(self):
        self.provider = LLM_PROVIDER
        self.model = LLM_MODEL
        self.client = self._create_client()
    
    def _create_client(self):
        if self.provider == LLMProvider.SCALEWAY:
            if not SCALEWAY_API_KEY:
                raise ValueError("SCALEWAY_API_KEY environment variable is required for Scaleway provider")
            return OpenAI(
                base_url=f"https://api.scaleway.ai/{SCALEWAY_PROJECT_ID}/v1",
                api_key=SCALEWAY_API_KEY
            )
        elif self.provider == LLMProvider.OLLAMA:
            # Test Ollama connection
            try:
                ollama.list()
                return None  # Ollama uses function calls, not a client object
            except Exception as e:
                raise ConnectionError(f"Failed to connect to Ollama at {OLLAMA_HOST}: {e}")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def generate(self, prompt: str, json_mode: bool = True) -> str:
        """Generate text using the configured LLM provider."""
        try:
            if self.provider == LLMProvider.SCALEWAY:
                messages = [{"role": "user", "content": prompt}]
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": MAX_TOKENS,
                    "temperature": TEMPERATURE
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            
            elif self.provider == LLMProvider.OLLAMA:
                # For Ollama, we need to add JSON instruction to the prompt
                if json_mode:
                    prompt = prompt + "\n\nIMPORTANT: Output ONLY valid JSON, no other text."
                
                response = ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        "temperature": TEMPERATURE,
                        "num_predict": MAX_TOKENS,
                    }
                )
                return response['response']
                
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise

# --- Qdrant Client ---
class QdrantRAG:
    def __init__(self):
        self.client = self._create_client()
        self.collection_name = QDRANT_COLLECTION
        self._verify_collection()
    
    def _create_client(self):
        """Create Qdrant client with appropriate configuration."""
        # For local Qdrant
        if not QDRANT_API_KEY and QDRANT_HOST in ['localhost', '127.0.0.1']:
            return QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT
            )
        
        # For Qdrant Cloud or authenticated instances
        kwargs = {
            "host": QDRANT_HOST,
            "port": QDRANT_PORT,
        }
        
        if QDRANT_API_KEY:
            kwargs["api_key"] = QDRANT_API_KEY
        
        if QDRANT_USE_GRPC:
            kwargs["grpc_port"] = 6334
            kwargs["prefer_grpc"] = True
        
        return QdrantClient(**kwargs)
    
    def _verify_collection(self):
        """Verify that the collection exists."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.warning(f"Collection '{self.collection_name}' not found in Qdrant. Available collections: {collection_names}")
                raise ValueError(f"Collection '{self.collection_name}' does not exist in Qdrant")
            
            logger.info(f"Successfully connected to Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to verify Qdrant collection: {e}")
            raise
    
    def search(self, query_text: str, top_k: int = RAG_TOP_K) -> List[str]:
        """Search for similar documents in Qdrant."""
        try:
            # First, check if the collection has points
            collection_info = self.client.get_collection(self.collection_name)
            if collection_info.points_count == 0:
                logger.warning(f"Collection '{self.collection_name}' has no points. Skipping RAG search.")
                return []
            
            # Try different search methods based on collection configuration
            try:
                # Method 1: Try neural search if collection supports it
                from qdrant_client.models import SearchRequest, NamedVector
                
                # Check if collection has named vectors
                if collection_info.config.params.vectors:
                    # If vectors is a dict, we have named vectors
                    if isinstance(collection_info.config.params.vectors, dict):
                        vector_names = list(collection_info.config.params.vectors.keys())
                        if vector_names:
                            # Use the first available vector name
                            vector_name = vector_names[0]
                            logger.info(f"Using named vector: {vector_name}")
                            
                            # For now, skip actual search if we don't have embeddings
                            logger.warning("Text-to-vector embedding not configured. Returning empty context.")
                            return []
                
                # Method 2: Try to use scroll to get some relevant documents
                # This is a fallback when we can't do vector search
                logger.info("Falling back to scroll method to retrieve documents")
                scroll_result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False
                )
                
                contexts = []
                if scroll_result and scroll_result[0]:
                    for point in scroll_result[0]:
                        if point.payload:
                            # Look for text content in various possible fields
                            text_content = None
                            for field in ['text', 'content', 'description', 'threat_description']:
                                if field in point.payload:
                                    text_content = point.payload[field]
                                    break
                            
                            if text_content:
                                # Simple keyword matching as a basic relevance filter
                                if any(keyword in text_content.lower() for keyword in query_text.lower().split()):
                                    contexts.append(text_content)
                
                return contexts[:top_k]
                
            except Exception as search_error:
                logger.error(f"Search method failed: {search_error}")
                return []
                
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return []

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
    if os.path.exists(STRIDE_CONFIG_PATH):
        try:
            with open(STRIDE_CONFIG_PATH, 'r') as f:
                custom_stride = json.load(f)
            logger.info(f"Loaded custom STRIDE definitions from '{STRIDE_CONFIG_PATH}'")
            # Convert to expected format
            return {k: (v[0], v[1]) if isinstance(v, list) else v for k, v in custom_stride.items()}
        except Exception as e:
            logger.warning(f"Failed to load custom STRIDE definitions: {e}. Using defaults.")
    
    return DEFAULT_STRIDE_DEFINITIONS

# --- Threat Analysis ---
class ThreatAnalyzer:
    def __init__(self, llm_client: LLMClient, rag_client: Optional[QdrantRAG] = None):
        self.llm = llm_client
        self.rag = rag_client
        self.stride_definitions = load_stride_definitions()
        self.threat_prompt_template = """
You are a cybersecurity architect specializing in threat modeling using the STRIDE methodology.
Your task is to generate 1-2 specific threats for a given DFD component, focusing ONLY on a single STRIDE category.

**DFD Component to Analyze:**
{component_info}

**STRIDE Category to Focus On:**
- **{stride_category} ({stride_name}):** {stride_definition}

**Security Context from Knowledge Base:**
'''
{rag_context}
'''

**Instructions:**
1. Generate 1-2 distinct and realistic threats for the component that fall **strictly** under the '{stride_name}' category.
2. Be specific and relate the threat directly to the component's type and details.
3. Use the provided Security Context to create specific descriptions, actionable mitigations, and accurate references.
4. Provide a realistic risk assessment (Impact, Likelihood, Score).
5. Output ONLY a valid JSON object with a single key "threats", containing a list of threat objects.

**JSON Schema:**
{{
  "threats": [
    {{
      "component_name": "string",
      "stride_category": "{stride_category}",
      "threat_description": "string",
      "mitigation_suggestion": "string",
      "impact": "Low|Medium|High",
      "likelihood": "Low|Medium|High",
      "references": ["string"],
      "risk_score": "Critical|High|Medium|Low"
    }}
  ]
}}
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
        component_str = json.dumps(component)
        component_name = component.get("name", component.get("details", {}).get("name", component.get("type", "Unknown")))
        
        logger.info(f"Analyzing component: {component_name}")
        
        # Get RAG context if enabled
        rag_context = "No specific security context available."
        if hasattr(self, 'rag') and self.rag:
            try:
                rag_contexts = self.rag.search(component_str)
                if rag_contexts:
                    rag_context = "\n---\n".join(rag_contexts)
                    logger.info(f"  Found {len(rag_contexts)} RAG contexts")
            except Exception as e:
                logger.warning(f"  RAG search failed: {e}")
        
        all_threats = []
        
        for cat_letter, (cat_name, cat_def) in self.stride_definitions.items():
            logger.info(f"  Generating threats for STRIDE category: {cat_name}")
            
            prompt = self.threat_prompt_template.format(
                component_info=component_str,
                rag_context=rag_context,
                stride_category=cat_letter,
                stride_name=cat_name,
                stride_definition=cat_def
            )
            
            try:
                response = self.llm.generate(prompt, json_mode=True)
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
                    
                    all_threats.extend(threats)
                    logger.info(f"    Generated {len(threats)} threat(s)")
                
            except Exception as e:
                logger.error(f"    Error generating threats for {cat_name}: {e}")
        
        return all_threats

# --- Progress Tracking ---
class ProgressTracker:
    def __init__(self, total_components: int):
        self.total = total_components
        self.completed = 0
        self.lock = threading.Lock()
        
    def increment(self):
        with self.lock:
            self.completed += 1
            return self.completed
    
    def get_progress(self):
        with self.lock:
            return self.completed, self.total

# --- Main Functions ---
def load_dfd_data(filepath: str) -> Dict[str, Any]:
    """Load DFD data from file."""
    try:
        with open(filepath, 'r') as f:
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
        'data_flows': 'Data Flow',
        'trust_boundaries': 'Trust Boundary'
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
    
    # Add project context if available
    if 'project_name' in dfd_data:
        components.append({
            "type": "Project Context",
            "name": dfd_data.get('project_name', 'Unknown Project'),
            "details": {
                "project_name": dfd_data.get('project_name'),
                "project_version": dfd_data.get('project_version'),
                "industry_context": dfd_data.get('industry_context')
            }
        })
    
    return components

def deduplicate_threats(threats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate threats based on description."""
    unique_threats = []
    seen_descriptions = set()
    
    for threat in threats:
        desc = threat.get('threat_description', '')
        if desc and desc not in seen_descriptions:
            seen_descriptions.add(desc)
            unique_threats.append(threat)
    
    return unique_threats

def main():
    """Main execution function."""
    logger.info("=== Starting Threat Modeling Analysis ===")
    
    # Initialize clients
    try:
        llm_client = LLMClient()
        logger.info(f"Initialized LLM client: {LLM_PROVIDER.value} with model {LLM_MODEL}")
        
        rag_client = None
        if ENABLE_RAG:
            try:
                rag_client = QdrantRAG()
                logger.info("Initialized Qdrant RAG client")
            except Exception as rag_error:
                logger.warning(f"Failed to initialize RAG client: {rag_error}")
                logger.info("Continuing without RAG support")
        else:
            logger.info("RAG is disabled (ENABLE_RAG=false)")
        
        analyzer = ThreatAnalyzer(llm_client, rag_client)
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return 1
    
    # Load DFD data
    try:
        dfd_data = load_dfd_data(DFD_INPUT_PATH)
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
    
    except Exception as e:
        logger.error(f"Failed to load or parse DFD data: {e}")
        return 1
    
    # Analyze components in parallel
    logger.info(f"Using {MAX_WORKERS} parallel workers for threat analysis")
    all_threats = []
    progress_tracker = ProgressTracker(len(components))
    
    def analyze_with_progress(component, index):
        """Wrapper function that includes progress tracking."""
        try:
            component_name = component.get('name', 'Unknown')
            logger.info(f"Starting analysis of component {index+1}/{len(components)}: {component_name}")
            
            threats = analyzer.analyze_component(component)
            
            completed = progress_tracker.increment()
            logger.info(f"Completed {completed}/{len(components)} components ({completed/len(components)*100:.1f}%)")
            
            return threats
        except Exception as e:
            logger.error(f"Error analyzing component {component_name}: {e}")
            progress_tracker.increment()  # Still increment to track progress
            return []
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_component = {
            executor.submit(analyze_with_progress, component, i): (component, i) 
            for i, component in enumerate(components)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_component):
            component, index = future_to_component[future]
            try:
                threats = future.result()
                all_threats.extend(threats)
            except Exception as e:
                component_name = component.get('name', 'Unknown')
                logger.error(f"Failed to get results for component {component_name}: {e}")
    
    # Post-process results
    all_threats = deduplicate_threats(all_threats)
    logger.info(f"Generated {len(all_threats)} unique threats")
    
    # Sort by risk score
    risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    all_threats.sort(key=lambda t: risk_order.get(t.get('risk_score', 'Low'), 0), reverse=True)
    
    # Create output
    output = {
        "threats": all_threats,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "source_dfd": os.path.basename(DFD_INPUT_PATH),
            "llm_provider": LLM_PROVIDER.value,
            "llm_model": LLM_MODEL,
            "rag_enabled": ENABLE_RAG and rag_client is not None,
            "qdrant_collection": QDRANT_COLLECTION if (ENABLE_RAG and rag_client) else None,
            "total_threats": len(all_threats),
            "components_analyzed": len(components),
            "parallel_workers": MAX_WORKERS,
            "dfd_structure": {
                "project_name": dfd_data.get('project_name', 'Unknown'),
                "industry_context": dfd_data.get('industry_context', 'Unknown')
            }
        }
    }
    
    # Validate output
    try:
        validated_output = ThreatsOutput(**output)
        logger.info("Output validation successful")
    except ValidationError as e:
        logger.error(f"Output validation failed: {e}")
        return 1
    
    # Save results
    with open(THREATS_OUTPUT_PATH, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Results saved to '{THREATS_OUTPUT_PATH}'")
    logger.info("=== Threat Modeling Analysis Complete ===")
    
    # Print summary
    print(f"\nSummary:")
    print(f"- Components analyzed: {len(components)}")
    print(f"- Total threats identified: {len(all_threats)}")
    print(f"- Critical threats: {sum(1 for t in all_threats if t.get('risk_score') == 'Critical')}")
    print(f"- High threats: {sum(1 for t in all_threats if t.get('risk_score') == 'High')}")
    print(f"- Medium threats: {sum(1 for t in all_threats if t.get('risk_score') == 'Medium')}")
    print(f"- Low threats: {sum(1 for t in all_threats if t.get('risk_score') == 'Low')}")
    print(f"- Parallel workers used: {MAX_WORKERS}")
    
    return 0

if __name__ == "__main__":
    exit(main())