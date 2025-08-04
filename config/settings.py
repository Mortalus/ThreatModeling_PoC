"""
Configuration settings for the threat modeling pipeline.
Enhanced with async processing and debug mode options.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    @staticmethod
    def get_config():
        """Get configuration from environment with defaults."""
        return {
            # LLM Configuration
            'llm_provider': os.getenv('LLM_PROVIDER', 'scaleway'),
            'llm_model': os.getenv('LLM_MODEL', 'llama-3.3-70b-instruct'),
            'local_llm_endpoint': os.getenv('LOCAL_LLM_ENDPOINT', 'http://localhost:11434/api/generate'),
            'custom_system_prompt': os.getenv('CUSTOM_SYSTEM_PROMPT', ''),
            'scw_api_url': os.getenv('SCW_API_URL', 'https://api.scaleway.ai/v1'),
            'scw_secret_key': os.getenv('SCW_SECRET_KEY') or os.getenv('SCW_API_KEY'),
            
            # Async Processing Configuration
            'enable_async_processing': os.getenv('ENABLE_ASYNC_PROCESSING', 'true').lower() == 'true',
            'max_concurrent_calls': int(os.getenv('MAX_CONCURRENT_CALLS', '5')),
            'detailed_llm_logging': os.getenv('DETAILED_LLM_LOGGING', 'true').lower() == 'true',
            
            # Debug Configuration
            'debug_mode': os.getenv('DEBUG_MODE', 'false').lower() == 'true',
            'force_rule_based': os.getenv('FORCE_RULE_BASED', 'false').lower() == 'true',
            'verbose_error_reporting': os.getenv('VERBOSE_ERROR_REPORTING', 'true').lower() == 'true',
            
            # Directories
            'input_dir': os.getenv('INPUT_DIR', './input_documents'),
            'output_dir': os.getenv('OUTPUT_DIR', './output'),
            'dfd_output_path': os.getenv('DFD_OUTPUT_PATH', './output/dfd_components.json'),
            'threats_output_path': os.getenv('THREATS_OUTPUT_PATH', './output/identified_threats.json'),
            'refined_threats_output_path': os.getenv('REFINED_THREATS_OUTPUT_PATH', './output/refined_threats.json'),
            'attack_paths_output': os.getenv('ATTACK_PATHS_OUTPUT', './output/attack_paths.json'),
            
            # Processing Parameters
            'timeout': int(os.getenv('PIPELINE_TIMEOUT', '5000')),
            'temperature': float(os.getenv('TEMPERATURE', '0.2')),
            'max_tokens': int(os.getenv('MAX_TOKENS', '4096')),
            'min_text_length': int(os.getenv('MIN_TEXT_LENGTH', '100')),
            'max_text_length': int(os.getenv('MAX_TEXT_LENGTH', '1000000')),
            
            # Feature Flags
            'enable_quality_check': os.getenv('ENABLE_DFD_QUALITY_CHECK', 'true').lower() == 'true',
            'enable_multi_pass': os.getenv('ENABLE_MULTI_PASS', 'true').lower() == 'true',
            'enable_mermaid': os.getenv('ENABLE_MERMAID', 'true').lower() == 'true',
            'enable_llm_enrichment': os.getenv('ENABLE_LLM_ENRICHMENT', 'true').lower() == 'true',
            'enable_vector_store': os.getenv('ENABLE_VECTOR_STORE', 'false').lower() == 'true',
            'mitre_enabled': os.getenv('MITRE_ENABLED', 'true').lower() == 'true',
            'mitre_version': os.getenv('MITRE_VERSION', 'v13.1'),
            
            # Threat Generation Specific
            'min_risk_score': int(os.getenv('MIN_RISK_SCORE', '3')),
            'max_components_to_analyze': int(os.getenv('MAX_COMPONENTS_TO_ANALYZE', '20')),
            'similarity_threshold': float(os.getenv('SIMILARITY_THRESHOLD', '0.70')),
        }
    
    @staticmethod
    def ensure_directories(*dirs):
        """Ensure all provided directories exist."""
        for directory in dirs:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def validate_async_config(config):
        """Validate async configuration parameters."""
        errors = []
        
        # Validate max concurrent calls
        max_concurrent = config.get('max_concurrent_calls', 5)
        if not isinstance(max_concurrent, int) or max_concurrent < 1 or max_concurrent > 50:
            errors.append("max_concurrent_calls must be between 1 and 50")
        
        # Check if async is enabled but provider doesn't support it
        if config.get('enable_async_processing') and config.get('llm_provider') == 'ollama':
            # Note: Ollama can still work with async via aiohttp
            pass
        
        return errors
    
    @staticmethod
    def get_llm_call_timeout(config):
        """Get timeout for individual LLM calls based on async mode."""
        base_timeout = config.get('timeout', 5000)
        
        if config.get('enable_async_processing'):
            # Shorter timeout per call in async mode
            return min(base_timeout // 2, 300)  # Max 5 minutes per call
        else:
            # Longer timeout for sync mode
            return base_timeout
    
    @staticmethod
    def should_use_debug_fallback(config):
        """Determine if debug fallback should be used."""
        return config.get('debug_mode', False) and not config.get('force_rule_based', False)
    
    @staticmethod
    def should_force_rule_based(config):
        """Determine if rule-based extraction should be forced."""
        return config.get('force_rule_based', False)