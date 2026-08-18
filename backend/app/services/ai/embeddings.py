from typing import Any, ClassVar

from sentence_transformers import SentenceTransformer

from app.services.ai.base import AIService


class EmbeddingService(AIService):
    """
    Multilingual text embedding service for Revive_Script.

    Converts OCR/VLM text into dense vectors that can later
    be stored and searched using Qdrant.
    """

    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    _model: ClassVar[SentenceTransformer | None] = None

    @classmethod
    def _load_model(cls) -> SentenceTransformer:
        """
        Load the embedding model once and reuse it.
        """

        if cls._model is None:
            cls._model = SentenceTransformer(
                cls.MODEL_NAME
            )

        return cls._model

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:

        if not isinstance(input_data, str):
            raise TypeError(
                "Embedding input_data must be text"
            )

        text = input_data.strip()

        if not text:
            raise ValueError(
                "Cannot create embedding from empty text"
            )

        model = self._load_model()

        vector = model.encode(
            text,
            normalize_embeddings=True,
        )

        return {
            "page_id": page_id,
            "model": self.MODEL_NAME,
            "dimension": len(vector),
            "text": text,
            "embedding": vector.tolist(),
        }