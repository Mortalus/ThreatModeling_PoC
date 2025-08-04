"""
Service for LLM interactions in DFD extraction.
Enhanced with async support, detailed logging, and proper error handling.
PRESERVES ALL ORIGINAL FUNCTIONALITY.
"""
import json
import logging
import asyncio
import aiohttp
import time
import requests
from typing import Optional, Dict, Any, Union
from models.dfd_models import SimpleDFDComponents, SimpleDataFlow
from services.rule_based_extractor import RuleBasedExtractor

logger = logging.getLogger(__name__)

# Conditional imports
try:
    from openai import OpenAI, AsyncOpenAI
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
    """Service for LLM-based DFD extraction with async support."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get('llm_provider', 'scaleway')
        self.model = config.get('llm_model', 'llama-3.3-70b-instruct')
        self.client = None
        self.async_client = None
        self.raw_client = None
        self.async_raw_client = None
        self.rule_extractor = RuleBasedExtractor()
        self.call_count = 0
        self.total_expected_calls = 0
        self.ollama_endpoint = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the LLM client with fallback options."""
        try:
            if self.provider == "scaleway" and OPENAI_AVAILABLE:
                # Initialize sync clients
                self.raw_client = OpenAI(
                    base_url=self.config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
                    api_key=self.config['scw_secret_key']
                )

                # Initialize async clients
                self.async_raw_client = AsyncOpenAI(
                    base_url=self.config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
                    api_key=self.config['scw_secret_key']
                )

                if INSTRUCTOR_AVAILABLE:
                    self.client = instructor.from_openai(self.raw_client)
                    logger.info("✅ Scaleway client with instructor initialized")
                else:
                    logger.info("✅ Scaleway client initialized (no structured output)")

            elif self.provider == "ollama":
                # For Ollama, we'll use direct HTTP requests
                self.ollama_endpoint = self.config.get('local_llm_endpoint', 'http://localhost:11434/api/generate')
                logger.info(f"✅ Ollama client configured for {self.ollama_endpoint}")
                logger.info(f"📊 Using model: {self.model}")

                # Test connection
                self._test_ollama_connection()

                # Mark as available for Ollama
                self.client = "ollama"  # Just a marker to indicate it's available
                self.async_client = "ollama"

            else:
                if not self.config.get('debug_mode', False):
                    raise ValueError(f"Unknown LLM provider: {self.provider}")
                else:
                    logger.warning("❌ Unknown LLM provider - debug mode enabled, will use rule-based extraction")

        except Exception as e:
            if not self.config.get('debug_mode', False):
                logger.error(f"❌ Failed to initialize LLM client: {e}")
                raise
            else:
                logger.warning(f"⚠️ Failed to initialize LLM client: {e} - debug mode enabled")
                self.client = None
                self.raw_client = None

    def _test_ollama_connection(self):
        """Test Ollama connection and log status."""
        try:
            test_url = self.ollama_endpoint.replace('/api/generate', '/api/tags')
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama server is reachable")
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                if self.model in model_names:
                    logger.info(f"✅ Model {self.model} is available")
                else:
                    logger.warning(f"⚠️ Model {self.model} not found. Available: {model_names}")
            else:
                logger.warning(f"⚠️ Ollama server returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Cannot reach Ollama server: {e}")

    def set_expected_calls(self, count: int):
        """Set the total expected number of LLM calls for progress tracking."""
        self.total_expected_calls = count
        self.call_count = 0
        logger.info(f"📊 Expecting {count} LLM calls for DFD extraction")

    def _log_call_progress(self, operation: str, success: bool = True):
        """Log progress of LLM calls with percentage."""
        self.call_count += 1
        if self.total_expected_calls > 0:
            percentage = (self.call_count / self.total_expected_calls) * 100
            status = "✅" if success else "❌"
            logger.info(f"{status} LLM Call {self.call_count}/{self.total_expected_calls} ({percentage:.1f}%) - {operation}")
        else:
            status = "✅" if success else "❌"
            logger.info(f"{status} LLM Call {self.call_count} - {operation}")

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call Ollama API directly (ORIGINAL METHOD PRESERVED)."""
        try:
            logger.info(f"🤖 Calling Ollama with model: {self.model}")
            logger.info(f"📝 Prompt length: {len(prompt)} characters")

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.get('temperature', 0.2),
                    "num_predict": self.config.get('max_tokens', 4096),
                    "top_p": 0.95,
                    "seed": 42  # For reproducibility
                }
            }

            logger.info("⏳ Waiting for Ollama response...")
            response = requests.post(
                self.ollama_endpoint,
                json=payload,
                timeout=self.config.get('timeout', 300)
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                logger.info(f"✅ Received response: {len(response_text)} characters")
                logger.debug(f"First 200 chars: {response_text[:200]}...")
                return response_text
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out - consider increasing timeout in settings")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama - is it running? (ollama serve)")
            return None
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return None

    async def _call_ollama_async(self, prompt: str) -> Optional[str]:
        """Call Ollama API asynchronously (NEW ASYNC METHOD)."""
        try:
            logger.info(f"🤖 Calling Ollama async with model: {self.model}")
            start_time = time.time()

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.get('temperature', 0.2),
                    "num_predict": self.config.get('max_tokens', 4096),
                    "top_p": 0.95,
                    "seed": 42
                }
            }

            timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 300))

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.ollama_endpoint, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get('response', '')
                        elapsed = time.time() - start_time
                        self._log_call_progress(f"Ollama async call completed in {elapsed:.1f}s", True)
                        return response_text
                    else:
                        error_text = await response.text()
                        elapsed = time.time() - start_time
                        error_msg = f"Ollama API error: {response.status} - {error_text}"
                        self._log_call_progress(f"Ollama async call failed after {elapsed:.1f}s", False)
                        logger.error(error_msg)
                        return None

        except Exception as e:
            elapsed = time.time() - start_time
            self._log_call_progress(f"Ollama async call failed after {elapsed:.1f}s", False)
            logger.error(f"Ollama async API error: {e}")
            return None

    def extract_dfd_components(self, content: str, doc_analysis: Dict) -> Optional[SimpleDFDComponents]:
        """Extract DFD components using LLM with fallback (ORIGINAL METHOD PRESERVED)."""
        if self.config.get('force_rule_based', False):
            logger.info("🔧 Force rule-based mode enabled, skipping LLM")
            return self.rule_extractor.extract(content, doc_analysis)

        # Check if we should use async mode
        if self.config.get('enable_async_processing', True):
            logger.info("⚡ Async processing enabled, using async extraction")
            return asyncio.run(self.extract_dfd_components_async(content, doc_analysis))

        # Original sync logic
        if self.provider == "ollama":
            logger.info("🔍 Using Ollama for DFD extraction")
            prompt = self._build_extraction_prompt(content, doc_analysis)
            response_text = self._call_ollama(prompt + "\n\nRespond with valid JSON only. Do not include any explanations or markdown formatting.")

            if response_text:
                try:
                    # Clean the response - remove any markdown or extra text
                    response_text = response_text.strip()

                    # Find JSON in the response
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1

                    if json_start >= 0 and json_end > json_start:
                        json_text = response_text[json_start:json_end]
                        data = json.loads(json_text)
                        logger.info("✅ Successfully parsed Ollama response")
                        return self._dict_to_simple_components(data)
                    else:
                        logger.error("No valid JSON found in response")
                        logger.debug(f"Response was: {response_text[:500]}...")
                        if self.config.get('debug_mode', False):
                            return self.rule_extractor.extract(content, doc_analysis)
                        else:
                            raise ValueError("No valid JSON found in Ollama response")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Ollama response as JSON: {e}")
                    logger.debug(f"Response was: {response_text[:500]}...")
                    if self.config.get('debug_mode', False):
                        return self.rule_extractor.extract(content, doc_analysis)
                    else:
                        raise ValueError(f"Failed to parse Ollama response: {e}")
            else:
                logger.warning("No response from Ollama")
                if self.config.get('debug_mode', False):
                    return self.rule_extractor.extract(content, doc_analysis)
                else:
                    raise RuntimeError("No response from Ollama server")

        # Original Scaleway logic
        if not self.raw_client:
            if self.config.get('debug_mode', False):
                logger.warning("No LLM client available, using rule-based extraction")
                return self.rule_extractor.extract(content, doc_analysis)
            else:
                raise RuntimeError("No LLM client available and debug mode is disabled")

        try:
            prompt = self._build_extraction_prompt(content, doc_analysis)

            logger.info("🔍 Using Scaleway for DFD extraction")
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
            logger.info("✅ Successfully parsed Scaleway response")
            return self._dict_to_simple_components(data)

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            if self.config.get('debug_mode', False):
                return self.rule_extractor.extract(content, doc_analysis)
            else:
                raise

    async def extract_dfd_components_async(self, content: str, doc_analysis: Dict) -> Optional[SimpleDFDComponents]:
        """Extract DFD components asynchronously (NEW ASYNC METHOD)."""
        logger.info("⚡ Starting async DFD extraction")
        start_time = time.time()

        try:
            # Check if we should use Ollama
            if self.provider == "ollama":
                prompt = self._build_extraction_prompt(content, doc_analysis)
                response_text = await self._call_ollama_async(prompt + "\n\nRespond with valid JSON only. Do not include any explanations or markdown formatting.")

                if response_text:
                    try:
                        # Clean the response - remove any markdown or extra text
                        response_text = response_text.strip()

                        # Find JSON in the response
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1

                        if json_start >= 0 and json_end > json_start:
                            json_text = response_text[json_start:json_end]
                            data = json.loads(json_text)
                            logger.info("✅ Successfully parsed Ollama async response")
                            return self._dict_to_simple_components(data)
                        else:
                            raise ValueError("No valid JSON found in response")

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Ollama async response as JSON: {e}")
                        if self.config.get('verbose_error_reporting', True):
                            logger.debug(f"Response was: {response_text[:500]}...")
                        raise
                else:
                    raise RuntimeError("No response from Ollama async call")

            # Scaleway async extraction
            elif self.async_raw_client:
                prompt = self._build_extraction_prompt(content, doc_analysis)

                logger.info("🔍 Using Scaleway for async DFD extraction")

                response = await self.async_raw_client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt + "\n\nRespond with valid JSON only."}],
                    temperature=self.config.get('temperature', 0.2),
                    max_tokens=self.config.get('max_tokens', 4096),
                    timeout=self.config.get('timeout', 300)
                )

                response_text = response.choices[0].message.content.strip()

                # Clean and parse JSON
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

                data = json.loads(response_text)
                elapsed = time.time() - start_time
                self._log_call_progress(f"Scaleway async call completed in {elapsed:.1f}s", True)
                logger.info("✅ Successfully parsed Scaleway async response")
                return self._dict_to_simple_components(data)

            else:
                raise RuntimeError("No async LLM client available")

        except Exception as e:
            elapsed = time.time() - start_time
            self._log_call_progress(f"Async extraction failed after {elapsed:.1f}s", False)

            if self.config.get('debug_mode', False):
                logger.warning(f"⚠️ LLM async extraction failed: {e} - falling back to rule-based")
                return self.rule_extractor.extract(content, doc_analysis)
            else:
                logger.error(f"❌ LLM async extraction failed: {e}")
                raise

    def _build_extraction_prompt(self, content: str, doc_analysis: Dict) -> str:
        """Build extraction prompt (ORIGINAL METHOD PRESERVED)."""
        # Truncate content if too long for the model
        max_content_length = 8000  # Leave room for the rest of the prompt
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n... [content truncated]"

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
{content}

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
        """Convert dictionary to SimpleDFDComponents (ORIGINAL METHOD PRESERVED)."""
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

        logger.info(f"📊 Extracted: {len(result.external_entities)} entities, "
                   f"{len(result.processes)} processes, {len(result.assets)} assets, "
                   f"{len(result.data_flows)} data flows")

        return result

    def is_available(self) -> bool:
        """Check if LLM service is available (ORIGINAL METHOD PRESERVED)."""
        if self.config.get('force_rule_based', False):
            return False

        if self.provider == "scaleway":
            return self.raw_client is not None
        elif self.provider == "ollama":
            return True  # Ollama availability is checked at runtime

        return False