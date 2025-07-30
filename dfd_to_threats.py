import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, asdict
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

import instructor
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from ollama import AsyncClient, Client
from openai import AsyncOpenAI, OpenAI
import PyPDF2
import docx
import base64
import mimetypes

# Load environment variables
load_dotenv()

# --- Configuration ---
@dataclass
class Config:
    """Centralized configuration management"""
    llm_provider: str = "ollama"
    llm_model: str = "llama3:70b-instruct"
    vision_model: str = "llava:34b"
    scw_api_url: str = "https://api.scaleway.ai/4a8fd76b-8606-46e6-afe6-617ce8eeb948/v1"
    scw_secret_key: Optional[str] = None
    input_dir: Path = Path("./input_documents")
    output_dir: Path = Path("./output")
    dfd_output_path: Path = Path("./output/dfd_components.json")
    max_workers: int = 4
    chunk_size: int = 5000  # For document chunking if needed
    
    def __post_init__(self):
        # Override with environment variables
        self.llm_provider = os.getenv("LLM_PROVIDER", self.llm_provider).lower()
        self.llm_model = os.getenv("LLM_MODEL", self.llm_model)
        self.vision_model = os.getenv("VISION_MODEL", 
                                     "llava:34b" if self.llm_provider == "ollama" else self.llm_model)
        self.scw_api_url = os.getenv("SCW_API_URL", self.scw_api_url)
        self.scw_secret_key = os.getenv("SCW_SECRET_KEY", self.scw_secret_key)
        self.input_dir = Path(os.getenv("INPUT_DIR", str(self.input_dir)))
        self.output_dir = Path(os.getenv("OUTPUT_DIR", str(self.output_dir)))
        self.dfd_output_path = Path(os.getenv("DFD_OUTPUT_PATH", str(self.dfd_output_path)))
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

# Initialize configuration
config = Config()

# --- Logging Setup ---
class LoggerSetup:
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a configured logger instance"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

logger = LoggerSetup.get_logger(__name__)

# --- DFD Schema ---
class DataFlow(BaseModel):
    source: str = Field(description="Source component of the data flow")
    destination: str = Field(description="Destination component of the data flow")
    data_description: str = Field(description="Description of data being transferred")
    data_classification: str = Field(description="Classification: 'Confidential', 'PII', or 'Public'")
    protocol: str = Field(description="Protocol used (e.g., 'HTTPS', 'JDBC/ODBC over TLS')")
    authentication_mechanism: str = Field(description="Authentication method (e.g., 'JWT in Header')")

class DFDComponents(BaseModel):
    project_name: str = Field(description="Name of the project")
    project_version: str = Field(description="Version of the project")
    industry_context: str = Field(description="Industry context")
    external_entities: List[str] = Field(description="List of external entities")
    assets: List[str] = Field(description="List of assets/data stores")
    processes: List[str] = Field(description="List of processes")
    trust_boundaries: List[str] = Field(description="List of trust boundaries")
    data_flows: List[DataFlow] = Field(description="List of data flows between components")

class DFDOutput(BaseModel):
    dfd: DFDComponents
    metadata: dict

# --- LLM Client Factory ---
class LLMClientFactory:
    """Factory for creating LLM clients with caching"""
    
    _clients = {}
    
    @classmethod
    def get_client(cls, provider: str = None) -> Tuple[Union[Client, OpenAI], Union[Client, OpenAI], str]:
        """Get or create LLM client with caching"""
        provider = provider or config.llm_provider
        
        if provider in cls._clients:
            return cls._clients[provider]
        
        if provider == "scaleway":
            if not config.scw_secret_key:
                raise ValueError("SCW_SECRET_KEY environment variable is required for Scaleway API.")
            
            raw_client = OpenAI(base_url=config.scw_api_url, api_key=config.scw_secret_key)
            instructor_client = instructor.from_openai(raw_client)
            logger.info("Scaleway OpenAI client initialized successfully")
            result = (raw_client, instructor_client, "scaleway")
        else:  # Default to Ollama
            raw_client = Client()
            instructor_client = instructor.patch(Client())
            logger.info("Ollama client initialized successfully")
            result = (raw_client, instructor_client, "ollama")
        
        cls._clients[provider] = result
        return result

