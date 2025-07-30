from qdrant_client import QdrantClient

# Try the most basic connection
client = QdrantClient("homebase", port=6333)
print(client.get_collections())