#!/usr/bin/env python3
# ingest_to_qdrant.py

"""
Standalone script to process documents from a directory, extract text (including OCR),
create embeddings, and upsert them into a Qdrant vector database.
"""

import os
import io
import logging
import uuid
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json

# --- Third-party libraries ---
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

@dataclass
class Config:
    """Configuration class for the ingestion pipeline."""
    source_docs_dir: str = os.getenv("SOURCE_DOCS_DIR", "rag_docs")
    qdrant_host: str = os.getenv("QDRANT_HOST", "http://localhost:6333")
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "threat_models")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
    vector_size: int = int(os.getenv("VECTOR_SIZE", "768"))
    distance_metric: str = os.getenv("DISTANCE_METRIC", "COSINE")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "100"))
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    skip_existing: bool = os.getenv("SKIP_EXISTING", "true").lower() == "true"
    cache_embeddings: bool = os.getenv("CACHE_EMBEDDINGS", "false").lower() == "true"
    cache_dir: str = os.getenv("CACHE_DIR", ".cache")

class DocumentProcessor:
    """Handles document processing and text extraction."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def get_file_hash(self, file_path: str) -> str:
        """Generate a hash for file content to detect changes."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def extract_text_from_scanned_pdf(self, pdf_path: str) -> List[Document]:
        """Extract text from a scanned PDF using PyMuPDF and OCR."""
        self.logger.info(f"Performing OCR on PDF: {pdf_path}")
        documents = []
        
        try:
            doc = fitz.open(pdf_path)
            file_hash = self.get_file_hash(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                # Process images on the page
                for img in page.get_images(full=True):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image = Image.open(io.BytesIO(image_bytes))
                        ocr_text = pytesseract.image_to_string(image, lang='eng')
                        if ocr_text.strip():
                            text += "\n" + ocr_text
                    except Exception as e:
                        self.logger.warning(f"OCR failed for image on page {page_num + 1} in {pdf_path}: {e}")
                
                if text.strip():
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                "source": pdf_path,
                                "page": page_num + 1,
                                "file_hash": file_hash,
                                "file_type": "pdf",
                                "processing_method": "ocr"
                            },
                        )
                    )
            doc.close()
            
        except Exception as e:
            self.logger.error(f"Failed to process PDF {pdf_path}: {e}")
            
        return documents

    def extract_text_from_image(self, image_path: str) -> List[Document]:
        """Extract text from a standalone image using OCR."""
        self.logger.debug(f"Processing image: {image_path}")
        
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='eng')
            
            if text.strip():
                file_hash = self.get_file_hash(image_path)
                return [Document(
                    page_content=text,
                    metadata={
                        "source": image_path,
                        "file_hash": file_hash,
                        "file_type": "image",
                        "processing_method": "ocr"
                    }
                )]
        except Exception as e:
            self.logger.warning(f"Failed to process image {image_path}: {e}")
            
        return []

    def load_documents(self) -> List[Document]:
        """Load and process all documents from the source directory."""
        if not Path(self.config.source_docs_dir).exists():
            Path(self.config.source_docs_dir).mkdir(parents=True, exist_ok=True)
            self.logger.warning(f"Created source directory: {self.config.source_docs_dir}")
            return []

        documents = []
        
        # Process PDFs
        pdf_files = list(Path(self.config.source_docs_dir).rglob("*.pdf"))
        self.logger.info(f"Found {len(pdf_files)} PDF files")
        
        for pdf_path in pdf_files:
            try:
                loader = PyPDFLoader(str(pdf_path))
                docs = loader.load()
                
                # Add file metadata
                file_hash = self.get_file_hash(str(pdf_path))
                for doc in docs:
                    doc.metadata.update({
                        "file_hash": file_hash,
                        "file_type": "pdf",
                        "processing_method": "standard"
                    })
                
                if any(doc.page_content.strip() for doc in docs):
                    documents.extend(docs)
                else:
                    # Fallback to OCR
                    documents.extend(self.extract_text_from_scanned_pdf(str(pdf_path)))
                    
            except Exception as e:
                self.logger.warning(f"Standard PDF processing failed for {pdf_path}, trying OCR: {e}")
                documents.extend(self.extract_text_from_scanned_pdf(str(pdf_path)))

        # Process images
        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}
        image_files = [f for f in Path(self.config.source_docs_dir).rglob("*") 
                      if f.suffix.lower() in image_extensions]
        
        self.logger.info(f"Found {len(image_files)} image files")
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_file = {
                executor.submit(self.extract_text_from_image, str(img_path)): img_path 
                for img_path in image_files
            }
            
            for future in as_completed(future_to_file):
                try:
                    docs = future.result()
                    documents.extend(docs)
                except Exception as e:
                    img_path = future_to_file[future]
                    self.logger.error(f"Failed to process image {img_path}: {e}")

        # Process other text files
        other_loaders = {
            "**/*.md": TextLoader,
            "**/*.txt": TextLoader,
            "**/*.docx": Docx2txtLoader
        }
        
        for glob_pattern, loader_cls in other_loaders.items():
            try:
                loader = DirectoryLoader(
                    self.config.source_docs_dir,
                    glob=glob_pattern,
                    loader_cls=loader_cls,
                    use_multithreading=True,
                    silent_errors=True
                )
                docs = loader.load()
                
                # Add metadata to text files
                for doc in docs:
                    file_hash = self.get_file_hash(doc.metadata["source"])
                    doc.metadata.update({
                        "file_hash": file_hash,
                        "file_type": Path(doc.metadata["source"]).suffix.lower()[1:],
                        "processing_method": "standard"
                    })
                
                documents.extend(docs)
                self.logger.info(f"Loaded {len(docs)} documents with pattern {glob_pattern}")
                
            except Exception as e:
                self.logger.error(f"Failed loading files with pattern {glob_pattern}: {e}")

        return documents

