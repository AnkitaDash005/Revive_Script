from pathlib import Path

import cv2

from app.services.ai.preprocessing import (
    ImagePreprocessor,
)


IMAGE_PATH = (
    Path("storage")
    / "originals"
    / "manuscript_1_page_1_508e5df9405844898f9dff29c2c074d4.png"
)

OUTPUT_DIR = Path("storage") / "processed"


def main():
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(
            f"Input image not found: {IMAGE_PATH}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    processor = ImagePreprocessor()

    results = processor.process(
        str(IMAGE_PATH)
    )

    cv2.imwrite(
        str(OUTPUT_DIR / "page_1_resized.png"),
        results["original"],
    )

    cv2.imwrite(
        str(OUTPUT_DIR / "page_1_grayscale.png"),
        results["grayscale"],
    )

    cv2.imwrite(
        str(OUTPUT_DIR / "page_1_denoised.png"),
        results["denoised"],
    )

    cv2.imwrite(
        str(OUTPUT_DIR / "page_1_enhanced.png"),
        results["enhanced"],
    )

    cv2.imwrite(
        str(OUTPUT_DIR / "page_1_binary.png"),
        results["binary"],
    )

    print("B2.2 preprocessing completed.")
    print()
    print(f"Input : {IMAGE_PATH}")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()