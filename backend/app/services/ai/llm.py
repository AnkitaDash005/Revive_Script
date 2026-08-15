from typing import Any

from app.services.ai.base import AIService


class LLMService(AIService):

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:

        raise NotImplementedError(
            "LLM implementation belongs to B2"
        )