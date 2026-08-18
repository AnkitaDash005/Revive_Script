import os
from typing import Any, ClassVar

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.services.ai.base import AIService


class QdrantService(AIService):
    """
    Qdrant vector database service for Revive Script.

    Stores manuscript embeddings together with searchable metadata.
    """

    COLLECTION_NAME: str = "revive_script_manuscripts"
    VECTOR_SIZE: int = 384

    _client: ClassVar[QdrantClient | None] = None

    @classmethod
    def _get_client(cls) -> QdrantClient:
        """
        Create the Qdrant client once and reuse it.
        """

        if cls._client is None:
            qdrant_url = os.getenv("QDRANT_URL")

            if qdrant_url:
                cls._client = QdrantClient(
                    url=qdrant_url,
                )
            else:
                # Local Qdrant mode
                cls._client = QdrantClient(
                    path="storage/qdrant"
                )

        return cls._client

    @classmethod
    def initialize_collection(cls) -> None:
        """
        Create the Qdrant collection if it doesn't already exist.
        """

        client = cls._get_client()

        collections = client.get_collections()

        exists = any(
            collection.name == cls.COLLECTION_NAME
            for collection in collections.collections
        )

        if exists:
            return

        client.create_collection(
            collection_name=cls.COLLECTION_NAME,
            vectors_config=VectorParams(
                size=cls.VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:
        """
        Store an embedding vector and manuscript metadata.
        """

        if not isinstance(input_data, dict):
            raise TypeError(
                "Qdrant input_data must be a dictionary"
            )

        embedding = input_data.get("embedding")

        if not embedding:
            raise ValueError(
                "embedding is required"
            )

        if len(embedding) != self.VECTOR_SIZE:
            raise ValueError(
                f"Expected {self.VECTOR_SIZE}-dimensional vector, "
                f"got {len(embedding)}"
            )

        self.initialize_collection()

        client = self._get_client()

        payload = {
            "page_id": page_id,
            "manuscript_id": input_data.get("manuscript_id"),
            "script": input_data.get("script"),
            "language": input_data.get("language"),
            "text": input_data.get("text"),
            "source": input_data.get("source", "unknown"),
        }

        point = PointStruct(
            id=page_id,
            vector=embedding,
            payload=payload,
        )

        client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[point],
        )

        return {
            "page_id": page_id,
            "collection": self.COLLECTION_NAME,
            "dimension": self.VECTOR_SIZE,
            "stored": True,
            "payload": payload,
        }

    def search(
        self,
        *,
        embedding: list[float],
        limit: int = 5,
    ) -> list[dict]:
        """
        Search for semantically similar manuscript pages.
        """

        if len(embedding) != self.VECTOR_SIZE:
            raise ValueError(
                f"Expected {self.VECTOR_SIZE}-dimensional vector"
            )

        self.initialize_collection()

        client = self._get_client()

        results = client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=embedding,
            limit=limit,
            with_payload=True,
        )

        return [
            {
                "id": point.id,
                "score": point.score,
                "payload": point.payload,
            }
            for point in results.points
        ]