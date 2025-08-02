"""
Configuration settings for the threat modeling pipeline.
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
            
            # Analysis Parameters
            'confidence_threshold': float(os.getenv('CONFIDENCE_THRESHOLD', '0.75')),
            'similarity_threshold': float(os.getenv('SIMILARITY_THRESHOLD', '0.70')),
            'cve_relevance_years': int(os.getenv('CVE_RELEVANCE_YEARS', '5')),
            'max_path_length': int(os.getenv('MAX_PATH_LENGTH', '5')),
            'max_paths_to_analyze': int(os.getenv('MAX_PATHS_TO_ANALYZE', '20')),
            'max_components_to_analyze': int(os.getenv('MAX_COMPONENTS_TO_ANALYZE', '20')),
            'min_risk_score': int(os.getenv('MIN_RISK_SCORE', '3')),
            
            # External APIs
            'nvd_api_url': os.getenv('NVD_API_URL', 'https://services.nvd.nist.gov/rest/json/cves/2.0'),
            'cisa_kev_url': os.getenv('CISA_KEV_URL', 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'),
            
            # Logging
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        }

    @staticmethod
    def ensure_directories(*directories):
        """Ensure directories exist."""
        for directory in directories:
            os.makedirs(directory, exist_ok=True)