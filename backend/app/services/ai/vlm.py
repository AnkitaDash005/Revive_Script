import os
from pathlib import Path
from typing import Any, ClassVar

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from app.services.ai.base import AIService

load_dotenv()


class VLMService(AIService):
    """
    High-speed manuscript transcription verification and correction service
    powered by Gemini 3.6 Flash.
    """

    MODEL_NAME: str = "gemini-3.6-flash"
    _client: ClassVar[Any] = None

    @classmethod
    def _get_client(cls) -> genai.Client:
        """
        Lazy-load and cache the Google GenAI client singleton.
        """
        if cls._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is missing in .env")
            cls._client = genai.Client(api_key=api_key)
        return cls._client

    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:
        if not isinstance(input_data, dict):
            raise TypeError("VLM input_data must be a dictionary")

        image_path = input_data.get("image_path")
        ocr_text = input_data.get("ocr_text", "")
        script = input_data.get("script", "unknown")

        if not image_path:
            raise ValueError("image_path is required")

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        client = self._get_client()
        image = Image.open(image_path)
        prompt = self._build_prompt(ocr_text=ocr_text, script=script)

        response = client.models.generate_content(
            model=self.MODEL_NAME,
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=1024,  # Increased to prevent truncated output
                tools=[],               # Explicit empty list avoids AFC warning logs
            ),
        )

        analysis_output = response.text.strip() if response.text else ""

        return {
            "page_id": page_id,
            "model": self.MODEL_NAME,
            "script": script,
            "ocr_text": ocr_text,
            "analysis": analysis_output,
        }

    def _build_prompt(
        self,
        *,
        ocr_text: str,
        script: str,
    ) -> str:
        return f"""
You are an expert paleographer assisting with the digital preservation of historical manuscripts.

Target Script: {script}

Initial OCR Hypothesis:
--- OCR TEXT ---
{ocr_text if ocr_text else "[None provided]"}
--- END OCR TEXT ---

Instructions:
1. Examine the manuscript image and provide a precise transcription of all visible lines.
2. Correct OCR misreadings, dropped ligatures, and diacritics.
3. Transcribe only what is visually legible. Do not guess or extrapolate obscured sections.
4. Output directly in the format below without preliminary greetings, disclaimers, or conversational filler.

Format:
CORRECTED_TEXT:
<final line-by-line transcription>

CONFIDENCE:
<high / medium / low>

NOTES:
<1-2 concise observations regarding script, line breaks, or damage>
""".strip()