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

# --- Configuration ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "scaleway").lower()  # Default to 'ollama', can be set to 'scaleway'
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-instruct")
SCW_API_URL = os.getenv("SCW_API_URL", "https://api.scaleway.ai/4a8fd76b-8606-46e6-afe6-617ce8eeb948/v1")
SCW_SECRET_KEY = os.getenv("SCW_API_KEY")
INPUT_DIR = os.getenv("INPUT_DIR", "./input_documents")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
DFD_OUTPUT_PATH = os.getenv("DFD_OUTPUT_PATH", os.path.join(OUTPUT_DIR, "dfd_components.json"))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
    documents = []
    for file_path in glob.glob(os.path.join(input_dir, "*.[tT][xX][tT]")) + glob.glob(os.path.join(input_dir, "*.[pP][dD][fF]")):
        try:
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

# --- Invocation and Output ---
logger.info("\n--- Starting Pre-Filter for Document Extraction ---")
try:
    # Initialize LLM client
    if LLM_PROVIDER == "scaleway":
        client, client_type = initialize_llm_client()
    else:
        raw_client, instructor_client, client_type = initialize_llm_client()

    # Load documents
    documents = load_documents(INPUT_DIR)
    documents_combined = "\n--- Document Separator ---\n".join(documents)

    # Generate messages from the prompt template
    messages = extract_prompt.format_messages(documents=documents_combined)

    # Log the prompt for debugging
    logger.info(f"--- Prompt sent to LLM ---\n{messages[0].content}")

    if client_type == "scaleway":
        # Use instructor client for Scaleway
        dfd_obj = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": messages[0].content}],
            response_model=DFDComponents,
            max_retries=5
        )
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
        dfd_obj = instructor_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": messages[0].content}],
            response_model=DFDComponents,
            max_retries=5
        )
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
    try:
        validated = DFDOutput(**output_dict)
        logger.info("--- JSON output validated successfully ---")
    except ValidationError as ve:
        logger.error(f"--- JSON validation failed: {ve} ---")
        raise
    
    # Save the DFD components to a file
    with open(DFD_OUTPUT_PATH, 'w') as f:
        json.dump(output_dict, f, indent=2)
        
    logger.info("\n--- LLM Output (DFD Components) ---")
    print(json.dumps(output_dict, indent=2))
    logger.info(f"\n--- DFD components successfully saved to '{DFD_OUTPUT_PATH}' ---")

except Exception as e:
    logger.error(f"\n--- An error occurred during document extraction ---")
    logger.error(f"Error: {e}")
    logger.error("This could be due to the LLM not returning a well-formed JSON object or an issue with the input documents.")