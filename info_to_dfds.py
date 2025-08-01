# This Python script serves as an automated tool for threat modeling in cybersecurity, 
# specifically extracting and structuring Data Flow Diagram (DFD) components from input documents (TXT or PDF files) describing system architectures. 
# It loads environment variables to configure the LLM provider (Ollama or Scaleway) and model, initializes the appropriate LLM client with support for structured outputs via Instructor, 
# and falls back to sample content if no documents are found. The script combines document contents, 
# crafts a detailed prompt for chain-of-thought reasoning to identify key elements like project metadata, external entities, assets, processes, trust boundaries, 
# and data flows (including details like protocols and authentication), then invokes the LLM to generate a validated JSON output conforming to a Pydantic schema. 
# It includes comprehensive logging of prompts, responses, token usage, and performance metrics, handles errors gracefully, 
# and saves the resulting DFD JSON to an output file for further use in security analysis.

import os
import json
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
import logging
import instructor
from ollama import Client
import PyPDF2
import glob
from openai import OpenAI

# Load environment variables
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
        'dfd_output_path': os.getenv('DFD_OUTPUT_PATH', './output/dfd_components.json'),
        'scw_api_url': os.getenv('SCW_API_URL', 'https://api.scaleway.ai/v1'),
        'scw_secret_key': os.getenv('SCW_SECRET_KEY') or os.getenv('SCW_API_KEY')
    }

# Get configuration
config = get_config()
LLM_PROVIDER = config['llm_provider']
LLM_MODEL = config['llm_model']
LOCAL_LLM_ENDPOINT = config['local_llm_endpoint']
CUSTOM_SYSTEM_PROMPT = config['custom_system_prompt']
INPUT_DIR = config['input_dir']
OUTPUT_DIR = config['output_dir']
DFD_OUTPUT_PATH = config['dfd_output_path']
SCW_API_URL = config['scw_api_url']
SCW_SECRET_KEY = config['scw_secret_key']

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
            'timestamp': datetime.now().isoformat()
        }
        
        progress_file = os.path.join(OUTPUT_DIR, f'step_{step}_progress.json')
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
            
    except Exception as e:
        logger.warning(f"Could not write progress: {e}")

def check_kill_signal(step: int) -> bool:
    """Check if user requested to kill this step."""
    try:
        kill_file = os.path.join(OUTPUT_DIR, f'step_{step}_kill.flag')
        if os.path.exists(kill_file):
            logger.info("Kill signal detected, stopping execution")
            return True
        return False
    except:
        return False

# --- Initialize LLM Client ---
def initialize_llm_client():
    if LLM_PROVIDER == "scaleway":
        if not SCW_SECRET_KEY:
            raise ValueError("SCW_SECRET_KEY environment variable is required for Scaleway API.")
        try:
            client = instructor.from_openai(OpenAI(base_url=SCW_API_URL, api_key=SCW_SECRET_KEY))
            logger.info("--- Scaleway OpenAI client initialized successfully ---")
            return client, "scaleway"
        except Exception as e:
            logger.error(f"--- Failed to initialize Scaleway client: {e} ---")
            raise
    else:  # Default to Ollama
        try:
            raw_client = Client()  # Raw Ollama client for debugging
            # Patch the Ollama client with instructor for structured output
            instructor_client = instructor.patch(Client())
            logger.info("--- Ollama client initialized successfully ---")
            return raw_client, instructor_client, "ollama"
        except Exception as e:
            logger.error(f"--- Failed to initialize Ollama client: {e} ---")
            raise

# --- DFD Schema for Validation ---
class DataFlow(BaseModel):
    source: str = Field(description="Source component of the data flow (e.g., 'U' for User).")
    destination: str = Field(description="Destination component of the data flow (e.g., 'CDN').")
    data_description: str = Field(description="Description of data being transferred (e.g., 'User session tokens').")
    data_classification: str = Field(description="Classification like 'Confidential', 'PII', or 'Public'.")
    protocol: str = Field(description="Protocol used (e.g., 'HTTPS', 'JDBC/ODBC over TLS').")
    authentication_mechanism: str = Field(description="Authentication method (e.g., 'JWT in Header').")

class DFDComponents(BaseModel):
    project_name: str = Field(description="Name of the project (e.g., 'Web Application Security Model').")
    project_version: str = Field(description="Version of the project (e.g., '1.1').")
    industry_context: str = Field(description="Industry context (e.g., 'Finance').")
    external_entities: list[str] = Field(description="List of external entities (e.g., ['U', 'Attacker']).")
    assets: list[str] = Field(description="List of assets like data stores (e.g., ['DB_P', 'DB_B']).")
    processes: list[str] = Field(description="List of processes (e.g., ['CDN', 'LB', 'WS']).")
    trust_boundaries: list[str] = Field(description="List of trust boundaries (e.g., ['Public Zone to Edge Zone']).")
    data_flows: list[DataFlow] = Field(description="List of data flows between components.")

class DFDOutput(BaseModel):
    dfd: DFDComponents
    metadata: dict