class QdrantManager:
    """Manages Qdrant operations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """Connect to Qdrant and set up collection."""
        try:
            self.client = QdrantClient(self.config.qdrant_host)
            
            # Test connection
            collections = self.client.get_collections()
            self.logger.info("Successfully connected to Qdrant")
            
            # Setup collection
            return self._setup_collection()
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Qdrant at {self.config.qdrant_host}: {e}")
            return False
    
    def _setup_collection(self) -> bool:
        """Create or verify collection setup."""
        try:
            # Check if collection exists
            try:
                collection_info = self.client.get_collection(self.config.qdrant_collection_name)
                self.logger.info(f"Collection '{self.config.qdrant_collection_name}' exists with {collection_info.vectors_count} vectors")
                return True
                
            except Exception:
                # Create collection
                distance_map = {
                    "COSINE": models.Distance.COSINE,
                    "EUCLIDEAN": models.Distance.EUCLID,
                    "DOT": models.Distance.DOT
                }
                
                self.client.recreate_collection(
                    collection_name=self.config.qdrant_collection_name,
                    vectors_config=models.VectorParams(
                        size=self.config.vector_size,
                        distance=distance_map.get(self.config.distance_metric, models.Distance.COSINE)
                    ),
                )
                self.logger.info(f"Created collection '{self.config.qdrant_collection_name}'")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to setup collection: {e}")
            return False
    
    def check_document_exists(self, file_hash: str) -> bool:
        """Check if a document with the given hash already exists."""
        if not self.config.skip_existing:
            return False
            
        try:
            results = self.client.scroll(
                collection_name=self.config.qdrant_collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_hash",
                            match=models.MatchValue(value=file_hash)
                        )
                    ]
                ),
                limit=1
            )
            return len(results[0]) > 0
            
        except Exception as e:
            self.logger.warning(f"Failed to check document existence: {e}")
            return False
    
    def upsert_chunks(self, chunks: List[Document], embeddings: List[List[float]]) -> bool:
        """Upsert document chunks with embeddings to Qdrant."""
        try:
            points = [
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        **chunk.metadata,
                        "text": chunk.page_content,
                        "chunk_length": len(chunk.page_content)
                    }
                )
                for chunk, embedding in zip(chunks, embeddings)
            ]
            
            self.client.upsert(
                collection_name=self.config.qdrant_collection_name,
                points=points,
                wait=True
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upsert chunks: {e}")
            return False

def setup_logging(config: Config):
    """Setup logging configuration."""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Reduce noise from other libraries
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)

def main():
    """Main function to run the ingestion pipeline."""
    config = Config()
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    logger.info("=== Starting Qdrant Document Ingestion Pipeline ===")
    logger.info(f"Configuration: {config}")
    
    # Initialize components
    doc_processor = DocumentProcessor(config)
    qdrant_manager = QdrantManager(config)
    
    # Connect to Qdrant
    if not qdrant_manager.connect():
        logger.error("Failed to connect to Qdrant. Exiting.")
        return False
    
    # Load documents
    logger.info("Loading documents...")
    documents = doc_processor.load_documents()
    
    if not documents:
        logger.warning("No documents found to process.")
        return True
    
    logger.info(f"Loaded {len(documents)} document pages/sections")
    
    # Filter out existing documents if skip_existing is enabled
    if config.skip_existing:
        filtered_docs = []
        for doc in documents:
            if not qdrant_manager.check_document_exists(doc.metadata.get("file_hash", "")):
                filtered_docs.append(doc)
        
        skipped = len(documents) - len(filtered_docs)
        if skipped > 0:
            logger.info(f"Skipped {skipped} already processed documents")
        documents = filtered_docs
    
    if not documents:
        logger.info("All documents already processed. Exiting.")
        return True
    
    # Split documents into chunks
    logger.info("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap
    )
    chunks = text_splitter.split_documents(documents)
    
    if not chunks:
        logger.error("No chunks created from documents.")
        return False
    
    logger.info(f"Created {len(chunks)} chunks")
    
    # Initialize embedding model
    logger.info(f"Loading embedding model: {config.embedding_model}")
    try:
        embeddings_model = HuggingFaceEmbeddings(
            model_name=config.embedding_model,
            model_kwargs={'device': 'cpu'},  # Adjust as needed
            encode_kwargs={'normalize_embeddings': True}
        )
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return False
    
    # Process chunks in batches
    logger.info("Generating embeddings and uploading to Qdrant...")
    total_batches = (len(chunks) + config.batch_size - 1) // config.batch_size
    successful_batches = 0
    
    for i in range(0, len(chunks), config.batch_size):
        batch_num = i // config.batch_size + 1
        batch_chunks = chunks[i:i + config.batch_size]
        
        try:
            # Generate embeddings
            batch_texts = [chunk.page_content for chunk in batch_chunks]
            batch_embeddings = embeddings_model.embed_documents(batch_texts)
            
            # Upsert to Qdrant
            if qdrant_manager.upsert_chunks(batch_chunks, batch_embeddings):
                successful_batches += 1
                logger.info(f"✓ Processed batch {batch_num}/{total_batches}")
            else:
                logger.error(f"✗ Failed to process batch {batch_num}/{total_batches}")
                
        except Exception as e:
            logger.error(f"Error processing batch {batch_num}: {e}")
    
    # Final summary
    final_count = qdrant_manager.client.get_collection(
        collection_name=config.qdrant_collection_name
    ).vectors_count
    
    logger.info("=== Ingestion Pipeline Complete ===")
    logger.info(f"Successfully processed: {successful_batches}/{total_batches} batches")
    logger.info(f"Total vectors in collection '{config.qdrant_collection_name}': {final_count}")
    
    return successful_batches == total_batches

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)