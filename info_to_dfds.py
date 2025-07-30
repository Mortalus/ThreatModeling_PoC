import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, AsyncIterator
from datetime import datetime
from dataclasses import dataclass, asdict, field
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import lru_cache, partial
import aiofiles
import aiofiles.os
from contextlib import asynccontextmanager

import instructor
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from ollama import AsyncClient, Client
from openai import AsyncOpenAI, OpenAI
import PyPDF2
import docx
import base64
import mimetypes
import hashlib
import pickle
from collections import defaultdict
import re

# Load environment variables
load_dotenv()

# --- Configuration ---
@dataclass
class Config:
    """Centralized configuration management with validation"""
    llm_provider: str = "ollama"
    llm_model: str = "llama3:8b"
    vision_model: str = "llava:34b"
    scw_api_url: str = "https://api.scaleway.ai/4a8fd76b-8606-46e6-afe6-617ce8eeb948/v1"
    scw_secret_key: Optional[str] = None
    input_dir: Path = Path("./input_documents")
    output_dir: Path = Path("./output")
    dfd_output_path: Path = Path("./output/dfd_components.json")
    cache_dir: Path = Path("./cache")
    max_workers: int = field(default_factory=lambda: min(32, (os.cpu_count() or 1) + 4))
    chunk_size: int = 5000
    batch_size: int = 10
    enable_cache: bool = True
    cache_ttl: int = 86400  # 24 hours
    max_retries: int = 3
    timeout: int = 300
    
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
        self.cache_dir = Path(os.getenv("CACHE_DIR", str(self.cache_dir)))
        self.enable_cache = os.getenv("ENABLE_CACHE", "true").lower() == "true"
        
        # Create directories
        for dir_path in [self.output_dir, self.cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Validate configuration
        if self.llm_provider == "scaleway" and not self.scw_secret_key:
            raise ValueError("SCW_SECRET_KEY environment variable is required for Scaleway API.")

# Initialize configuration
config = Config()

# --- Optimized Logging Setup ---
class LoggerSetup:
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, level: int = logging.INFO) -> logging.Logger:
        """Get a configured logger instance with caching"""
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        cls._loggers[name] = logger
        return logger

logger = LoggerSetup.get_logger(__name__)

