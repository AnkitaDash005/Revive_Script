import os
import re
from pathlib import Path
from typing import Any, ClassVar
from PIL import Image

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.services.ai.base import AIService

load_dotenv()


class ReconstructionService(AIService):
    """
    Reconstructs uncertain or damaged manuscript text using:
    - Visual inspection of the original image
    - OCR / VLM output
    - RAG-retrieved manuscript context
    """

    # Using 2.0 Flash or Pro is recommended for multimodal reasoning
    MODEL_NAME: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    _client: ClassVar[Any] = None

    @classmethod
    def _get_client(cls) -> genai.Client:
        if cls._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is missing in .env")
            cls._client = genai.Client(api_key=api_key)
        return cls._client

    @staticmethod
    def _resolve_image_path(raw_path: str | Path) -> Path:
        p = Path(raw_path)
        if p.exists():
            return p

        clean_str = str(raw_path).lstrip("/\\")
        p_rel = Path(clean_str)
        if p_rel.exists():
            return p_rel

        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        p_base = base_dir / clean_str
        if p_base.exists():
            return p_base

        raise FileNotFoundError(f"Image file not found at: {raw_path}")

    @staticmethod
    def _extract_reconstructed_text(raw_output: str) -> str:
        if not raw_output:
            return ""

        match = re.search(
            r"RECONSTRUCTED_TEXT:\s*(.*?)(?=\n\s*(?:CONFIDENCE|UNCERTAIN_PORTIONS|NOTES):|$)",
            raw_output,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            clean = match.group(1).strip()
            if clean and clean != "<full reconstructed manuscript text>":
                return clean

        return raw_output.strip()

    @staticmethod
    def _extract_confidence(raw_output: str) -> str:
        match = re.search(
            r"CONFIDENCE:\s*(.*?)(?=\n\s*(?:UNCERTAIN_PORTIONS|NOTES):|$)",
            raw_output,
            re.DOTALL | re.IGNORECASE,
        )
        return match.group(1).strip() if match else "medium"

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:
        if not isinstance(input_data, dict):
            raise TypeError("Reconstruction input_data must be a dictionary")

        raw_image_path = input_data.get("image_path")
        ocr_text = input_data.get("ocr_text", "")
        corrected_text = input_data.get("corrected_text", "")
        rag_context = input_data.get("rag_context", "")
        script = input_data.get("script", "Devanagari")

        if not raw_image_path:
            raise ValueError("image_path is required for multimodal reconstruction")

        image_path = self._resolve_image_path(raw_image_path)
        client = self._get_client()

        prompt = self._build_prompt(
            ocr_text=ocr_text,
            corrected_text=corrected_text,
            rag_context=rag_context,
            script=script,
        )

        with Image.open(image_path) as image:
            response = client.models.generate_content(
                model=self.MODEL_NAME,
                contents=[image, prompt], # The AI can finally see!
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )

        raw_output = response.text.strip() if response and response.text else ""
        clean_text = self._extract_reconstructed_text(raw_output)
        confidence = self._extract_confidence(raw_output)

        return {
            "page_id": page_id,
            "model": self.MODEL_NAME,
            "script": script,
            "ocr_text": ocr_text,
            "corrected_text": corrected_text,
            "rag_context": rag_context,
            "reconstructed_text": clean_text or raw_output,
            "reconstruction": clean_text or raw_output,
            "raw_output": raw_output,
            "confidence": confidence,
        }

    def _build_prompt(
        self,
        *,
        ocr_text: str,
        corrected_text: str,
        rag_context: str,
        script: str,
    ) -> str:
        rag_section = f"{rag_context}" if rag_context else "No external RAG context provided. Use your internal knowledge of the Vedic corpus."

        return f"""
You are an expert historical manuscript reconstruction assistant and Sanskrit philologist.

Target script:
{script}

INITIAL OCR / VLM TEXT (May be truncated or inaccurate):
---
{corrected_text or ocr_text or "[None available]"}
---

RELEVANT CONTEXT:
---
{rag_section}
---

Your task is to visually inspect the manuscript image and RECONSTRUCT the damaged, cut-off, or stained portions.

Rules:
1. DO NOT blind-trust the provided OCR text. It is likely truncated. Look at the attached image and read it completely.
2. Identify broken sentences, grammatical gaps, and cut-off margins.
3. ACTIVELY INFILL missing characters under stains or tears based on visual outlines, meter, and known historical texts.
4. Enclose all reconstructed/restored words in brackets, e.g., `सम**[र्धयति ३]**`.
5. Maintain the original script, formatting, and line breaks.

Return exactly:

RECONSTRUCTED_TEXT:
[Left Margin]
<margin text>

[Main Text]
Line 1: <text>
Line 2: <text>
...

CONFIDENCE:
<high / medium / low>

UNCERTAIN_PORTIONS:
<list any portions that were absolutely impossible to deduce, or "none">

NOTES:
<briefly explain what specific words you reconstructed and why>
""".strip()