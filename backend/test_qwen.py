import sys
from pathlib import Path
from pprint import pprint

from app.services.ai.llm import LLMService

# Define absolute or relative project path to the image
IMAGE_PATH = Path("storage") / "processed" / "page_1_enhanced.png"

# Sample or real OCR text output from your previous pipeline step
SAMPLE_OCR_TEXT = """
(Paste real raw OCR text from your OCR step here, or leave empty if testing pure Vision-Language)
""".strip()


def main():
    if not IMAGE_PATH.exists():
        print(f"[-] Error: Image not found at {IMAGE_PATH.resolve()}", file=sys.stderr)
        return

    print("[+] Initializing LLM Service...")
    service = LLMService()

    print(f"[+] Processing page with {service.MODEL_NAME} on {service.device.upper()}...")
    
    try:
        result = service.process(
            page_id=1,
            input_data={
                "image_path": str(IMAGE_PATH.resolve()),
                "ocr_text": SAMPLE_OCR_TEXT,
                "script": "Odia",
            },
        )
    except Exception as e:
        print(f"[-] Inference failed: {e}", file=sys.stderr)
        return

    print("\n" + "=" * 30 + " QWEN RESULT " + "=" * 30)
    print(f"Page ID  : {result.get('page_id')}")
    print(f"Model    : {result.get('model')}")
    print(f"Script   : {result.get('script')}")
    print("-" * 73)
    print("Raw OCR Input:\n", result.get("ocr_text"))
    print("-" * 73)
    print("Qwen Analysis & Correction:\n", result.get("analysis"))
    print("=" * 73)


if __name__ == "__main__":
    main()