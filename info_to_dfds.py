#!/usr/bin/env python3
"""
Enhanced DFD Extraction Script - Complete Version
Extracts Data Flow Diagrams from uploaded documents using LLM-based analysis.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Any
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config
from services.dfd_extraction_service import DFDExtractionService
from utils.logging_utils import logger, setup_logging
from utils.progress_utils import write_progress, check_kill_signal, cleanup_progress_file
from utils.sample_documents import create_sample_requirements_document

class DocumentLoaderService:
    """Service for loading documents from Step 1 output."""
    
    def __init__(self, config: dict):
        self.config = config
    
    def load_documents_from_step1(self, output_dir: str, step: int = 2) -> Tuple[List[str], List[str]]:
        """
        Load ONLY the documents that were processed in Step 1.
        """
        logger.info(f"📂 Loading documents from Step 1 results in {output_dir}")
        
        documents = []
        document_info = []
        
        # Look for text files created by Step 1
        step1_files = []
        
        # Pattern 1: YYYYMMDD_HHMMSS_extracted.txt
        import glob
        extracted_files = glob.glob(os.path.join(output_dir, "*_extracted.txt"))
        step1_files.extend(extracted_files)
        
        # Pattern 2: session_SESSIONID.txt
        session_files = glob.glob(os.path.join(output_dir, "session_*.txt"))
        step1_files.extend(session_files)
        
        # Also check for recent text files (within last 2 hours)
        import time
        current_time = time.time()
        two_hours_ago = current_time - 7200
        
        for txt_file in glob.glob(os.path.join(output_dir, "*.txt")):
            file_mtime = os.path.getmtime(txt_file)
            if (file_mtime > two_hours_ago and 
                txt_file not in step1_files and 
                not os.path.basename(txt_file).startswith('sample_')):
                step1_files.append(txt_file)
        
        if not step1_files:
            logger.info("📁 No Step 1 output files found")
            
            # Check if we can find any recent upload based on session ID
            session_id = os.getenv('SESSION_ID')
            if session_id:
                session_file = os.path.join(output_dir, f"session_{session_id}.txt")
                extracted_file = os.path.join(output_dir, f"{session_id}_extracted.txt")
                
                if os.path.exists(session_file):
                    step1_files = [session_file]
                    logger.info(f"📄 Found session file: {os.path.basename(session_file)}")
                elif os.path.exists(extracted_file):
                    step1_files = [extracted_file]
                    logger.info(f"📄 Found extracted file: {os.path.basename(extracted_file)}")
            
            if not step1_files:
                # Last resort: create sample content
                logger.info("📁 No Step 1 files found, creating sample content")
                sample_content = create_sample_requirements_document()
                documents.append(sample_content)
                document_info.append("Sample Requirements Document (no Step 1 output found)")
                return documents, document_info
        
        # Process Step 1 files
        total_files = len(step1_files)
        successful_files = 0
        
        for i, file_path in enumerate(step1_files):
            filename = os.path.basename(file_path)
            
            try:
                # Read the text content directly (it's already extracted)
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Validate content
                if len(content.strip()) < 50:
                    logger.info(f"File {filename} too short, skipping")
                    continue
                
                # Basic validation that this looks like requirements/technical content
                if not self._validate_content_is_requirements(content, filename):
                    logger.info(f"File {filename} doesn't appear to be requirements, skipping")
                    continue
                
                documents.append(content)
                document_info.append(f"{filename} ({len(content):,} chars) [Step 1 output]")
                successful_files += 1
                
                logger.info(f"📄 Loaded Step 1 file: {filename} ({len(content):,} chars)")
                
            except Exception as e:
                logger.warning(f"Failed to load {filename}: {e}")
                continue
        
        if not documents:
            logger.warning("❌ No valid documents loaded from Step 1")
            # Create sample as absolute fallback
            sample_content = create_sample_requirements_document()
            documents.append(sample_content)
            document_info.append("Sample Requirements Document (Step 1 files invalid)")
        
        logger.info(f"📚 Successfully loaded {successful_files} documents from Step 1")
        return documents, document_info
    
    def _validate_content_is_requirements(self, content: str, filename: str) -> bool:
        """
        Validate that content appears to be requirements/technical documentation.
        """
        content_lower = content.lower()
        
        # Technical keywords that suggest this is requirements/design content
        technical_keywords = [
            'system', 'architecture', 'component', 'service', 'database',
            'api', 'interface', 'security', 'authentication', 'authorization',
            'user', 'admin', 'process', 'workflow', 'data', 'storage',
            'server', 'client', 'web', 'mobile', 'application', 'platform',
            'requirement', 'specification', 'design', 'implementation'
        ]
        
        # Count technical keywords
        keyword_count = sum(1 for keyword in technical_keywords if keyword in content_lower)
        
        # Check for structured content indicators
        structure_indicators = [
            'requirements:', 'specification:', 'architecture:', 'design:',
            'components:', 'services:', 'apis:', 'database:', 'security:',
            '1.', '2.', '3.',  # Numbered lists
            '- ', '* ',  # Bullet points
            'external entities:', 'processes:', 'data flows:', 'assets:'
        ]
        
        structure_count = sum(1 for indicator in structure_indicators if indicator in content_lower)
        
        # Accept if we have enough technical keywords or clear structure
        is_valid = keyword_count >= 3 or structure_count >= 2
        
        logger.debug(f"Content validation for {filename}: {keyword_count} keywords, {structure_count} structure indicators, valid: {is_valid}")
        
        return is_valid

def main():
    """Main execution function."""
    logger.info("=== Starting DFD Extraction ===")
    write_progress(2, 0, 100, "Initializing DFD extraction", "Loading configuration")
    
    try:
        # Get configuration
        config = Config.get_config()
        
        # Ensure directories exist
        Config.ensure_directories(config['output_dir'])
        
        logger.info(f"🔧 Configuration loaded:")
        logger.info(f"   LLM Provider: {config['llm_provider']}")
        logger.info(f"   LLM Model: {config['llm_model']}")
        logger.info(f"   Input Dir: {config['input_dir']}")
        logger.info(f"   Output Dir: {config['output_dir']}")
        
        # Initialize services
        write_progress(2, 10, 100, "Initializing services", "Setting up document loader and extraction service")
        
        doc_loader = DocumentLoaderService(config)
        extraction_service = DFDExtractionService(config)
        
        if check_kill_signal(2):
            write_progress(2, 100, 100, "Cancelled", "User requested stop")
            return 1
        
        # Load documents
        write_progress(2, 20, 100, "Loading documents", "Searching for Step 1 output files")
        
        # Try both input_documents and output directories
        documents1, doc_info1 = doc_loader.load_documents_from_step1(config['input_dir'])
        documents2, doc_info2 = doc_loader.load_documents_from_step1(config['output_dir'])
        
        # Use whichever has documents
        documents = documents1 if documents1 else documents2
        doc_info = doc_info1 if doc_info1 else doc_info2
        
        if not documents:
            logger.error("No documents found for processing")
            write_progress(2, 100, 100, "Failed", "No input documents found")
            return 1
        
        write_progress(2, 30, 100, "Documents loaded", f"Found {len(documents)} documents")
        
        if check_kill_signal(2):
            write_progress(2, 100, 100, "Cancelled", "User requested stop")
            return 1
        
        # Extract DFD
        write_progress(2, 40, 100, "Extracting DFD", "Analyzing documents with LLM")
        
        logger.info(f"🚀 Starting DFD extraction from {len(documents)} documents")
        result = extraction_service.extract_from_documents(documents, doc_info)
        
        if not result:
            logger.error("DFD extraction failed - no result returned")
            write_progress(2, 100, 100, "Failed", "DFD extraction returned no result")
            return 1
        
        if check_kill_signal(2):
            write_progress(2, 100, 100, "Cancelled", "User requested stop")
            return 1
        
        # Save output
        write_progress(2, 90, 100, "Saving output", "Writing DFD components to file")
        
        output_path = config.get('dfd_output_path') or os.path.join(config['output_dir'], 'dfd_components.json')
        
        logger.info(f"💾 Saving DFD to: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Verify the file was created and has content
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"✅ DFD file created successfully: {file_size} bytes")
            
            # Log summary
            if 'dfd' in result:
                dfd = result['dfd']
                logger.info(f"📊 DFD Summary:")
                logger.info(f"   External Entities: {len(dfd.get('external_entities', []))}")
                logger.info(f"   Processes: {len(dfd.get('processes', []))}")
                logger.info(f"   Assets: {len(dfd.get('assets', []))}")
                logger.info(f"   Data Flows: {len(dfd.get('data_flows', []))}")
                logger.info(f"   Trust Boundaries: {len(dfd.get('trust_boundaries', []))}")
        else:
            logger.error(f"❌ Failed to create output file: {output_path}")
            write_progress(2, 100, 100, "Failed", "Could not write output file")
            return 1
        
        write_progress(2, 100, 100, "Complete", f"DFD extraction completed successfully")
        cleanup_progress_file(2)
        
        logger.info("✅ DFD extraction completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"DFD extraction failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        write_progress(2, 100, 100, "Failed", str(e))
        return 1

if __name__ == "__main__":
    # Set up logging
    setup_logging()
    
    logger.info("--- Starting DFD Extraction Script ---")
    
    try:
        exit_code = main()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        sys.exit(1)