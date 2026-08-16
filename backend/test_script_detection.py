from app.services.ai.script_detection import (
    ScriptDetectionService,
)


def main():
    detector = ScriptDetectionService()

    result = detector.detect_from_metadata(
        language="Odia",
        script="Odia",
    )

    print("=== B2.3 Script Detection ===")
    print()

    for key, value in result.items():
        print(f"{key}: {value}")

    odia_text = """
    ଓଡ଼ିଆ ଭାଷା ଭାରତର ଏକ ପ୍ରମୁଖ ଭାଷା।
    """

    text_result = detector.detect_from_text(
        odia_text
    )

    print()
    print("Text detection:")
    print()

    for key, value in text_result.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()