# --- Sample Input for Testing (if no documents are found) ---
SAMPLE_DOCUMENT_CONTENT = """
System: Web Application Security Model, Version 1.1, Finance Industry
External Entities: User (U), External Attacker
Assets: Profile Database (DB_P), Billing Database (DB_B)
Processes: Content Delivery Network (CDN), Load Balancer (LB), Web Server (WS), Message Queue (MQ), Worker (WRK), Admin Service (ADM), Admin Portal (ADM_P)
Trust Boundaries: Public Zone to Edge Zone, Edge Zone to Application DMZ, Application DMZ to Internal Core, Internal Core to Data Zone, Management Zone to Application DMZ
Data Flows:
- From User to CDN: User session tokens and requests for static assets, Confidential, HTTPS, JWT in Header
- From CDN to LB: Cached content and user requests, Confidential, HTTPS, mTLS
- From WS to DB_P: User profile data including names and email addresses, PII, JDBC/ODBC over TLS, Database Credentials from Secrets Manager
"""

# --- Load and Parse Documents ---
def load_documents(input_dir):
    logger.info(f"--- Loading documents from '{input_dir}' ---")
    write_progress(2, 0, 100, "Loading documents", f"Scanning {input_dir}")
    
    documents = []
    files_found = glob.glob(os.path.join(input_dir, "*.[tT][xX][tT]")) + glob.glob(os.path.join(input_dir, "*.[pP][dD][fF]"))
    total_files = len(files_found)
    
    for i, file_path in enumerate(files_found):
        if check_kill_signal(2):
            return []
            
        try:
            write_progress(2, int((i / total_files) * 30), 100, 
                         f"Loading file {i+1}/{total_files}", 
                         os.path.basename(file_path))
            
            if file_path.lower().endswith(".txt"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    documents.append(f.read())
                logger.info(f"Loaded text file: {file_path}")
            elif file_path.lower().endswith(".pdf"):
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = "".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
                    documents.append(text)
                logger.info(f"Loaded PDF file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")
    
    if not documents:
        logger.warning("--- No valid documents found. Using sample document content ---")
        documents = [SAMPLE_DOCUMENT_CONTENT]
        write_progress(2, 30, 100, "Using sample content", "No documents found")
    else:
        write_progress(2, 30, 100, f"Loaded {len(documents)} documents", "Ready for processing")
    
    return documents

# --- Prompt Engineering for Document Extraction ---
extract_prompt_template = """
You are a senior cybersecurity analyst specializing in threat modeling. Your task is to extract structured information from multiple input documents describing a system architecture and transform it into a standardized JSON format for a Data Flow Diagram (DFD). The documents may include architecture diagrams, design specs, or text descriptions in varied formats.

Using Chain-of-Thought reasoning:
1. Identify and extract key elements: project metadata (name, version, industry), external entities, assets (e.g., databases), processes, trust boundaries, and data flows.
2. Normalize component names (e.g., use 'DB_P' for 'Profile Database' if abbreviated elsewhere).
3. For data flows, capture source, destination, data description, classification (e.g., 'Confidential', 'PII'), protocol, and authentication mechanism.
4. Resolve conflicts across documents by prioritizing the most detailed description.
5. If information is ambiguous, flag it in the metadata with an 'assumptions' key.

Output a JSON object with:
- 'project_name': Project name (default: 'Unknown Project' if not specified).
- 'project_version': Version (default: '1.0').
- 'industry_context': Industry (default: 'Unknown').
- 'external_entities': List of external entities (e.g., ['U', 'Attacker']).
- 'assets': List of assets like databases (e.g., ['DB_P', 'DB_B']).
- 'processes': List of processes (e.g., ['CDN', 'LB', 'WS']).
- 'trust_boundaries': List of trust boundaries (e.g., ['Public Zone to Edge Zone']).
- 'data_flows': List of data flow objects with source, destination, data_description, data_classification, protocol, and authentication_mechanism.

Input Documents:
---
{documents}
---

Output ONLY the JSON, with no additional commentary or formatting.
"""

extract_prompt = ChatPromptTemplate.from_template(extract_prompt_template)

# --- Main Execution ---
logger.info("\n--- Starting Pre-Filter for Document Extraction ---")
write_progress(2, 0, 100, "Initializing", "Starting DFD extraction")

try:
    # Initialize LLM client
    write_progress(2, 5, 100, "Initializing LLM", f"Provider: {LLM_PROVIDER}")
    
    if LLM_PROVIDER == "scaleway":
        client, client_type = initialize_llm_client()
    else:
        raw_client, instructor_client, client_type = initialize_llm_client()

    # Load documents
    write_progress(2, 10, 100, "Loading documents", INPUT_DIR)
    documents = load_documents(INPUT_DIR)
    documents_combined = "\n--- Document Separator ---\n".join(documents)

    # Generate messages from the prompt template
    write_progress(2, 35, 100, "Preparing prompt", "Creating extraction prompt")
    messages = extract_prompt.format_messages(documents=documents_combined)

    # Log the prompt for debugging
    logger.info(f"--- Prompt sent to LLM ---\n{messages[0].content}")

    write_progress(2, 40, 100, "Calling LLM", f"Using {LLM_MODEL}")
    
    if client_type == "scaleway":
        # Use instructor client for Scaleway
        write_progress(2, 50, 100, "Processing with LLM", "Extracting DFD components")
        
        dfd_obj = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": messages[0].content}],
            response_model=DFDComponents,
            max_retries=5
        )
        
        write_progress(2, 70, 100, "Parsing response", "Validating structure")
        
        # Log raw response for debugging
        raw_client = OpenAI(base_url=SCW_API_URL, api_key=SCW_SECRET_KEY)
        raw_response = raw_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": messages[0].content}],
            response_format={"type": "json_object"}
        )
        logger.info(f"--- Raw Scaleway Response ---\n{raw_response.choices[0].message.content}")
        
        # Log token usage for Scaleway
        if hasattr(raw_response, 'usage'):
            prompt_tokens = raw_response.usage.prompt_tokens or 'N/A'
            completion_tokens = raw_response.usage.completion_tokens or 'N/A'
            total_tokens = raw_response.usage.total_tokens or 'N/A'
            logger.info(f"--- Token Usage for Scaleway ---")
            logger.info(f"Input Tokens: {prompt_tokens}")
            logger.info(f"Output Tokens: {completion_tokens}")
            logger.info(f"Total Tokens: {total_tokens}")

        
    else:
        # Use instructor client for Ollama
        write_progress(2, 50, 100, "Processing with LLM", "Extracting DFD components")
        
        dfd_obj = instructor_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": messages[0].content}],
            response_model=DFDComponents,
            max_retries=5
        )
        
        write_progress(2, 70, 100, "Parsing response", "Validating structure")
        
        # Log raw response for debugging
        raw_response = raw_client.chat(model=LLM_MODEL, messages=[{"role": "user", "content": messages[0].content}])
        logger.info(f"--- Raw Ollama Response ---\n{raw_response['message']['content']}")
        
        # Log Token Count and Performance
        prompt_tokens = raw_response.get('prompt_eval_count', 'N/A')
        prompt_duration_ns = raw_response.get('prompt_eval_duration', 0)
        response_tokens = raw_response.get('eval_count', 'N/A')
        response_duration_ns = raw_response.get('eval_duration', 0)
        prompt_duration_s = f"{prompt_duration_ns / 1_000_000_000:.2f}s" if prompt_duration_ns else "N/A"
        response_duration_s = f"{response_duration_ns / 1_000_000_000:.2f}s" if response_duration_ns else "N/A"
        logger.info(f"--- Token Usage & Performance ---")
        logger.info(f"Input Tokens: {prompt_tokens} (processed in {prompt_duration_s})")
        logger.info(f"Output Tokens: {response_tokens} (generated in {response_duration_s})")

    write_progress(2, 80, 100, "Building output", "Creating final structure")
    dfd_dict = dfd_obj.model_dump()
    
    # Add metadata
    output_dict = {
        "dfd": dfd_dict,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "source_documents": glob.glob(os.path.join(INPUT_DIR, "*.[tT][xX][tT]")) + glob.glob(os.path.join(INPUT_DIR, "*.[pP][dD][fF]")),
            "assumptions": [],
            "llm_provider": LLM_PROVIDER
        }
    }
    
    # Validate the output against schema
    write_progress(2, 90, 100, "Validating output", "Checking schema compliance")
    try:
        validated = DFDOutput(**output_dict)
        logger.info("--- JSON output validated successfully ---")
    except ValidationError as ve:
        logger.error(f"--- JSON validation failed: {ve} ---")
        write_progress(2, 100, 100, "Failed", f"Validation error: {str(ve)}")
        raise
    
    # Save the DFD components to a file
    write_progress(2, 95, 100, "Saving results", DFD_OUTPUT_PATH)
    with open(DFD_OUTPUT_PATH, 'w') as f:
        json.dump(output_dict, f, indent=2)
        
    logger.info("\n--- LLM Output (DFD Components) ---")
    print(json.dumps(output_dict, indent=2))
    logger.info(f"\n--- DFD components successfully saved to '{DFD_OUTPUT_PATH}' ---")
    
    # Summary stats
    dfd = output_dict['dfd']
    stats_msg = f"Extracted: {len(dfd.get('external_entities', []))} entities, " \
                f"{len(dfd.get('processes', []))} processes, " \
                f"{len(dfd.get('assets', []))} assets, " \
                f"{len(dfd.get('data_flows', []))} data flows"
    
    write_progress(2, 100, 100, "Complete", stats_msg)
    
    # Clean up progress file after success
    try:
        progress_file = os.path.join(OUTPUT_DIR, 'step_2_progress.json')
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except:
        pass

except Exception as e:
    logger.error(f"\n--- An error occurred during document extraction ---")
    logger.error(f"Error: {e}")
    logger.error("This could be due to the LLM not returning a well-formed JSON object or an issue with the input documents.")
    write_progress(2, 100, 100, "Failed", str(e))
    # Exit with error code so Flask knows it failed
    exit(1)