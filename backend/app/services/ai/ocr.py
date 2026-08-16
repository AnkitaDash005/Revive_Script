from pathlib import Path
from typing import Any

from app.services.ai.base import AIService


class OCRService(AIService):
    """
    OCR service.

    B2.4:
    - Loads a manuscript image
    - Runs OCR
    - Returns text, confidence and regions
    """

    def __init__(self):
        self._ocr = None

    def _load_engine(self):
        """
        Lazy-load PaddleOCR with the Devanagari recognition model.
        """

        if self._ocr is None:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="devanagari_PP-OCRv5_mobile_rec",

                # Our preprocessing pipeline already handles these.
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,

                # Windows CPU workaround.
                enable_mkldnn=False,
            )

        return self._ocr

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:

        if not isinstance(input_data, (str, Path)):
            raise TypeError(
                "OCR input_data must be an image path"
            )

        image_path = Path(input_data)

        if not image_path.exists():
            raise FileNotFoundError(
                f"OCR image not found: {image_path}"
            )

        ocr = self._load_engine()

        result = ocr.predict(
            str(image_path)
        )

        return {
            "page_id": page_id,
            "text": self._extract_text(result),
            "regions": self._extract_regions(result),
        }

    def _get_result_data(self, page) -> dict:
        """
        Extract the actual OCR dictionary from a PaddleOCR
        3.x Result object.

        PaddleOCR 3.x returns data under:
            {
                "res": {
                    "rec_texts": ...,
                    "rec_scores": ...,
                    "rec_polys": ...,
                    "rec_boxes": ...
                }
            }
        """

        data = getattr(
            page,
            "json",
            None,
        )

        if callable(data):
            data = data()

        if not data:
            return {}

        if isinstance(data, dict):
            # PaddleOCR 3.x result wrapper
            if "res" in data:
                data = data["res"]

            return data

        return {}

    def _extract_text(self, result) -> str:
        """
        Extract recognized text from PaddleOCR.
        """

        texts = []

        for page in result:

            data = self._get_result_data(page)

            if not data:
                continue

            rec_texts = data.get(
                "rec_texts",
                [],
            )

            if isinstance(rec_texts, list):
                texts.extend(
                    str(text)
                    for text in rec_texts
                    if text
                )

        return "\n".join(texts)

    def _extract_regions(self, result) -> list:
        """
        Extract OCR regions, confidence scores,
        and bounding boxes.
        """

        regions = []

        for page in result:

            data = self._get_result_data(page)

            if not data:
                continue

            texts = data.get(
                "rec_texts",
                [],
            )

            scores = data.get(
                "rec_scores",
                [],
            )

            boxes = data.get(
                "rec_polys",
                [],
            )

            for index, text in enumerate(texts):

                score = None

                if index < len(scores):
                    score = scores[index]

                box = None

                if index < len(boxes):
                    box = boxes[index]

                # Convert NumPy values into normal Python
                # values so the result can later be stored
                # as JSON/database data.
                if hasattr(box, "tolist"):
                    box = box.tolist()

                if hasattr(score, "item"):
                    score = score.item()

                regions.append(
                    {
                        "text": str(text),
                        "confidence": score,
                        "box": box,
                    }
                )

        return regions