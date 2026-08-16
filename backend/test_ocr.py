import os

os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["PADDLE_DISABLE_ONEDNN"] = "1"


from pathlib import Path

from app.services.ai.ocr import OCRService

IMAGE_PATH = (
    Path("storage")
    /"processed"
    /"page_1_enhanced.png"
)

def main():
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(
            f"Processed image not found: {IMAGE_PATH}"
        )
    service = OCRService()
    print("Starting OCR...")
    print(f"Image:{IMAGE_PATH}")
    print()

    result = service.process(
        page_id=1,
        input_data=IMAGE_PATH,
    )
    print("=== OCR RESULT ===")
    print()

    print("Page ID : ")
    print(result["page_id"])

    print()
    print("Recognized text : ")
    print("-----------------")
    print(result["text"])

    print()
    print(
        f"Regions detected : "
        f"{len(result['regions'])}"
    )

if __name__ == "__main__":
    main()
