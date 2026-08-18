from app.services.ai.embeddings import EmbeddingService
from app.services.ai.qdrant import QdrantService


embedding_service = EmbeddingService()
qdrant_service = QdrantService()

# ----------------------------------------------------
# 1. Embed and Store Document (Passage)
# ----------------------------------------------------
text = "This is a historical manuscript preserved by Revive Script."

embedding_result = embedding_service.process(
    page_id=1,
    input_data=text,
)

embedding = embedding_result["embedding"]

insert_result = qdrant_service.process(
    page_id=1,
    input_data={
        "embedding": embedding,
        "manuscript_id": 1,
        "script": "Devanagari",
        "language": "Hindi",
        "text": text,
        "source": "test",
    },
)

print("Qdrant insert result:")
print(insert_result)

# ----------------------------------------------------
# 2. Embed Query and Search in Qdrant
# ----------------------------------------------------
search_query = "historical manuscript preservation"

# Note: E5 models perform best when query text is prefixed with "query: "
search_embedding = embedding_service.process(
    page_id=1,
    input_data=f"query: {search_query}",
)["embedding"]

search_results = qdrant_service.search(
    embedding=search_embedding,
    limit=5,
)

print("\nSearch results:")
for hit in search_results:
    print(hit)

qdrant_service._get_client().close()