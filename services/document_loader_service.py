"""
Document Loader Service - Extracted from info_to_dfds.py for better modularity
Enhanced with better session handling and file discovery
"""

import os
import glob
import time
from typing import List, Tuple
from utils.logging_utils import logger
from utils.sample_documents import create_sample_requirements_document

class DocumentLoaderService:
    """Service for loading documents from Step 1 output."""
    
    def __init__(self, config: dict):
        self.config = config
    
    def load_documents_from_step1(self, output_dir: str, step: int = 2) -> Tuple[List[str], List[str]]:
        """
        Load ONLY the documents that were processed in Step 1.
        Enhanced with better session handling and debugging.
        """
        logger.info(f"📂 Loading documents from Step 1 results in {output_dir}")
        
        documents = []
        document_info = []
        
        # Get session ID from environment (set by pipeline service)
        session_id = os.getenv('SESSION_ID')
        logger.info(f"🔍 Session ID from environment: {session_id}")
        
        # Look for text files created by Step 1
        step1_files = []
        
        # **ENHANCED PATTERN MATCHING**
        
        # Pattern 1: YYYYMMDD_HHMMSS_extracted.txt (standard upload format)
        extracted_files = glob.glob(os.path.join(output_dir, "*_extracted.txt"))
        step1_files.extend(extracted_files)
        logger.info(f"📄 Found extracted files: {[os.path.basename(f) for f in extracted_files]}")
        
        # Pattern 2: session_SESSIONID.txt (session-specific files)
        session_files = glob.glob(os.path.join(output_dir, "session_*.txt"))
        step1_files.extend(session_files)
        logger.info(f"📄 Found session files: {[os.path.basename(f) for f in session_files]}")
        
        # Pattern 3: Recent text files (within last 2 hours, excluding samples)
        current_time = time.time()
        two_hours_ago = current_time - 7200
        
        for txt_file in glob.glob(os.path.join(output_dir, "*.txt")):
            file_mtime = os.path.getmtime(txt_file)
            basename = os.path.basename(txt_file)
            
            if (file_mtime > two_hours_ago and 
                txt_file not in step1_files and 
                not basename.startswith('sample_') and
                not basename.startswith('test_')):
                step1_files.append(txt_file)
                logger.info(f"📄 Found recent file: {basename}")
        
        # **SESSION-SPECIFIC FILE HANDLING**
        if session_id:
            logger.info(f"🔍 Looking for session-specific files for session: {session_id}")
            
            # Check multiple possible naming patterns for session files
            session_patterns = [
                f"session_{session_id}.txt",
                f"{session_id}_extracted.txt", 
                f"{session_id}.txt"
            ]
            
            for pattern in session_patterns:
                session_file = os.path.join(output_dir, pattern)
                if os.path.exists(session_file) and session_file not in step1_files:
                    step1_files.append(session_file)
                    logger.info(f"✅ Found session file: {pattern}")
                else:
                    logger.debug(f"❌ Session file not found: {pattern}")
        
        # **PRIORITIZE SESSION FILES**
        if session_id and step1_files:
            # If we have a session ID, prioritize files that contain the session ID
            session_specific_files = [
                f for f in step1_files 
                if session_id in os.path.basename(f)
            ]
            
            if session_specific_files:
                logger.info(f"🎯 Prioritizing session-specific files: {[os.path.basename(f) for f in session_specific_files]}")
                step1_files = session_specific_files
        
        # **FALLBACK HANDLING**
        if not step1_files:
            logger.warning("📁 No Step 1 output files found")
            
            # Last resort: check alternative directories
            alternative_dirs = ['./uploads', './output', './input_documents']
            for alt_dir in alternative_dirs:
                if alt_dir != output_dir and os.path.exists(alt_dir):
                    logger.info(f"🔍 Checking alternative directory: {alt_dir}")
                    alt_files = glob.glob(os.path.join(alt_dir, "*_extracted.txt"))
                    if alt_files:
                        step1_files.extend(alt_files)
                        logger.info(f"📄 Found files in {alt_dir}: {[os.path.basename(f) for f in alt_files]}")
                        break
            
            if not step1_files:
                # Final fallback: create sample content
                logger.warning("📄 No Step 1 files found anywhere, creating sample content")
                sample_content = create_sample_requirements_document()
                documents.append(sample_content)
                document_info.append("Sample Requirements Document (no Step 1 output found)")
                return documents, document_info
        
        # **PROCESS STEP 1 FILES**
        total_files = len(step1_files)
        successful_files = 0
        
        logger.info(f"📚 Processing {total_files} Step 1 files")
        
        for i, file_path in enumerate(step1_files):
            filename = os.path.basename(file_path)
            
            try:
                # Read the text content directly (it's already extracted)
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                logger.info(f"📖 Read file {filename}: {len(content)} characters")
                
                # Validate content length
                if len(content.strip()) < 50:
                    logger.warning(f"File {filename} too short ({len(content)} chars), skipping")
                    continue
                
                # Enhanced content validation
                if not self._validate_content_is_requirements(content, filename):
                    logger.warning(f"File {filename} doesn't appear to be requirements, but using anyway")
                    # Don't skip - use the content even if it doesn't look like requirements
                
                documents.append(content)
                document_info.append(f"{filename} ({len(content):,} chars) [Step 1 output]")
                successful_files += 1
                
                logger.info(f"✅ Successfully loaded: {filename}")
                
            except Exception as e:
                logger.error(f"❌ Failed to load {filename}: {e}")
                continue
        
        # **FINAL VALIDATION**
        if not documents:
            logger.error("❌ No valid documents loaded from Step 1")
            # Create sample as absolute fallback
            logger.info("📄 Creating sample document as final fallback")
            sample_content = create_sample_requirements_document()
            documents.append(sample_content)
            document_info.append("Sample Requirements Document (Step 1 files invalid)")
        
        logger.info(f"📚 Successfully loaded {successful_files}/{total_files} documents from Step 1")
        logger.info(f"📊 Total content: {sum(len(doc) for doc in documents):,} characters")
        
        return documents, document_info
    
    def _validate_content_is_requirements(self, content: str, filename: str) -> bool:
        """
        Validate that content appears to be requirements/technical documentation.
        Enhanced to be more lenient and informative.
        """
        content_lower = content.lower()
        
        # Technical indicators (more comprehensive)
        technical_indicators = [
            'system', 'application', 'software', 'database', 'server', 'api', 'web',
            'user', 'admin', 'authentication', 'authorization', 'security', 'data',
            'process', 'function', 'feature', 'requirement', 'specification',
            'architecture', 'design', 'implementation', 'interface', 'component',
            'service', 'module', 'client', 'browser', 'protocol', 'network',
            'encrypt', 'decrypt', 'hash', 'token', 'session', 'login', 'password',
            'input', 'output', 'request', 'response', 'endpoint', 'resource'
        ]
        
        # Business indicators
        business_indicators = [
            'business', 'customer', 'order', 'payment', 'transaction', 'account',
            'profile', 'product', 'service', 'workflow', 'process', 'operation',
            'management', 'report', 'dashboard', 'analytics', 'metric', 'kpi'
        ]
        
        # Count indicators
        technical_count = sum(1 for indicator in technical_indicators if indicator in content_lower)
        business_count = sum(1 for indicator in business_indicators if indicator in content_lower)
        
        total_indicators = technical_count + business_count
        content_words = len(content.split())
        
        # Calculate relevance score
        if content_words > 0:
            relevance_score = (total_indicators / content_words) * 100
        else:
            relevance_score = 0
        
        logger.info(f"📊 Content validation for {filename}:")
        logger.info(f"   Technical indicators: {technical_count}")
        logger.info(f"   Business indicators: {business_count}")
        logger.info(f"   Total words: {content_words}")
        logger.info(f"   Relevance score: {relevance_score:.2f}%")
        
        # More lenient threshold - accept if it has any relevant content
        is_valid = total_indicators >= 3 or relevance_score >= 0.5
        
        if not is_valid:
            logger.warning(f"⚠️  {filename} has low relevance but will be processed anyway")
        
        return True  # Always return True to process all uploaded content