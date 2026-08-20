import logging
import os
import re
from pathlib import Path
from typing import Any, ClassVar

from app.services.ai.base import AIService
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

load_dotenv()
logger = logging.getLogger(__name__)


class VLMService(AIService):
    """
    High-speed manuscript transcription verification and correction service
    powered by Gemini Vision-Language Models.
    """

    MODEL_NAME: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
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
        """Resolves relative and absolute project paths safely."""
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
    def _extract_clean_text(raw_analysis: str) -> str:
        """Extracts just the transcribed text from CORRECTED_TEXT block."""
        if not raw_analysis:
            return ""

        match = re.search(
            r"CORRECTED_TEXT:\s*(.*?)(?=\n\s*(?:CONFIDENCE|NOTES):|$)",
            raw_analysis,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            clean = match.group(1).strip()
            if clean and clean != "<final line-by-line transcription>":
                return clean

        return raw_analysis.strip()

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:
        if not isinstance(input_data, dict):
            raise TypeError("VLM input_data must be a dictionary")

        raw_image_path = input_data.get("image_path")
        ocr_text = input_data.get("ocr_text", "")
        script = input_data.get("script", "Devanagari")

        if not raw_image_path:
            raise ValueError("image_path is required")

        image_path = self._resolve_image_path(raw_image_path)
        client = self._get_client()

        models_to_try = [
            self.MODEL_NAME,
            "gemini-3.6-flash",
        ]

        response = None
        used_model = self.MODEL_NAME

        with Image.open(image_path) as image:
            prompt = self._build_prompt(ocr_text=ocr_text, script=script)

            for model_candidate in dict.fromkeys(models_to_try):
                try:
                    response = client.models.generate_content(
                        model=model_candidate,
                        contents=[image, prompt],
                        config=types.GenerateContentConfig(
                            temperature=0.0,
                            max_output_tokens=1024,
                        ),
                    )
                    used_model = model_candidate
                    break
                except Exception as err:
                    logger.warning(f"Model {model_candidate} failed: {err}")
                    continue

        if response is None:
            logger.warning("Gemini VLM call failed. Falling back to OCR text.")
            return {
                "page_id": page_id,
                "model": "ocr-fallback",
                "script": script,
                "ocr_text": ocr_text,
                "analysis": ocr_text,
                "raw_output": ocr_text,
            }

        raw_output = response.text.strip() if response and response.text else ""
        clean_transcription = self._extract_clean_text(raw_output)

        return {
            "page_id": page_id,
            "model": used_model,
            "script": script,
            "ocr_text": ocr_text,
            "analysis": clean_transcription or raw_output,
            "raw_output": raw_output,
        }

    def _build_prompt(
        self,
        *,
        ocr_text: str,
        script: str,
    ) -> str:
        return f"""
You are an expert paleographer and Sanskrit manuscript epigraphist assisting with digital preservation and restoration.

Target Script: {script}

Initial OCR Hypothesis:
--- OCR TEXT ---
{ocr_text if ocr_text else "[None provided]"}
--- END OCR TEXT ---

Instructions:
1. Examine the manuscript image and provide a complete, line-by-line transcription of EVERY visible line from top to bottom. Do not stop at the first line.
2. Identify and separate margin text using the `[Left Margin]` tag. Put the main body under `[Main Text]`.
3. RECONSTRUCT missing, stained, or torn regions. Do not skip them. Use your knowledge of Vedic Sanskrit, grammar, and context to fill in the blanks.
4. Enclose any reconstructed or inferred text inside bold brackets, like this: `सम**[र्धयति ३]**`.
5. Output directly in the format below without preliminary greetings or conversational filler.

Format:
CORRECTED_TEXT:
[Left Margin]
<margin text>

[Main Text]
Line 1: <text>
Line 2: <text>
...

CONFIDENCE:
<high / medium / low>

NOTES:
<Briefly explain what words you reconstructed and why>
""".strip()

    def generate_from_context(
        self,
        *,
        query: str,
        context: str,
    ) -> str:
        client = self._get_client()

        prompt = f"""
You are an assistant for historical manuscript research.

Answer the user's question using ONLY the retrieved manuscript context below.
Do not invent facts. Do not use outside knowledge.

USER QUERY:
{query}

RETRIEVED MANUSCRIPT CONTEXT:
--- BEGIN CONTEXT ---
{context}
--- END CONTEXT ---

Provide a concise research-oriented answer.
""".strip()

        models_to_try = [
            self.MODEL_NAME,
            "gemini-3.6-flash",
        ]

        for model_candidate in dict.fromkeys(models_to_try):
            try:
                response = client.models.generate_content(
                    model=model_candidate,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=2048,
                    ),
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as err:
                logger.warning(f"Context generation model {model_candidate} failed: {err}")
                continue

        return ""