import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# 1. Load .env file from the current or parent directory
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path if env_path.exists() else None)

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

IMAGE_PATH = (
    Path(__file__).resolve().parent
    / "storage"
    / "processed"
    / "page_1_enhanced.png"
)


def run_test():
    if not API_KEY:
        print("Error: GEMINI_API_KEY is not set in environment or .env file.")
        return

    if not IMAGE_PATH.exists():
        print(f"Error: Image not found at {IMAGE_PATH}")
        return

    print("Connecting to Gemini API...")
    client = genai.Client(api_key=API_KEY)

    img = Image.open(IMAGE_PATH)

    prompt = (
        "Transcribe the visible text in this manuscript image.\n"
        "Output format:\n"
        "CORRECTED_TEXT:\n<text>\n\n"
        "CONFIDENCE:\n<high/medium/low>\n\n"
        "NOTES:\n<brief notes>"
    )

    start_time = time.time()

    # Use a standard production model like 'gemini-2.5-flash'
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[img, prompt],
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=1024,
        ),
    )

    elapsed = time.time() - start_time
    print(f"\n--- Output (Finished in {elapsed:.2f}s) ---")
    print(response.text)


if __name__ == "__main__":
    run_test()