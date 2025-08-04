"""
Service for generating threats using LLM.
Enhanced with async support, detailed logging, and proper error handling.
PRESERVES ALL ORIGINAL FUNCTIONALITY.
"""
import json
import logging
import asyncio
import aiohttp
import time
import requests
from typing import List, Dict, Any, Optional
from models.threat_models import ThreatModel, ComponentAnalysis

logger = logging.getLogger(__name__)

# Conditional imports
try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available")

class LLMThreatService:
    """Service for LLM-based threat generation with async support."""
    
    def __init__(self, config: Dict[str, Any], stride_definitions: Dict[str, tuple]):
        self.config = config
        self.stride_definitions = stride_definitions
        self.client = None
        self.async_client = None
        self.provider = config.get('llm_provider', 'scaleway')
        self.model = config.get('llm_model', 'llama-3.3-70b-instruct')
        self.ollama_endpoint = None
        self.call_count = 0
        self.total_expected_calls = 0
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LLM client (ORIGINAL METHOD PRESERVED)."""
        try:
            if self.provider == "scaleway" and OPENAI_AVAILABLE:
                if not self.config.get('scw_secret_key'):
                    if not self.config.get('debug_mode', False):
                        raise ValueError("No Scaleway API key found")
                    else:
                        logger.warning("⚠️ No Scaleway API key found, debug mode enabled")
                        return
                
                # Initialize sync client
                self.client = OpenAI(
                    base_url=self.config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
                    api_key=self.config['scw_secret_key']
                )
                
                # Initialize async client
                self.async_client = AsyncOpenAI(
                    base_url=self.config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
                    api_key=self.config['scw_secret_key']
                )
                
                logger.info("✅ Scaleway threat clients initialized successfully")
                
            elif self.provider == "ollama":
                self.ollama_endpoint = self.config.get('local_llm_endpoint', 'http://localhost:11434/api/generate')
                logger.info(f"✅ Ollama threat client configured for {self.ollama_endpoint}")
                logger.info(f"📊 Using model: {self.model}")
                
                # Test connection
                self._test_ollama_connection()
                
                # Mark as available for Ollama
                self.client = "ollama"  # Just a marker to indicate it's available
                self.async_client = "ollama"
                
            else:
                if not self.config.get('debug_mode', False):
                    raise ValueError(f"Unsupported LLM provider: {self.provider}")
                else:
                    logger.warning(f"❌ Unsupported LLM provider: {self.provider} - debug mode enabled")
                
        except Exception as e:
            if not self.config.get('debug_mode', False):
                logger.error(f"❌ Failed to initialize LLM threat client: {e}")
                raise
            else:
                logger.warning(f"⚠️ Failed to initialize LLM threat client: {e} - debug mode enabled")
                self.client = None
                self.async_client = None
    
    def _test_ollama_connection(self):
        """Test Ollama connection and log status (ORIGINAL METHOD PRESERVED)."""
        try:
            test_url = self.ollama_endpoint.replace('/api/generate', '/api/tags')
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama server is reachable for threat generation")
            else:
                logger.warning(f"⚠️ Ollama server returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Cannot reach Ollama server: {e}")
    
    def set_expected_calls(self, count: int):
        """Set the total expected number of LLM calls for progress tracking (NEW METHOD)."""
        self.total_expected_calls = count
        self.call_count = 0
        logger.info(f"📊 Expecting {count} LLM calls for threat generation")
    
    def _log_call_progress(self, operation: str, success: bool = True):
        """Log progress of LLM calls with percentage (NEW METHOD)."""
        self.call_count += 1
        if self.total_expected_calls > 0:
            percentage = (self.call_count / self.total_expected_calls) * 100
            status = "✅" if success else "❌"
            logger.info(f"{status} LLM Call {self.call_count}/{self.total_expected_calls} ({percentage:.1f}%) - {operation}")
        else:
            status = "✅" if success else "❌"
            logger.info(f"{status} LLM Call {self.call_count} - {operation}")
    
    def is_available(self) -> bool:
        """Check if LLM service is available (ORIGINAL METHOD PRESERVED)."""
        if self.config.get('force_rule_based', False):
            return False
        return self.client is not None
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call Ollama API directly (ORIGINAL METHOD PRESERVED)."""
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
    
    async def _call_ollama_async(self, prompt: str) -> Optional[str]:
        """Call Ollama API asynchronously (NEW ASYNC METHOD)."""
        try:
            logger.info(f"🤖 Calling Ollama async for threat generation with model: {self.model}")
            start_time = time.time()
            
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
            
            timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 300))
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.ollama_endpoint, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get('response', '')
                        elapsed = time.time() - start_time
                        self._log_call_progress(f"Ollama async threat call completed in {elapsed:.1f}s", True)
                        return response_text
                    else:
                        error_text = await response.text()
                        elapsed = time.time() - start_time
                        error_msg = f"Ollama API error: {response.status} - {error_text}"
                        self._log_call_progress(f"Ollama async threat call failed after {elapsed:.1f}s", False)
                        logger.error(error_msg)
                        return None
                        
        except Exception as e:
            elapsed = time.time() - start_time if 'start_time' in locals() else 0
            self._log_call_progress(f"Ollama async threat call failed after {elapsed:.1f}s", False)
            logger.error(f"Ollama async API error: {e}")
            return None
    
    def generate_threats(self, component: ComponentAnalysis, cat_letter: str, 
                        cat_name: str, cat_def: str) -> List[ThreatModel]:
        """Generate threats using LLM (ORIGINAL METHOD PRESERVED WITH ENHANCEMENTS)."""
        if not self.is_available():
            if not self.config.get('debug_mode', False):
                raise RuntimeError("LLM service not available for threat generation and debug mode is disabled")
            else:
                logger.warning("LLM service not available for threat generation")
                return []
        
        # Check if we should use async mode
        if self.config.get('enable_async_processing', True):
            return asyncio.run(self.generate_threats_async(component, cat_letter, cat_name, cat_def))
        else:
            return self._generate_threats_sync(component, cat_letter, cat_name, cat_def)
    
    def _generate_threats_sync(self, component: ComponentAnalysis, cat_letter: str, 
                              cat_name: str, cat_def: str) -> List[ThreatModel]:
        """Generate threats using synchronous LLM calls (ENHANCED ORIGINAL LOGIC)."""
        prompt = self._build_threat_prompt(component, cat_letter, cat_name, cat_def)
        
        try:
            # Handle Ollama (ORIGINAL LOGIC PRESERVED)
            if self.client == "ollama":
                logger.info(f"🎯 Generating {cat_name} threats for {component.name} using Ollama")
                start_time = time.time()
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
                            elapsed = time.time() - start_time
                            self._log_call_progress(f"{cat_name} threats for {component.name} (sync) in {elapsed:.1f}s", True)
                            logger.info(f"✅ Generated {len(threats)} {cat_name} threats")
                            return threats
                        else:
                            elapsed = time.time() - start_time
                            self._log_call_progress(f"{cat_name} threats for {component.name} (sync) failed after {elapsed:.1f}s", False)
                            logger.error(f"No valid JSON found in Ollama response for {cat_name}")
                            if self.config.get('debug_mode', False):
                                return []
                            else:
                                raise ValueError("No valid JSON found in Ollama response")
                            
                    except json.JSONDecodeError as e:
                        elapsed = time.time() - start_time
                        self._log_call_progress(f"{cat_name} threats for {component.name} (sync) failed after {elapsed:.1f}s", False)
                        logger.error(f"Failed to parse Ollama threat response: {e}")
                        if self.config.get('verbose_error_reporting', True):
                            logger.debug(f"Response was: {response_text[:500]}...")
                        if self.config.get('debug_mode', False):
                            return []
                        else:
                            raise ValueError(f"Failed to parse Ollama response: {e}")
                else:
                    elapsed = time.time() - start_time
                    self._log_call_progress(f"{cat_name} threats for {component.name} (sync) failed after {elapsed:.1f}s", False)
                    logger.warning(f"No response from Ollama for {cat_name} threats")
                    if self.config.get('debug_mode', False):
                        return []
                    else:
                        raise RuntimeError("No response from Ollama")
            
            # Handle Scaleway (ORIGINAL LOGIC PRESERVED)
            elif isinstance(self.client, OpenAI):
                logger.info(f"🎯 Generating {cat_name} threats for {component.name} using Scaleway")
                start_time = time.time()
                
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
                
                # Parse JSON response (ORIGINAL LOGIC PRESERVED)
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                data = json.loads(response_text)
                threats = self._parse_threat_response(data, component.name, cat_letter)
                elapsed = time.time() - start_time
                self._log_call_progress(f"{cat_name} threats for {component.name} (sync) in {elapsed:.1f}s", True)
                logger.info(f"✅ Generated {len(threats)} {cat_name} threats")
                return threats
            
            else:
                raise RuntimeError("No valid LLM client available")
                
        except Exception as e:
            self._log_call_progress(f"{cat_name} threats for {component.name} (sync) - FAILED", False)
            
            if self.config.get('debug_mode', False):
                logger.warning(f"⚠️ LLM threat generation failed: {e} - debug mode, returning empty")
                return []
            else:
                logger.error(f"❌ LLM threat generation failed: {e}")
                raise
    
    async def generate_threats_async(self, component: ComponentAnalysis, cat_letter: str, 
                                   cat_name: str, cat_def: str) -> List[ThreatModel]:
        """Generate threats using asynchronous LLM calls (NEW ASYNC METHOD)."""
        prompt = self._build_threat_prompt(component, cat_letter, cat_name, cat_def)
        
        try:
            # Handle Ollama async
            if self.async_client == "ollama":
                logger.info(f"🎯 Generating {cat_name} threats for {component.name} using Ollama (async)")
                response_text = await self._call_ollama_async(prompt)
                
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
                            logger.info(f"✅ Generated {len(threats)} {cat_name} threats (async)")
                            return threats
                        else:
                            raise ValueError("No valid JSON found in async Ollama response")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Ollama async threat response: {e}")
                        if self.config.get('verbose_error_reporting', True):
                            logger.debug(f"Response was: {response_text[:500]}...")
                        raise
                else:
                    raise RuntimeError("No response from Ollama async call")
            
            # Handle Scaleway async
            elif isinstance(self.async_client, AsyncOpenAI):
                logger.info(f"🎯 Generating {cat_name} threats for {component.name} using Scaleway (async)")
                start_time = time.time()
                
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a cybersecurity expert specializing in threat modeling."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.config.get('temperature', 0.2),
                    max_tokens=self.config.get('max_tokens', 2048),
                    timeout=self.config.get('timeout', 300)
                )
                
                response_text = response.choices[0].message.content.strip()
                
                # Parse JSON response
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                data = json.loads(response_text)
                threats = self._parse_threat_response(data, component.name, cat_letter)
                elapsed = time.time() - start_time
                self._log_call_progress(f"{cat_name} threats for {component.name} (async) in {elapsed:.1f}s", True)
                logger.info(f"✅ Generated {len(threats)} {cat_name} threats (async)")
                return threats
            
            else:
                raise RuntimeError("No valid async LLM client available")
                
        except Exception as e:
            self._log_call_progress(f"{cat_name} threats for {component.name} (async) - FAILED", False)
            
            if self.config.get('debug_mode', False):
                logger.warning(f"⚠️ LLM async threat generation failed: {e} - debug mode, returning empty")
                return []
            else:
                logger.error(f"❌ LLM async threat generation failed: {e}")
                raise
    
    async def generate_threats_for_components_batch(self, component_categories: List[tuple]) -> List[ThreatModel]:
        """Generate threats for multiple components in parallel using async processing (NEW BATCH METHOD)."""
        if not self.config.get('enable_async_processing', True):
            # Fall back to sequential processing
            all_threats = []
            for component, cat_letter, cat_name, cat_def in component_categories:
                threats = self.generate_threats(component, cat_letter, cat_name, cat_def)
                all_threats.extend(threats)
            return all_threats
        
        # Limit concurrent calls
        max_concurrent = self.config.get('max_concurrent_calls', 5)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(component, cat_letter, cat_name, cat_def):
            async with semaphore:
                return await self.generate_threats_async(component, cat_letter, cat_name, cat_def)
        
        # Create tasks for all threat generations
        tasks = [
            generate_with_semaphore(component, cat_letter, cat_name, cat_def)
            for component, cat_letter, cat_name, cat_def in component_categories
        ]
        
        # Execute all tasks concurrently
        logger.info(f"⚡ Starting {len(tasks)} concurrent threat generation tasks (max {max_concurrent} parallel)")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        all_threats = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                component, cat_letter, cat_name, cat_def = component_categories[i]
                logger.error(f"❌ Failed to generate {cat_name} threats for {component.name}: {result}")
                if not self.config.get('debug_mode', False):
                    raise result
            else:
                all_threats.extend(result)
        
        return all_threats
    
    def _build_threat_prompt(self, component: ComponentAnalysis, cat_letter: str, 
                           cat_name: str, cat_def: str) -> str:
        """Build threat generation prompt (ORIGINAL METHOD PRESERVED)."""
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
        """Parse LLM response into ThreatModel objects (ORIGINAL METHOD PRESERVED)."""
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