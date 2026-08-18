from app.services.ai.embeddings import EmbeddingService


service = EmbeddingService()

result = service.process(
    page_id=1,
    input_data="This is a historical manuscript preserved by Revive Script."
)

print("Model:", result["model"])
print("Dimension:", result["dimension"])
print("Vector length:", len(result["embedding"]))
print("First 10 values:", result["embedding"][:10])