# --- Document Loaders ---
class DocumentLoader:
    """Efficient document loading with parallel processing"""
    
    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.pdf', '.docx', '.png', '.jpg', '.jpeg'
    }
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_mime_type(file_path: Path) -> str:
        """Get MIME type with caching"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or 'application/octet-stream'
    
    @classmethod
    def load_text_file(cls, file_path: Path) -> str:
        """Load text-based files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    @classmethod
    def load_pdf_file(cls, file_path: Path) -> str:
        """Load PDF files with better error handling"""
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                pages = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            pages.append(text)
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num} from {file_path}: {e}")
                return "\n".join(pages)
        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {e}")
            return ""
    
    @classmethod
    def load_docx_file(cls, file_path: Path) -> str:
        """Load DOCX files"""
        try:
            doc = docx.Document(str(file_path))
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n".join(paragraphs)
        except Exception as e:
            logger.error(f"Failed to load DOCX {file_path}: {e}")
            return ""
    
    @classmethod
    def process_image_file(cls, file_path: Path, raw_client, vision_model: str) -> str:
        """Process image files using vision model"""
        vision_prompt = """You are an expert in analyzing diagrams, especially Data Flow Diagrams (DFD). 
Describe this diagram in full detail. Identify all external entities, processes, data stores (assets), 
trust boundaries, and every data flow with source, destination, data description, classification, 
protocol, authentication mechanism if possible. Be as comprehensive as possible."""
        
        try:
            if config.llm_provider == "ollama":
                response = raw_client.chat(
                    model=vision_model,
                    messages=[{"role": "user", "content": vision_prompt, "images": [str(file_path)]}]
                )
                return response['message']['content']
            elif config.llm_provider == "scaleway":
                with open(file_path, "rb") as f:
                    base64_image = base64.b64encode(f.read()).decode('utf-8')
                
                ext = file_path.suffix.lower()
                image_type = "png" if ext == ".png" else "jpeg"
                content = [
                    {"type": "text", "text": vision_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/{image_type};base64,{base64_image}"}}
                ]
                
                response = raw_client.chat.completions.create(
                    model=vision_model,
                    messages=[{"role": "user", "content": content}]
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {e}")
            return ""
    
    @classmethod
    def load_single_document(cls, file_path: Path, raw_client=None) -> Optional[str]:
        """Load a single document based on its type"""
        ext = file_path.suffix.lower()
        
        try:
            if ext in {'.txt', '.md'}:
                content = cls.load_text_file(file_path)
                logger.info(f"Loaded text file: {file_path}")
                return content
            elif ext == '.pdf':
                content = cls.load_pdf_file(file_path)
                logger.info(f"Loaded PDF file: {file_path}")
                return content
            elif ext == '.docx':
                content = cls.load_docx_file(file_path)
                logger.info(f"Loaded DOCX file: {file_path}")
                return content
            elif ext in {'.png', '.jpg', '.jpeg'} and raw_client:
                content = cls.process_image_file(file_path, raw_client, config.vision_model)
                logger.info(f"Processed image file: {file_path}")
                return content
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
        
        return None
    
    @classmethod
    def load_documents_parallel(cls, input_dir: Path) -> List[str]:
        """Load all documents in parallel"""
        logger.info(f"Loading documents from '{input_dir}'")
        
        # Find all supported files
        file_paths = [
            f for f in input_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in cls.SUPPORTED_EXTENSIONS
        ]
        
        if not file_paths:
            logger.warning("No valid documents found. Using sample document content.")
            return [SAMPLE_DOCUMENT_CONTENT]
        
        # Get raw client for image processing
        raw_client, _, _ = LLMClientFactory.get_client()
        
        # Load documents in parallel
        documents = []
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(cls.load_single_document, fp, raw_client): fp 
                for fp in file_paths
            }
            
            # Collect results
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    content = future.result()
                    if content:
                        documents.append(content)
                except Exception as e:
                    logger.error(f"Error processing {path}: {e}")
        
        return documents

# --- Sample Document Content ---
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

# --- Prompt Template ---
EXTRACT_PROMPT_TEMPLATE = """
You are a senior cybersecurity analyst specializing in threat modeling. Your task is to extract structured information from one or more input documents describing a system and transform it into a comprehensive and accurate JSON object representing a Data Flow Diagram (DFD).

Your analysis must be meticulous. Follow these reasoning steps precisely:

1. **Identify Core Components**: First, perform a full scan of the document(s) to identify and list all high-level components:
   * `project_name`, `project_version`, and `industry_context`
   * `external_entities`: Any user, actor, or system outside the primary application boundary
   * `processes`: The distinct computational components or services that handle data
   * `assets`: The data stores, such as databases, object storage buckets, or message queues
   * `trust_boundaries`: The defined boundaries separating zones of different trust levels

2. **Systematically Extract ALL Data Flows**: This is the most critical step. You must identify every single flow of data mentioned or implied in the documents. Create a data flow entry for each interaction type:
   * External-to-Process flows
   * Process-to-External flows
   * Process-to-Asset flows
   * Process-to-Process flows

3. **Detail and Classify Each Flow**: For every data flow, accurately populate all attributes:
   * Apply strict data classification (Confidential for sensitive data, Public only for truly public data)
   * Infer missing details from context when necessary

Input Documents:
---
{documents}
---

4. **Final Review**: Ensure every major action described in the use cases is represented by one or more data flows in your output.

Output ONLY the JSON, with no additional commentary or formatting.
"""

# --- Main Processing Class ---
class DFDExtractor:
    """Main class for DFD extraction"""
    
    def __init__(self):
        self.raw_client, self.instructor_client, self.client_type = LLMClientFactory.get_client()
        self.prompt_template = ChatPromptTemplate.from_template(EXTRACT_PROMPT_TEMPLATE)
    
    def extract_dfd(self, documents: List[str]) -> DFDOutput:
        """Extract DFD components from documents"""
        # Combine documents
        documents_combined = "\n--- Document Separator ---\n".join(documents)
        
        # Generate prompt
        messages = self.prompt_template.format_messages(documents=documents_combined)
        prompt_content = messages[0].content
        
        logger.info("Sending prompt to LLM...")
        
        # Get response
        if self.client_type == "scaleway":
            dfd_obj = self._extract_scaleway(prompt_content)
        else:
            dfd_obj = self._extract_ollama(prompt_content)
        
        # Create output
        dfd_dict = dfd_obj.model_dump()
        output_dict = {
            "dfd": dfd_dict,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_documents": list(str(f) for f in config.input_dir.iterdir() 
                                       if f.suffix.lower() in DocumentLoader.SUPPORTED_EXTENSIONS),
                "assumptions": [],
                "llm_provider": config.llm_provider,
                "model": config.llm_model
            }
        }
        
        # Validate output
        return DFDOutput(**output_dict)
    
    def _extract_scaleway(self, prompt_content: str) -> DFDComponents:
        """Extract using Scaleway API"""
        # Get structured response
        dfd_obj = self.instructor_client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": prompt_content}],
            response_model=DFDComponents,
            max_retries=5
        )
        
        # Log raw response for debugging
        raw_response = self.raw_client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": prompt_content}],
            response_format={"type": "json_object"}
        )
        
        self._log_token_usage_scaleway(raw_response)
        return dfd_obj
    
    def _extract_ollama(self, prompt_content: str) -> DFDComponents:
        """Extract using Ollama"""
        # Get structured response
        dfd_obj = self.instructor_client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": prompt_content}],
            response_model=DFDComponents,
            max_retries=5
        )
        
        # Log raw response for debugging
        raw_response = self.raw_client.chat(
            model=config.llm_model, 
            messages=[{"role": "user", "content": prompt_content}]
        )
        
        self._log_token_usage_ollama(raw_response)
        return dfd_obj
    
    @staticmethod
    def _log_token_usage_scaleway(response):
        """Log token usage for Scaleway"""
        if hasattr(response, 'usage'):
            logger.info(f"Token Usage - Input: {response.usage.prompt_tokens}, "
                       f"Output: {response.usage.completion_tokens}, "
                       f"Total: {response.usage.total_tokens}")
    
    @staticmethod
    def _log_token_usage_ollama(response):
        """Log token usage for Ollama"""
        prompt_tokens = response.get('prompt_eval_count', 'N/A')
        response_tokens = response.get('eval_count', 'N/A')
        prompt_duration = response.get('prompt_eval_duration', 0) / 1e9
        response_duration = response.get('eval_duration', 0) / 1e9
        
        logger.info(f"Token Usage - Input: {prompt_tokens} ({prompt_duration:.2f}s), "
                   f"Output: {response_tokens} ({response_duration:.2f}s)")

# --- Main Function ---
def main():
    """Main execution function"""
    logger.info("Starting DFD Extraction Process")
    
    try:
        # Load documents
        documents = DocumentLoader.load_documents_parallel(config.input_dir)
        
        # Extract DFD
        extractor = DFDExtractor()
        output = extractor.extract_dfd(documents)
        
        # Save output
        output_dict = output.model_dump()
        with open(config.dfd_output_path, 'w') as f:
            json.dump(output_dict, f, indent=2)
        
        # Log results
        logger.info("DFD Components:")
        print(json.dumps(output_dict, indent=2))
        logger.info(f"DFD components successfully saved to '{config.dfd_output_path}'")
        
    except Exception as e:
        logger.error(f"An error occurred during document extraction: {e}")
        raise

if __name__ == "__main__":
    main()