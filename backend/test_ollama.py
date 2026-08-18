import time
from pathlib import Path
import ollama

IMAGE_PATH = Path(__file__).resolve().parent / "storage" / "processed" / "page_1_enhanced.png"

def run_test():
    if not IMAGE_PATH.exists():
        print(f"Error: Could not find image at {IMAGE_PATH}")
        return

    print(f"Found image: {IMAGE_PATH}")
    print("Sending image to Ollama (llava)...")

    start_time = time.time()

    response = ollama.chat(
        model="llava",  # <-- Uses your downloaded llava model
        messages=[
            {
                "role": "user",
                "content": (
                    "Transcribe any visible text in this manuscript image. "
                    "Format:\n"
                    "CORRECTED_TEXT:\n<transcription>\n\n"
                    "CONFIDENCE:\n<high/medium/low>\n\n"
                    "NOTES:\n<brief notes>"
                ),
                "images": [str(IMAGE_PATH)],
            }
        ],
        options={
            "temperature": 0.0,
            "num_predict": 180,
        },
    )

    elapsed_time = time.time() - start_time
    print(f"\n--- Output (Completed in {elapsed_time:.2f}s) ---")
    print(response["message"]["content"])

if __name__ == "__main__":
    run_test()