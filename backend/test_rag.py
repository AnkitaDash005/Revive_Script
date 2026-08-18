from app.services.ai.rag import RAGService

service = RAGService()

result = service.process(
    page_id=1,
    input_data={
        "query": "What is this manuscript about?",
        "limit": 5,
    },
)

print("\n=== RAG RESULT ===")

print("\nQuery:")
print(result["query"])

print("\nRetrieved:")
for item in result["retrieved"]:
    print(item)

print("\nAnswer:")
print(result["answer"])