import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    @staticmethod
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
            'mitre_enabled': os.getenv('MITRE_ENABLED', 'true').lower() == 'true',
            'mitre_version': os.getenv('MITRE_VERSION', 'v13.1'),
            'scw_api_url': os.getenv('SCW_API_URL', 'https://api.scaleway.ai/v1'),
            'scw_secret_key': os.getenv('SCW_SECRET_KEY') or os.getenv('SCW_API_KEY')
        }

    @staticmethod
    def ensure_directories(upload_folder, output_folder, input_folder):
        for folder in [upload_folder, output_folder, input_folder]:
            os.makedirs(folder, exist_ok=True)