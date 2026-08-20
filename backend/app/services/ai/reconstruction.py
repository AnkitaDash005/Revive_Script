import os
import re
from typing import Any, ClassVar

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.services.ai.base import AIService

load_dotenv()


class ReconstructionService(AIService):
    """
    Reconstructs uncertain or damaged manuscript text using:
    - OCR output
    - VLM-corrected transcription
    - RAG-retrieved manuscript context
    """

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
    def _extract_reconstructed_text(raw_output: str) -> str:
        """Extracts text between RECONSTRUCTED_TEXT: and CONFIDENCE:"""
        if not raw_output:
            return ""

        match = re.search(
            r"RECONSTRUCTED_TEXT:\s*(.*?)(?=\n\s*(?:CONFIDENCE|UNCERTAIN_PORTIONS|NOTES):|$)",
            raw_output,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            clean = match.group(1).strip()
            if clean and clean != "<reconstructed manuscript text>":
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

        ocr_text = input_data.get("ocr_text", "")
        corrected_text = input_data.get("corrected_text", "")
        rag_context = input_data.get("rag_context", "")
        script = input_data.get("script", "Devanagari")

        prompt = self._build_prompt(
            ocr_text=ocr_text,
            corrected_text=corrected_text,
            rag_context=rag_context,
            script=script,
        )

        client = self._get_client()

        response = client.models.generate_content(
            model=self.MODEL_NAME,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=1024,
            ),
        )

        raw_output = response.text.strip() if response.text else ""
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
        return f"""
You are an expert historical manuscript reconstruction assistant.

Target script:
{script}

INITIAL OCR:
---
{ocr_text or "[None available]"}
---

VLM CORRECTED TRANSCRIPTION:
---
{corrected_text or "[None available]"}
---

RELEVANT MANUSCRIPT CONTEXT FROM RAG:
---
{rag_context or "[No relevant context found]"}
---

Your task is to reconstruct only text that can be reasonably
supported by the available evidence.

Rules:
1. Prefer the VLM transcription when it is visually supported.
2. Use RAG context only as supporting historical/manuscript context.
3. Do not invent missing words or characters.
4. Do not silently replace uncertain text.
5. Mark genuinely uncertain portions as [UNCERTAIN].
6. Preserve the original script.
7. Preserve meaningful line breaks where possible.
8. If reconstruction is impossible, keep the uncertain section.
9. Explain important reconstruction decisions briefly.

Return exactly:

RECONSTRUCTED_TEXT:
<reconstructed manuscript text>

CONFIDENCE:
<high / medium / low>

UNCERTAIN_PORTIONS:
<list uncertain portions, or "none">

NOTES:
<brief explanation>
""".strip()