# --- Optimized DFD Schema with Pydantic v2 ---
class DataFlow(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    source: str = Field(description="Source component of the data flow")
    destination: str = Field(description="Destination component of the data flow")
    data_description: str = Field(description="Description of data being transferred")
    data_classification: str = Field(description="Classification: 'Confidential', 'PII', or 'Public'")
    protocol: str = Field(description="Protocol used (e.g., 'HTTPS', 'JDBC/ODBC over TLS')")
    authentication_mechanism: str = Field(description="Authentication method (e.g., 'JWT in Header')")

class DFDComponents(BaseModel):
    model_config = ConfigDict(frozen=True)
    
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

# --- Cache Manager ---
class CacheManager:
    """Efficient file-based caching with async support"""
    
    def __init__(self, cache_dir: Path, ttl: int = 86400):
        self.cache_dir = cache_dir
        self.ttl = ttl
        self._cache_index = self._load_index()
    
    def _load_index(self) -> Dict[str, float]:
        """Load cache index"""
        index_path = self.cache_dir / ".cache_index.json"
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_index(self):
        """Save cache index"""
        index_path = self.cache_dir / ".cache_index.json"
        with open(index_path, 'w') as f:
            json.dump(self._cache_index, f)
    
    def _get_cache_key(self, content: str) -> str:
        """Generate cache key from content hash"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[str]:
        """Get cached content"""
        if not config.enable_cache:
            return None
        
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists():
            # Check TTL
            if key in self._cache_index:
                if datetime.now().timestamp() - self._cache_index[key] > self.ttl:
                    # Expired
                    await aiofiles.os.remove(cache_file)
                    del self._cache_index[key]
                    self._save_index()
                    return None
            
            async with aiofiles.open(cache_file, 'r') as f:
                return await f.read()
        return None
    
    async def set(self, key: str, value: str):
        """Set cached content"""
        if not config.enable_cache:
            return
        
        cache_file = self.cache_dir / f"{key}.cache"
        async with aiofiles.open(cache_file, 'w') as f:
            await f.write(value)
        
        self._cache_index[key] = datetime.now().timestamp()
        self._save_index()

# --- Async LLM Client Factory ---
class AsyncLLMClientFactory:
    """Factory for creating async LLM clients with connection pooling"""
    
    _clients = {}
    _async_clients = {}
    
    @classmethod
    async def get_async_client(cls, provider: str = None) -> Tuple[Union[AsyncClient, AsyncOpenAI], Union[AsyncClient, AsyncOpenAI], str]:
        """Get or create async LLM client"""
        provider = provider or config.llm_provider
        
        if provider in cls._async_clients:
            return cls._async_clients[provider]
        
        if provider == "scaleway":
            raw_client = AsyncOpenAI(
                base_url=config.scw_api_url, 
                api_key=config.scw_secret_key,
                max_retries=config.max_retries,
                timeout=config.timeout
            )
            instructor_client = instructor.from_openai(raw_client)
            result = (raw_client, instructor_client, "scaleway")
        else:  # ollama
            raw_client = AsyncClient()
            # Do not patch with instructor for Ollama; use raw client
            result = (raw_client, raw_client, "ollama")
        
        cls._async_clients[provider] = result
        logger.info(f"{provider.capitalize()} async client initialized")
        return result
    
    @classmethod
    def get_sync_client(cls, provider: str = None) -> Tuple[Union[Client, OpenAI], Union[Client, OpenAI], str]:
        """Get sync client for backward compatibility"""
        provider = provider or config.llm_provider
        
        if provider in cls._clients:
            return cls._clients[provider]
        
        if provider == "scaleway":
            raw_client = OpenAI(
                base_url=config.scw_api_url,
                api_key=config.scw_secret_key,
                max_retries=config.max_retries,
                timeout=config.timeout
            )
            instructor_client = instructor.from_openai(raw_client)
            result = (raw_client, instructor_client, "scaleway")
        else:  # ollama
            raw_client = Client()
            # Do not patch with instructor for Ollama; use raw client
            result = (raw_client, raw_client, "ollama")
        
        cls._clients[provider] = result
        return result

# --- Optimized Document Loaders ---
class AsyncDocumentLoader:
    """Async document loading with better error handling and chunking"""
    
    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.pdf', '.docx', '.png', '.jpg', '.jpeg'
    }
    
    TEXT_EXTENSIONS = {'.txt', '.md'}
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
    
    def __init__(self):
        self.cache_manager = CacheManager(config.cache_dir)
    
    @staticmethod
    @lru_cache(maxsize=256)
    def get_mime_type(file_path: str) -> str:
        """Get MIME type with caching"""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
    
    async def load_text_file_async(self, file_path: Path) -> str:
        """Async load text-based files"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return await f.read()
    
    def load_pdf_file_optimized(self, file_path: Path) -> str:
        """Optimized PDF loading with better memory management"""
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                total_pages = len(pdf_reader.pages)
                
                # Process in chunks for large PDFs
                chunk_size = 50
                all_text = []
                
                for start_idx in range(0, total_pages, chunk_size):
                    end_idx = min(start_idx + chunk_size, total_pages)
                    chunk_text = []
                    
                    for page_num in range(start_idx, end_idx):
                        try:
                            page = pdf_reader.pages[page_num]
                            text = page.extract_text()
                            if text:
                                chunk_text.append(text)
                        except Exception as e:
                            logger.warning(f"Error extracting page {page_num} from {file_path}: {e}")
                    
                    if chunk_text:
                        all_text.extend(chunk_text)
                
                return "\n".join(all_text)
        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {e}")
            return ""
    
    def load_docx_file_optimized(self, file_path: Path) -> str:
        """Optimized DOCX loading"""
        try:
            doc = docx.Document(str(file_path))
            # Use generator for memory efficiency
            paragraphs = (para.text for para in doc.paragraphs if para.text.strip())
            return "\n".join(paragraphs)
        except Exception as e:
            logger.error(f"Failed to load DOCX {file_path}: {e}")
            return ""
    
    async def process_image_file_async(self, file_path: Path) -> str:
        """Async process image files using vision model"""
        # Check cache first
        cache_key = self.cache_manager._get_cache_key(str(file_path))
        cached = await self.cache_manager.get(cache_key)
        if cached:
            logger.info(f"Using cached vision analysis for {file_path}")
            return cached
        
        vision_prompt = """You are an expert in analyzing diagrams, especially Data Flow Diagrams (DFD). 
Describe this diagram in full detail. Identify all external entities, processes, data stores (assets), 
trust boundaries, and every data flow with source, destination, data description, classification, 
protocol, authentication mechanism if possible. Be as comprehensive as possible."""
        
        try:
            raw_client, _, _ = await AsyncLLMClientFactory.get_async_client()
            
            if config.llm_provider == "ollama":
                response = await raw_client.chat(
                    model=config.vision_model,
                    messages=[{"role": "user", "content": vision_prompt, "images": [str(file_path)]}]
                )
                content = response['message']['content']
            else:  # scaleway
                async with aiofiles.open(file_path, 'rb') as f:
                    image_data = await f.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                
                ext = file_path.suffix.lower()
                image_type = "png" if ext == ".png" else "jpeg"
                content_list = [
                    {"type": "text", "text": vision_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/{image_type};base64,{base64_image}"}}
                ]
                
                response = await raw_client.chat.completions.create(
                    model=config.vision_model,
                    messages=[{"role": "user", "content": content_list}]
                )
                content = response.choices[0].message.content
            
            # Cache the result
            await self.cache_manager.set(cache_key, content)
            return content
            
        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {e}")
            return ""
    
    async def load_single_document_async(self, file_path: Path) -> Optional[str]:
        """Async load a single document"""
        ext = file_path.suffix.lower()
        
        try:
            if ext in self.TEXT_EXTENSIONS:
                content = await self.load_text_file_async(file_path)
                logger.info(f"Loaded text file: {file_path}")
                return content
            elif ext == '.pdf':
                # PDF loading is CPU-bound, use thread pool
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(
                    None, self.load_pdf_file_optimized, file_path
                )
                logger.info(f"Loaded PDF file: {file_path}")
                return content
            elif ext == '.docx':
                # DOCX loading is CPU-bound, use thread pool
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(
                    None, self.load_docx_file_optimized, file_path
                )
                logger.info(f"Loaded DOCX file: {file_path}")
                return content
            elif ext in self.IMAGE_EXTENSIONS:
                content = await self.process_image_file_async(file_path)
                logger.info(f"Processed image file: {file_path}")
                return content
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
        
        return None
    
    async def load_documents_async(self, input_dir: Path) -> List[str]:
        """Load all documents asynchronously with batching"""
        logger.info(f"Loading documents from '{input_dir}'")
        
        # Find all supported files
        file_paths = [
            f for f in input_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]
        
        if not file_paths:
            logger.warning("No valid documents found. Using sample document content.")
            return [SAMPLE_DOCUMENT_CONTENT]
        
        # Group files by type for optimized processing
        files_by_type = defaultdict(list)
        for fp in file_paths:
            ext = fp.suffix.lower()
            if ext in self.TEXT_EXTENSIONS:
                files_by_type['text'].append(fp)
            elif ext in self.IMAGE_EXTENSIONS:
                files_by_type['image'].append(fp)
            else:
                files_by_type['other'].append(fp)
        
        documents = []
        
        # Process text files in parallel (fast I/O)
        if files_by_type['text']:
            tasks = [self.load_single_document_async(fp) for fp in files_by_type['text']]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, str) and result:
                    documents.append(result)
        
        # Process other files with controlled concurrency
        for file_type in ['other', 'image']:
            if files_by_type[file_type]:
                # Process in batches to avoid overwhelming the system
                for i in range(0, len(files_by_type[file_type]), config.batch_size):
                    batch = files_by_type[file_type][i:i + config.batch_size]
                    tasks = [self.load_single_document_async(fp) for fp in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, str) and result:
                            documents.append(result)
        
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

# --- Optimized Prompt Template ---
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

# --- Async DFD Extractor ---
class AsyncDFDExtractor:
    """Async DFD extraction with retry logic and better error handling"""
    
    def __init__(self):
        self.prompt_template = ChatPromptTemplate.from_template(EXTRACT_PROMPT_TEMPLATE)
        self.cache_manager = CacheManager(config.cache_dir / "llm_responses")
    
    async def extract_dfd(self, documents: List[str]) -> DFDOutput:
        """Extract DFD components from documents asynchronously"""
        # Combine documents efficiently
        documents_combined = "\n--- Document Separator ---\n".join(documents)
        
        # Check cache
        cache_key = self.cache_manager._get_cache_key(documents_combined)
        cached_response = await self.cache_manager.get(cache_key)
        
        if cached_response:
            logger.info("Using cached DFD extraction")
            return DFDOutput(**json.loads(cached_response))
        
        # Generate prompt
        messages = self.prompt_template.format_messages(documents=documents_combined)
        prompt_content = messages[0].content
        
        logger.info("Sending prompt to LLM...")
        
        # Get clients
        raw_client, instructor_client, client_type = await AsyncLLMClientFactory.get_async_client()
        
        # Extract with retry logic
        for attempt in range(config.max_retries):
            try:
                if client_type == "scaleway":
                    dfd_obj = await self._extract_scaleway_async(
                        prompt_content, raw_client, instructor_client
                    )
                else:
                    dfd_obj = await self._extract_ollama_async(
                        prompt_content, raw_client
                    )
                
                # Create output
                output = self._create_output(dfd_obj)
                
                # Cache the result
                await self.cache_manager.set(cache_key, json.dumps(output.model_dump()))
                
                return output
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == config.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _extract_scaleway_async(self, prompt_content: str, raw_client, instructor_client) -> DFDComponents:
        """Extract using Scaleway API asynchronously"""
        # Get structured response
        dfd_obj = await instructor_client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": prompt_content}],
            response_model=DFDComponents,
            max_retries=2
        )
        
        # Log usage asynchronously
        asyncio.create_task(self._log_usage_async(raw_client, prompt_content, "scaleway"))
        
        return dfd_obj
    
    async def _extract_ollama_async(self, prompt_content: str, client) -> DFDComponents:
        """Extract using Ollama asynchronously"""
        # Strengthen prompt: Remove any prior output instruction and add a strict one at the end
        # Format schema nicely for the prompt
        schema_json = json.dumps(DFDComponents.model_json_schema(), indent=2)
        prompt_with_json_instruction = (
            prompt_content.rstrip()  # Trim any trailing output instructions
            + "\n\n"
            + "Return the response as a valid JSON object matching the following schema. "
            + "Your output must be EXACTLY the JSON object ONLY. Do NOT add any explanations, text, code fences, or additional formatting before or after the JSON:\n"
            + schema_json
        )
        
        response = await client.chat(
            model=config.llm_model,
            messages=[{"role": "user", "content": prompt_with_json_instruction}],
            options={"format": "json"}
        )
        
        # Extract content
        content = response['message']['content']
        
        # Log raw content for debugging
        logger.debug(f"Raw Ollama response content: {content}")
        
        # Parse with robust extraction
        try:
            dfd_dict = self.extract_json(content)
            dfd_obj = DFDComponents(**dfd_dict)
        except (json.JSONDecodeError, ValueError, ValidationError) as e:
            logger.error(f"Failed to parse Ollama response as DFDComponents: {e}")
            logger.error(f"Invalid response content: {content}")
            raise
        
        # Log usage asynchronously
        asyncio.create_task(self._log_usage_async(client, prompt_content, "ollama"))
        
        return dfd_obj
    
    def extract_json(self, text: str) -> dict:
            """Helper to extract and parse JSON from potentially noisy text"""
            if not text:
                raise ValueError("Empty response content")
            
            text = text.strip()
            
            # Remove code fences if present
            if text.startswith('```json'):
                text = text[7:].strip()
            elif text.startswith('```'):
                text = text[3:].strip()
            
            if text.endswith('```'):
                text = text[:-3].strip()
            
            # Find the JSON substring (largest {} block)
            match = re.search(r'\{.*\}', text, re.DOTALL | re.MULTILINE)
            if match:
                json_str = match.group(0)
                
                # **FIX**: Remove trailing commas that cause JSONDecodeError
                # This regex finds a comma followed by whitespace and then a } or ]
                # and removes the comma.
                json_str = re.sub(r',\s*([\}\]])', r'\1', json_str)
                
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    # Add more context to the error for easier debugging
                    raise ValueError(f"Invalid JSON after cleaning: {e}\nContent: {json_str[:500]}...")
            
            raise ValueError("No valid JSON found in response")
    
    async def _log_usage_async(self, client, prompt_content: str, provider: str):
        """Log token usage asynchronously"""
        try:
            if provider == "scaleway":
                response = await client.chat.completions.create(
                    model=config.llm_model,
                    messages=[{"role": "user", "content": prompt_content}],
                    response_format={"type": "json_object"},
                    max_tokens=1  # Minimal to just get usage
                )
                if hasattr(response, 'usage'):
                    logger.info(f"Token Usage - Input: {response.usage.prompt_tokens}, "
                               f"Output: {response.usage.completion_tokens}, "
                               f"Total: {response.usage.total_tokens}")
            else:  # ollama
                response = await client.chat(
                    model=config.llm_model,
                    messages=[{"role": "user", "content": prompt_content}],
                    options={"num_predict": 1}  # Minimal response
                )
                prompt_tokens = response.get('prompt_eval_count', 'N/A')
                response_tokens = response.get('eval_count', 'N/A')
                logger.info(f"Token Usage - Input: {prompt_tokens}, Output: {response_tokens}")
        except Exception as e:
            logger.debug(f"Failed to log usage: {e}")
    
    def _create_output(self, dfd_obj: DFDComponents) -> DFDOutput:
        """Create DFD output with metadata"""
        # Find source documents efficiently
        source_docs = []
        try:
            source_docs = [
                str(f) for f in config.input_dir.iterdir()
                if f.is_file() and f.suffix.lower() in AsyncDocumentLoader.SUPPORTED_EXTENSIONS
            ]
        except:
            pass
        
        output_dict = {
            "dfd": dfd_obj.model_dump(),
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_documents": source_docs,
                "assumptions": [],
                "llm_provider": config.llm_provider,
                "model": config.llm_model,
                "version": "2.0"  # Script version
            }
        }
        
        return DFDOutput(**output_dict)

# --- Main Async Function ---
async def async_main():
    """Main async execution function"""
    logger.info("Starting Optimized DFD Extraction Process")
    
    try:
        # Load documents asynchronously
        loader = AsyncDocumentLoader()
        documents = await loader.load_documents_async(config.input_dir)
        
        # Extract DFD asynchronously
        extractor = AsyncDFDExtractor()
        output = await extractor.extract_dfd(documents)
        
        # Save output asynchronously
        output_dict = output.model_dump()
        async with aiofiles.open(config.dfd_output_path, 'w') as f:
            await f.write(json.dumps(output_dict, indent=2))
        
        # Log results
        logger.info("DFD Components:")
        print(json.dumps(output_dict, indent=2))
        logger.info(f"DFD components successfully saved to '{config.dfd_output_path}'")
        
    except Exception as e:
        logger.error(f"An error occurred during document extraction: {e}")
        raise

# --- Entry Point ---
def main():
    """Entry point with async support"""
    # Run async main
    asyncio.run(async_main())

if __name__ == "__main__":
    main()