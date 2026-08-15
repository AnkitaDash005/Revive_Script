from typing import Any

from app.services.ai.base import AIService


class OCRService(AIService):

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:

        raise NotImplementedError(
            "OCR implementation belongs to B2"
        )