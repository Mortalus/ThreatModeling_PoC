"""
Enhanced LLM service for threat generation with async support and detailed logging.
"""
import os
import json
import logging
import time
import asyncio
from typing import List, Dict, Any, Tuple, Optional, Callable
from datetime import datetime

from models.threat_models import ThreatModel, ComponentAnalysis

logger = logging.getLogger(__name__)

class LLMThreatService:
    """LLM service specialized for threat generation with async support."""
    
    def __init__(self, config: Dict[str, Any], stride_definitions: Dict[str, Tuple[str, str]]):
        self.config = config
        self.stride_definitions = stride_definitions
        self.client = None
        self.async_client = None
        
        # Progress tracking
        self.total_calls = 0
        self.expected_calls = 0
        self.progress_callback: Optional[Callable] = None
        
        # Initialize clients
        self._init_clients()
        
        # Threat prompt template
        self.threat_prompt_template = """You are a cybersecurity architect specializing in realistic threat modeling. Analyze this DFD component and generate ONLY the 1-2 most realistic and significant threats for the specified STRIDE category.

**Component:**
{component_info}

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
      "component_name": "{component_name}",
      "stride_category": "{cat_letter}",
      "threat_description": "Specific, realistic threat description focusing on actual attack scenarios",
      "mitigation_suggestion": "Actionable, specific mitigation strategies with implementation details",
      "impact": "Low|Medium|High|Critical",
      "likelihood": "Low|Medium|High",
      "references": ["Relevant security standards or attack frameworks"],
      "risk_score": "Critical|High|Medium|Low"
    }}
  ]
}}"""
    
    def _init_clients(self):
        """Initialize LLM clients based on provider."""
        provider = self.config.get('llm_provider', 'scaleway').lower()
        
        if provider == 'scaleway':
            api_key = (
                self.config.get('scw_secret_key') or 
                os.getenv('SCW_SECRET_KEY') or 
                os.getenv('SCW_API_KEY') or 
                os.getenv('SCALEWAY_API_KEY')
            )
            
            if not api_key:
                logger.warning("No Scaleway API key found, LLM features will be disabled")
                return
            
            try:
                from openai import OpenAI, AsyncOpenAI
                
                # Sync client
                self.client = OpenAI(
                    base_url=self.config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
                    api_key=api_key
                )
                
                # Async client
                self.async_client = AsyncOpenAI(
                    base_url=self.config.get('scw_api_url', 'https://api.scaleway.ai/v1'),
                    api_key=api_key
                )
                
                logger.info("✅ Scaleway LLM clients initialized (sync + async)")
                
            except ImportError:
                logger.warning("OpenAI library not available, LLM features will be disabled")
            except Exception as e:
                logger.error(f"Failed to initialize Scaleway clients: {e}")
                
        elif provider == 'ollama':
            # Ollama doesn't need initialization, just check if available
            endpoint = self.config.get('local_llm_endpoint', 'http://localhost:11434/api/generate')
            logger.info(f"Ollama configured with endpoint: {endpoint}")
        else:
            logger.error(f"Unsupported LLM provider: {provider}")
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        provider = self.config.get('llm_provider', 'scaleway').lower()
        
        if provider == 'scaleway':
            return self.client is not None
        elif provider == 'ollama':
            # Could ping the endpoint to check
            return True
        
        return False
    
    def set_expected_calls(self, count: int):
        """Set expected number of calls for progress tracking."""
        self.expected_calls = count
        self.total_calls = 0
    
    def set_progress_callback(self, callback: Callable):
        """Set progress callback."""
        self.progress_callback = callback
    
    def _log_call_progress(self, message: str, success: bool = True):
        """Log LLM call progress with detailed information."""
        self.total_calls += 1
        
        if self.config.get('detailed_llm_logging', True):
            percentage = (self.total_calls / self.expected_calls * 100) if self.expected_calls > 0 else 0
            status = "✅" if success else "❌"
            logger.info(f"{status} LLM Call {self.total_calls}/{self.expected_calls} ({percentage:.1f}%): {message}")
    
    def generate_threats(self, component: ComponentAnalysis, cat_letter: str, 
                        cat_name: str, cat_def: str) -> List[ThreatModel]:
        """Generate threats using LLM (sync version)."""
        start_time = time.time()
        
        try:
            prompt = self._build_threat_prompt(component, cat_letter, cat_name, cat_def)
            
            if self.config.get('llm_provider', 'scaleway').lower() == 'scaleway':
                response = self._generate_scaleway(prompt)
            else:
                response = self._generate_ollama(prompt)
            
            # Parse response
            threats = self._parse_threat_response(response, component.name, cat_letter)
            
            elapsed = time.time() - start_time
            self._log_call_progress(f"{cat_name} threats for {component.name} in {elapsed:.1f}s", True)
            
            return threats
            
        except Exception as e:
            self._log_call_progress(f"{cat_name} threats for {component.name} - FAILED", False)
            logger.error(f"LLM threat generation failed: {e}")
            
            if self.config.get('debug_mode', False):
                return []
            raise
    
    async def generate_threats_async(self, component: ComponentAnalysis, cat_letter: str,
                                   cat_name: str, cat_def: str) -> List[ThreatModel]:
        """Generate threats using LLM (async version)."""
        start_time = time.time()
        
        try:
            prompt = self._build_threat_prompt(component, cat_letter, cat_name, cat_def)
            
            if self.config.get('llm_provider', 'scaleway').lower() == 'scaleway':
                response = await self._generate_scaleway_async(prompt)
            else:
                response = await self._generate_ollama_async(prompt)
            
            # Parse response
            threats = self._parse_threat_response(response, component.name, cat_letter)
            
            elapsed = time.time() - start_time
            self._log_call_progress(f"{cat_name} threats for {component.name} (async) in {elapsed:.1f}s", True)
            
            return threats
            
        except Exception as e:
            self._log_call_progress(f"{cat_name} threats for {component.name} (async) - FAILED", False)
            logger.error(f"Async LLM threat generation failed: {e}")
            
            if self.config.get('debug_mode', False):
                return []
            raise
    
    async def generate_threats_for_components_batch(self, 
                                                  component_categories: List[Tuple[ComponentAnalysis, str, str, str]]) -> List[ThreatModel]:
        """Generate threats for multiple components in parallel using async processing."""
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
        """Build threat generation prompt."""
        component_info = {
            'name': component.name,
            'type': component.type,
            'details': component.details,
            'risk_score': component.risk_score
        }
        
        return self.threat_prompt_template.format(
            component_info=json.dumps(component_info, indent=2),
            component_name=component.name,
            cat_letter=cat_letter,
            cat_name=cat_name,
            cat_def=cat_def
        )
    
    def _generate_scaleway(self, prompt: str) -> Dict[str, Any]:
        """Generate response using Scaleway (sync)."""
        if not self.client:
            raise RuntimeError("Scaleway client not initialized")
        
        response = self.client.chat.completions.create(
            model=self.config.get('llm_model', 'llama-3.3-70b-instruct'),
            messages=[
                {"role": "system", "content": "You are a cybersecurity expert. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.config.get('temperature', 0.2),
            max_tokens=self.config.get('max_tokens', 2048),
            response_format={"type": "json_object"}
        )
        
        return self._parse_json_response(response.choices[0].message.content)
    
    async def _generate_scaleway_async(self, prompt: str) -> Dict[str, Any]:
        """Generate response using Scaleway (async)."""
        if not self.async_client:
            raise RuntimeError("Scaleway async client not initialized")
        
        response = await self.async_client.chat.completions.create(
            model=self.config.get('llm_model', 'llama-3.3-70b-instruct'),
            messages=[
                {"role": "system", "content": "You are a cybersecurity expert. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.config.get('temperature', 0.2),
            max_tokens=self.config.get('max_tokens', 2048),
            response_format={"type": "json_object"}
        )
        
        return self._parse_json_response(response.choices[0].message.content)
    
    def _generate_ollama(self, prompt: str) -> Dict[str, Any]:
        """Generate response using Ollama (sync)."""
        import requests
        
        response = requests.post(
            self.config.get('local_llm_endpoint', 'http://localhost:11434/api/generate'),
            json={
                "model": self.config.get('llm_model', 'llama2'),
                "prompt": prompt + "\n\nIMPORTANT: Output ONLY valid JSON, no other text.",
                "stream": False,
                "options": {
                    "temperature": self.config.get('temperature', 0.2),
                    "num_predict": self.config.get('max_tokens', 2048),
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            content = response.json().get('response', '')
            return self._parse_json_response(content)
        else:
            raise Exception(f"Ollama API error: {response.status_code} {response.text}")
    
    async def _generate_ollama_async(self, prompt: str) -> Dict[str, Any]:
        """Generate response using Ollama (async)."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.config.get('local_llm_endpoint', 'http://localhost:11434/api/generate'),
                json={
                    "model": self.config.get('llm_model', 'llama2'),
                    "prompt": prompt + "\n\nIMPORTANT: Output ONLY valid JSON, no other text.",
                    "stream": False,
                    "options": {
                        "temperature": self.config.get('temperature', 0.2),
                        "num_predict": self.config.get('max_tokens', 2048),
                    }
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get('response', '')
                    return self._parse_json_response(content)
                else:
                    text = await response.text()
                    raise Exception(f"Ollama API error: {response.status} {text}")
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON response from LLM."""
        # Clean response
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response content: {content[:500]}...")
            raise
    
    def _parse_threat_response(self, data: Dict, component_name: str, 
                              cat_letter: str) -> List[ThreatModel]:
        """Parse LLM response into ThreatModel objects."""
        threats = []
        
        if not isinstance(data, dict) or 'threats' not in data:
            logger.warning(f"Invalid threat response structure for {component_name}")
            return threats
        
        for threat_data in data.get('threats', []):
            try:
                # Ensure all required fields
                threat = ThreatModel(
                    component_name=component_name,
                    stride_category=cat_letter,
                    threat_description=threat_data.get('threat_description', ''),
                    mitigation_suggestion=threat_data.get('mitigation_suggestion', ''),
                    impact=threat_data.get('impact', 'Medium'),
                    likelihood=threat_data.get('likelihood', 'Medium'),
                    references=threat_data.get('references', []),
                    risk_score=threat_data.get('risk_score', 'Medium')
                )
                
                # Validate threat quality
                if len(threat.threat_description) > 30 and len(threat.mitigation_suggestion) > 20:
                    threats.append(threat)
                else:
                    logger.debug(f"Filtered out low-quality threat for {component_name}")
                    
            except Exception as e:
                logger.warning(f"Failed to parse threat for {component_name}: {e}")
                continue
        
        return threats