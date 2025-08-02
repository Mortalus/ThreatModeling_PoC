"""
Service for loading and validating documents for DFD extraction.
"""
import os
import glob
import time
import logging
from typing import List, Tuple
from utils.sample_documents import create_sample_requirements_document

logger = logging.getLogger(__name__)

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
        extracted_files = glob.glob(os.path.join(output_dir, "*_extracted.txt"))
        step1_files.extend(extracted_files)
        
        # Pattern 2: session_SESSIONID.txt
        session_files = glob.glob(os.path.join(output_dir, "session_*.txt"))
        step1_files.extend(session_files)
        
        # Also check for recent text files (within last 2 hours)
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
        
        # Check for diagram indicators (these suggest it's NOT requirements)
        diagram_indicators = [
            'graph td', 'graph tb', 'graph lr', 'flowchart',
            'subgraph', 'classdef', '-->',
            '<?xml', '<svg',
            'digraph', 'node [', 'edge [',
            'participant ', 'activate ', 'deactivate ',
            '#!/usr/bin', 'import ', 'function ', 'class ',
            'select * from', 'insert into', 'create table',
        ]
        
        diagram_count = sum(1 for indicator in diagram_indicators if indicator in content_lower)
        
        if diagram_count >= 2:
            logger.info(f"File {filename} appears to be a diagram/code file (found {diagram_count} indicators)")
            return False
        
        # Check for requirements/technical content indicators
        requirements_indicators = [
            'system', 'user', 'requirement', 'functional', 'non-functional',
            'component', 'service', 'application', 'database', 'server',
            'security', 'authentication', 'authorization', 'data flow',
            'architecture', 'design', 'interface', 'api', 'endpoint',
            'business', 'process', 'workflow', 'use case', 'scenario'
        ]
        
        requirements_count = sum(1 for indicator in requirements_indicators 
                               if indicator in content_lower)
        
        if requirements_count < 3:
            logger.info(f"File {filename} lacks requirements terminology (found {requirements_count} terms)")
            return False
        
        # Check content length
        if len(content) < 100:
            logger.info(f"File {filename} too short for requirements ({len(content)} chars)")
            return False
        
        logger.info(f"File {filename} validated as requirements content ({requirements_count} indicators)")
        return True