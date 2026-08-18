from typing import Any

from app.services.ai.base import AIService


class EvaluationService(AIService):
    """
    Evaluates manuscript AI output.

    This is intentionally simple for B2.10:
    - character-level similarity
    - word-level similarity
    - basic confidence classification

    Later this can be replaced with a more sophisticated
    historical/OCR evaluation pipeline.
    """

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:

        if not isinstance(input_data, dict):
            raise TypeError(
                "Evaluation input_data must be a dictionary"
            )

        predicted_text = input_data.get(
            "predicted_text",
            "",
        )

        reference_text = input_data.get(
            "reference_text",
            "",
        )

        if not predicted_text:
            raise ValueError(
                "predicted_text is required"
            )

        predicted = self._normalize(predicted_text)
        reference = self._normalize(reference_text)

        if not reference:
            return {
                "page_id": page_id,
                "evaluation_available": False,
                "predicted_text": predicted_text,
                "reference_text": "",
                "character_similarity": None,
                "word_similarity": None,
                "confidence": "unknown",
            }

        character_similarity = self._character_similarity(
            predicted,
            reference,
        )

        word_similarity = self._word_similarity(
            predicted,
            reference,
        )

        return {
            "page_id": page_id,
            "evaluation_available": True,
            "predicted_text": predicted_text,
            "reference_text": reference_text,
            "character_similarity": character_similarity,
            "word_similarity": word_similarity,
            "confidence": self._confidence(
                character_similarity,
                word_similarity,
            ),
        }

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(
            str(text).strip().split()
        )

    @staticmethod
    def _character_similarity(
        predicted: str,
        reference: str,
    ) -> float:

        if predicted == reference:
            return 1.0

        if not predicted or not reference:
            return 0.0

        max_length = max(
            len(predicted),
            len(reference),
        )

        distance = EvaluationService._levenshtein(
            predicted,
            reference,
        )

        return max(
            0.0,
            1.0 - (distance / max_length),
        )

    @staticmethod
    def _word_similarity(
        predicted: str,
        reference: str,
    ) -> float:

        predicted_words = predicted.split()
        reference_words = reference.split()

        if not reference_words:
            return 0.0

        predicted_set = set(predicted_words)
        reference_set = set(reference_words)

        overlap = predicted_set & reference_set

        return len(overlap) / len(reference_set)

    @staticmethod
    def _confidence(
        character_similarity: float,
        word_similarity: float,
    ) -> str:

        score = (
            character_similarity
            + word_similarity
        ) / 2

        if score >= 0.90:
            return "high"

        if score >= 0.70:
            return "medium"

        return "low"

    @staticmethod
    def _levenshtein(
        first: str,
        second: str,
    ) -> int:

        if first == second:
            return 0

        if not first:
            return len(second)

        if not second:
            return len(first)

        previous = list(range(len(second) + 1))

        for i, char_first in enumerate(
            first,
            start=1,
        ):
            current = [i]

            for j, char_second in enumerate(
                second,
                start=1,
            ):
                insertion = current[j - 1] + 1
                deletion = previous[j] + 1
                substitution = (
                    previous[j - 1]
                    + (char_first != char_second)
                )

                current.append(
                    min(
                        insertion,
                        deletion,
                        substitution,
                    )
                )

            previous = current

        return previous[-1]