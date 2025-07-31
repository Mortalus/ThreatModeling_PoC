import uuid
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from stix2 import MemoryStore, Filter

# --- 1. SETUP ---
# Initialize Qdrant client (can be in-memory, on-prem, or cloud)
client = QdrantClient(":memory:") 
COLLECTION_NAME = "mitre_attack"

# Load a sentence-transformer model for creating embeddings
encoder = SentenceTransformer("all-MiniLM-L6-v2")

# Create the Qdrant collection if it doesn't exist
# We define a vector size (384 for MiniLM) and distance metric
try:
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=encoder.get_sentence_embedding_dimension(), 
            distance=models.Distance.COSINE
        ),
    )
    print(f"Collection '{COLLECTION_NAME}' created.")
except Exception as e:
    print(f"Collection may already exist. Error: {e}")


# --- 2. LOAD & PARSE STIX DATA ---
# Load the STIX data from the downloaded enterprise-attack.json file
store = MemoryStore(stix_data="path/to/your/enterprise-attack.json")

# Filter for all techniques ('attack-pattern' type in STIX)
attack_techniques = store.query(Filter("type", "=", "attack-pattern"))
print(f"Found {len(attack_techniques)} techniques in the STIX data.")


# --- 3. PROCESS AND UPSERT TO QDRANT ---
points_to_upsert = []
for tech in attack_techniques:
    # Skip deprecated or revoked techniques to keep the DB clean
    if getattr(tech, 'revoked', False) or getattr(tech, 'x_mitre_deprecated', False):
        continue

    technique_id = tech.external_references[0].external_id
    technique_name = tech.name
    technique_description = tech.description or "No description available."
    tactics = [phase.phase_name for phase in tech.kill_chain_phases] if tech.get('kill_chain_phases') else []
    
    # Create the text to be embedded by the model
    # A descriptive text helps the semantic search quality
    text_to_embed = f"Technique: {technique_name}. Tactic: {', '.join(tactics)}. Description: {technique_description}"

    # Create the metadata payload for filtering in Qdrant
    payload = {
        "id": technique_id,
        "name": technique_name,
        "tactics": tactics,
        "description": technique_description,
        "source": "MITRE ATT&CK",
        "url": tech.external_references[0].url if tech.get('external_references') else ""
    }

    # Create a Qdrant PointStruct
    point = models.PointStruct(
        id=str(uuid.uuid4()),  # Assign a unique ID for the point
        vector=encoder.encode(text_to_embed).tolist(),
        payload=payload
    )
    points_to_upsert.append(point)

# Upsert all points to Qdrant in a single batch operation
if points_to_upsert:
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points_to_upsert,
        wait=True
    )
    print(f"Successfully upserted {len(points_to_upsert)} techniques to Qdrant.")