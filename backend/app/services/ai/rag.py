from typing import Any

from app.services.ai.base import AIService
from app.services.ai.embeddings import EmbeddingService
from app.services.ai.qdrant import QdrantService
from app.services.ai.vlm import VLMService


class RAGService(AIService):
    """
    Retrieval-Augmented Generation service.

    Flow:
        Query
          ↓
        Embedding
          ↓
        Qdrant retrieval
          ↓
        Context construction
          ↓
        Gemini generation
    """

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.qdrant_service = QdrantService()
        self.vlm_service = VLMService()

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:

        if not isinstance(input_data, dict):
            raise TypeError(
                "RAG input_data must be a dictionary"
            )

        query = input_data.get("query")

        if not query:
            raise ValueError(
                "query is required"
            )

        limit = input_data.get("limit", 5)

        # --------------------------------------------------
        # 1. Convert query into embedding
        # --------------------------------------------------

        embedding_result = self.embedding_service.process(
            page_id=page_id,
            input_data=query,
        )

        query_embedding = embedding_result["embedding"]

        # --------------------------------------------------
        # 2. Search Qdrant
        # --------------------------------------------------

        retrieved_results = self.qdrant_service.search(
            embedding=query_embedding,
            limit=limit,
        )

        # --------------------------------------------------
        # 3. Build context from retrieved manuscripts
        # --------------------------------------------------

        context_parts = []

        for result in retrieved_results:
            payload = result.get("payload") or {}

            text = payload.get("text")

            if not text:
                continue

            context_parts.append(
                
                    f"Page ID: {payload.get('page_id')}\n"
                    f"Manuscript ID: {payload.get('manuscript_id')}\n"
                    f"Script: {payload.get('script')}\n"
                    f"Language: {payload.get('language')}\n"
                    f"Similarity: {result.get('score')}\n\n"
                    f"Text:\n{text}"
                
            )

        context = "\n\n---\n\n".join(context_parts)

        # --------------------------------------------------
        # 4. No relevant information found
        # --------------------------------------------------

        if not context:
            return {
                "page_id": page_id,
                "query": query,
                "retrieved": [],
                "context": "",
                "answer": "No relevant manuscript information was found.",
            }

        # --------------------------------------------------
        # 5. Return retrieved context
        #
        # Gemini generation will be connected in the next
        # B2.8 step after retrieval is verified.
        # --------------------------------------------------

        return {
            "page_id": page_id,
            "query": query,
            "retrieved": retrieved_results,
            "context": context,
            "answer": None,
        }

    def index_text(
        self,
        *,
        page_id: int,
        text: str,
        manuscript_id: int | None = None,
        script: str | None = None,
        language: str | None = None,
        source: str = "manuscript",
    ) -> dict:
        """
        Convert manuscript text into an embedding and store it in Qdrant.
        """

        if not text or not text.strip():
            raise ValueError("text cannot be empty")

        embedding_result = self.embedding_service.process(
            page_id=page_id,
            input_data=text,
        )

        return self.qdrant_service.process(
            page_id=page_id,
            input_data={
                "embedding": embedding_result["embedding"],
                "manuscript_id": manuscript_id,
                "script": script,
                "language": language,
                "text": text,
                "source": source,
            },
        )