import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MitreToQdrantIngester:
    """Optimized ingester for MITRE ATT&CK data into Qdrant."""
    
    def __init__(
        self,
        qdrant_host: str = "homebase",
        qdrant_port: int = 6333,
        collection_name: str = "threat_models",
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int = 100,
        use_grpc: bool = True
    ):
        """
        Initialize the ingester.
        
        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            collection_name: Name of the collection to create/use
            model_name: Sentence transformer model name
            batch_size: Number of points to upsert in each batch
            use_grpc: Use gRPC for better performance
        """
        self.collection_name = collection_name
        self.batch_size = batch_size
        
        # Initialize Qdrant client with network configuration
        self.client = QdrantClient(
            host=qdrant_host,
            port=qdrant_port,
            prefer_grpc=use_grpc,  # gRPC is faster for bulk operations
            timeout=60  # Increase timeout for large operations
        )
        
        # Initialize encoder with optimizations
        self.encoder = SentenceTransformer(model_name)
        self.encoder.max_seq_length = 512  # Increase for longer descriptions
        self.vector_size = self.encoder.get_sentence_embedding_dimension()
        
        logger.info(f"Initialized with model: {model_name}, vector size: {self.vector_size}")
    
    def create_collection(self, recreate: bool = False) -> None:
        """Create or recreate the Qdrant collection with optimized settings."""
        try:
            collections = self.client.get_collections().collections
            exists = any(col.name == self.collection_name for col in collections)
            
            if exists and not recreate:
                logger.info(f"Collection '{self.collection_name}' already exists. Skipping creation.")
                return
            
            if exists and recreate:
                self.client.delete_collection(self.collection_name)
                logger.info(f"Deleted existing collection '{self.collection_name}'")
            
            # Create collection with optimized settings
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                ),
                # Optimize for search performance
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=20000,
                    memmap_threshold=50000
                ),
                # Configure HNSW index for better search performance
                hnsw_config=models.HnswConfigDiff(
                    m=16,
                    ef_construct=200,
                    full_scan_threshold=10000
                )
            )
            
            # Create payload indexes for common filters
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="tactics",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="id",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            
            logger.info(f"Created collection '{self.collection_name}' with optimized settings")
            
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise
    
    def load_stix_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load and parse STIX data directly from JSON for better performance."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"STIX file not found: {file_path}")
        
        logger.info(f"Loading STIX data from: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract techniques (attack-patterns) directly
        techniques = [
            obj for obj in data.get('objects', [])
            if obj.get('type') == 'attack-pattern'
            and not obj.get('revoked', False)
            and not obj.get('x_mitre_deprecated', False)
        ]
        
        logger.info(f"Loaded {len(techniques)} active techniques")
        return techniques
    
    def create_embedding_text(self, technique: Dict[str, Any]) -> str:
        """Create optimized text for embedding generation."""
        # Extract key information
        name = technique.get('name', '')
        description = technique.get('description', '')
        
        # Get tactics from kill chain phases
        tactics = []
        if 'kill_chain_phases' in technique:
            tactics = [phase['phase_name'] for phase in technique['kill_chain_phases']]
        
        # Get platforms if available
        platforms = technique.get('x_mitre_platforms', [])
        
        # Get data sources
        data_sources = technique.get('x_mitre_data_sources', [])
        
        # Build comprehensive text for better semantic search
        text_parts = [
            f"Technique: {name}",
            f"Tactics: {', '.join(tactics)}" if tactics else "",
            f"Platforms: {', '.join(platforms)}" if platforms else "",
            f"Description: {description[:1000]}",  # Limit description length
            f"Data Sources: {', '.join(data_sources[:5])}" if data_sources else ""
        ]
        
        return " ".join(filter(None, text_parts))
    
    def create_payload(self, technique: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive payload for Qdrant."""
        # Extract external references
        external_refs = technique.get('external_references', [])
        mitre_ref = next((ref for ref in external_refs if ref.get('source_name') == 'mitre-attack'), {})
        
        # Get tactics
        tactics = []
        if 'kill_chain_phases' in technique:
            tactics = list(set(phase['phase_name'] for phase in technique['kill_chain_phases']))
        
        # Create payload with all relevant fields
        payload = {
            "id": mitre_ref.get('external_id', ''),
            "name": technique.get('name', ''),
            "description": technique.get('description', ''),
            "tactics": tactics,
            "platforms": technique.get('x_mitre_platforms', []),
            "permissions_required": technique.get('x_mitre_permissions_required', []),
            "data_sources": technique.get('x_mitre_data_sources', []),
            "is_subtechnique": technique.get('x_mitre_is_subtechnique', False),
            "detection": technique.get('x_mitre_detection', ''),
            "mitigation": technique.get('x_mitre_mitigation', ''),
            "created": technique.get('created', ''),
            "modified": technique.get('modified', ''),
            "version": technique.get('x_mitre_version', ''),
            "url": mitre_ref.get('url', ''),
            "source": "MITRE ATT&CK"
        }
        
        return payload
    
    def batch_encode_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch encode texts for better performance."""
        # Use GPU if available
        embeddings = self.encoder.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        return embeddings.tolist()
    
    def ingest_techniques(self, file_path: str, recreate_collection: bool = False) -> None:
        """Main ingestion method with optimizations."""
        start_time = datetime.now()
        
        # Create/verify collection
        self.create_collection(recreate=recreate_collection)
        
        # Load techniques
        techniques = self.load_stix_data(file_path)
        
        if not techniques:
            logger.warning("No techniques found to ingest")
            return
        
        # Process in batches
        total_ingested = 0
        
        with tqdm(total=len(techniques), desc="Ingesting techniques") as pbar:
            for i in range(0, len(techniques), self.batch_size):
                batch = techniques[i:i + self.batch_size]
                
                # Prepare texts and payloads
                texts = []
                payloads = []
                
                for tech in batch:
                    texts.append(self.create_embedding_text(tech))
                    payloads.append(self.create_payload(tech))
                
                # Batch encode
                embeddings = self.batch_encode_texts(texts)
                
                # Create points
                points = [
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload=payload
                    )
                    for embedding, payload in zip(embeddings, payloads)
                ]
                
                # Upsert batch
                try:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=points,
                        wait=True
                    )
                    total_ingested += len(points)
                except Exception as e:
                    logger.error(f"Error upserting batch: {e}")
                    continue
                
                pbar.update(len(batch))
        
        # Final statistics
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Ingestion complete: {total_ingested} techniques in {elapsed:.2f} seconds")
        logger.info(f"Average: {elapsed/total_ingested:.3f} seconds per technique")
        
        # Verify collection info
        info = self.client.get_collection(self.collection_name)
        logger.info(f"Collection '{self.collection_name}' now has {info.points_count} points")
    
    def search_techniques(self, query: str, limit: int = 5, tactics_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for techniques with optional tactic filtering."""
        # Encode query
        query_vector = self.encoder.encode(query).tolist()
        
        # Build filter if tactics specified
        search_filter = None
        if tactics_filter:
            search_filter = models.Filter(
                should=[
                    models.FieldCondition(
                        key="tactics",
                        match=models.MatchAny(any=tactics_filter)
                    )
                ]
            )
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=limit,
            with_payload=True,
            score_threshold=0.3  # Minimum similarity threshold
        )
        
        return [
            {
                "score": hit.score,
                "id": hit.payload.get("id"),
                "name": hit.payload.get("name"),
                "tactics": hit.payload.get("tactics"),
                "description": hit.payload.get("description")[:200] + "..."
            }
            for hit in results
        ]


def main():
    """Example usage of the optimized ingester."""
    # Configuration
    QDRANT_HOST = "homebase"  # Change to your Qdrant server host
    QDRANT_PORT = 6333         # Change to your Qdrant server port
    STIX_FILE = "enterprise-attack.json"
    
    # Initialize ingester
    ingester = MitreToQdrantIngester(
        qdrant_host=QDRANT_HOST,
        qdrant_port=QDRANT_PORT,
        collection_name="threat_models",
        model_name="all-MiniLM-L6-v2",  # You can use a better model like "all-mpnet-base-v2"
        batch_size=100,
        use_grpc=True
    )
    
    # Ingest data
    try:
        ingester.ingest_techniques(
            file_path=STIX_FILE,
            recreate_collection=True  # Set to False to append to existing collection
        )
        
        # Example search
        print("\n--- Example Search ---")
        results = ingester.search_techniques(
            query="ransomware encryption techniques",
            limit=5,
            tactics_filter=["impact", "defense-evasion"]
        )
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['name']} (ID: {result['id']})")
            print(f"   Score: {result['score']:.3f}")
            print(f"   Tactics: {', '.join(result['tactics'])}")
            print(f"   Description: {result['description']}")
            
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise


if __name__ == "__main__":
    main()