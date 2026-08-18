import os
from pathlib import Path
from typing import Any, ClassVar

import cv2
import numpy as np
from app.services.ai.base import AIService


class OCRService(AIService):
    """
    OCR service for historical manuscript transcription.

    Optimized for low-latency CPU inference on Windows.
    """

    # Class-level singleton to prevent reloading models per request
    _engine: ClassVar[Any] = None

    @classmethod
    def _load_engine(cls):
        """
        Lazy-load and cache the PaddleOCR singleton engine.
        """
        if cls._engine is None:
            from paddleocr import PaddleOCR

            cls._engine = PaddleOCR(
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="devanagari_PP-OCRv5_mobile_rec",
                
                # Preprocessing pipeline handles document-level alignment
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,

                # Performance tuning
                enable_mkldnn=False,
                cpu_threads=min(4, os.cpu_count() or 4),
                
                # Constrain max detection image dimension to prevent slow processing
                text_det_limit_side_len=1280,
                text_det_limit_type="max",
            )

        return cls._engine

    def _prepare_image(self, image_path: Path, max_side: int = 2000) -> np.ndarray:
        """
        Read and optionally downsample oversized manuscript images.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not decode image at {image_path}")

        h, w = img.shape[:2]
        longest_side = max(h, w)

        if longest_side > max_side:
            scale = max_side / longest_side
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return img

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:

        if not isinstance(input_data, (str, Path)):
            raise TypeError("OCR input_data must be an image path")

        image_path = Path(input_data)
        if not image_path.exists():
            raise FileNotFoundError(f"OCR image not found: {image_path}")

        ocr = self._load_engine()
        img_array = self._prepare_image(image_path)

        # Run inference directly on preprocessed NumPy array
        result = ocr.predict(img_array)

        return {
            "page_id": page_id,
            "text": self._extract_text(result),
            "regions": self._extract_regions(result),
        }

    def _get_result_data(self, page) -> dict:
        data = getattr(page, "json", None)

        if callable(data):
            data = data()

        if not data:
            return {}

        if isinstance(data, dict):
            if "res" in data:
                data = data["res"]
            return data

        return {}

    def _extract_text(self, result) -> str:
        texts = []

        for page in result:
            data = self._get_result_data(page)
            if not data:
                continue

            rec_texts = data.get("rec_texts", [])
            if isinstance(rec_texts, list):
                texts.extend(str(t) for t in rec_texts if t)

        return "\n".join(texts)

    def _extract_regions(self, result) -> list[dict[str, Any]]:
        regions = []

        for page in result:
            data = self._get_result_data(page)
            if not data:
                continue

            texts = data.get("rec_texts", [])
            scores = data.get("rec_scores", [])
            boxes = data.get("rec_polys", [])

            for index, text in enumerate(texts):
                score = scores[index] if index < len(scores) else None
                box = boxes[index] if index < len(boxes) else None

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