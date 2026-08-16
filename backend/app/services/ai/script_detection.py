from typing import Any, ClassVar


class ScriptDetectionService:
    """
    Determines the likely script/language for a manuscript.

    B2.3 initially uses trusted manuscript metadata.
    Image-based verification can be plugged in later.
    """

    # Add the ClassVar type annotation here
    SUPPORTED_SCRIPTS: ClassVar[dict[str, dict[str, str]]] = {
        "Odia": {
            "language": "Odia",
            "code": "ory",
        },
        "Devanagari": {
            "language": "Hindi",
            "code": "hin",
        },
        "Bengali": {
            "language": "Bengali",
            "code": "ben",
        },
        "Telugu": {
            "language": "Telugu",
            "code": "tel",
        },
        "Tamil": {
            "language": "Tamil",
            "code": "tam",
        },
        "Kannada": {
            "language": "Kannada",
            "code": "kan",
        },
        "Malayalam": {
            "language": "Malayalam",
            "code": "mal",
        },
        "Gujarati": {
            "language": "Gujarati",
            "code": "guj",
        },
        "Gurmukhi": {
            "language": "Punjabi",
            "code": "pan",
        },
    }

    def detect_from_metadata(
        self,
        *,
        language: str | None = None,
        script: str | None = None,
    ) -> dict[str, Any]:
        """
        Detect script using existing manuscript metadata.
        """

        if not script:
            return {
                "script": None,
                "language": language,
                "confidence": 0.0,
                "source": "metadata",
                "status": "unknown",
            }

        # Normalize simple variations.
        normalized_script = script.strip()

        for supported_script, information in self.SUPPORTED_SCRIPTS.items():
            if normalized_script.lower() == supported_script.lower():
                return {
                    "script": supported_script,
                    "language": (
                        language
                        or information["language"]
                    ),
                    "language_code": information["code"],
                    "confidence": 1.0,
                    "source": "manuscript_metadata",
                    "status": "detected",
                }

        return {
            "script": normalized_script,
            "language": language,
            "confidence": 0.5,
            "source": "manuscript_metadata",
            "status": "unsupported_or_unknown",
        }

    def detect_from_text(
        self,
        text: str,
    ) -> dict[str, Any]:
        """
        Basic Unicode-based script detection.

        This is useful after OCR produces text.
        It is NOT the primary image detector.
        """

        if not text or not text.strip():
            return {
                "script": None,
                "language": None,
                "confidence": 0.0,
                "source": "text",
                "status": "unknown",
            }

        script_ranges = {
            "Odia": (0x0B00, 0x0B7F),
            "Devanagari": (0x0900, 0x097F),
            "Bengali": (0x0980, 0x09FF),
            "Tamil": (0x0B80, 0x0BFF),
            "Telugu": (0x0C00, 0x0C7F),
            "Kannada": (0x0C80, 0x0CFF),
            "Malayalam": (0x0D00, 0x0D7F),
            "Gujarati": (0x0A80, 0x0AFF),
            "Gurmukhi": (0x0A00, 0x0A7F),
        }

        counts = {
            script: 0
            for script in script_ranges
        }

        total_script_characters = 0

        for character in text:
            codepoint = ord(character)

            for script, (
                start,
                end,
            ) in script_ranges.items():

                if start <= codepoint <= end:
                    counts[script] += 1
                    total_script_characters += 1
                    break

        if total_script_characters == 0:
            return {
                "script": None,
                "language": None,
                "confidence": 0.0,
                "source": "text",
                "status": "unknown",
            }

        detected_script = max(
            counts,
            key=counts.get,
        )

        confidence = (
            counts[detected_script]
            / total_script_characters
        )

        language = self.SUPPORTED_SCRIPTS[
            detected_script
        ]["language"]

        return {
            "script": detected_script,
            "language": language,
            "language_code": self.SUPPORTED_SCRIPTS[
                detected_script
            ]["code"],
            "confidence": round(
                confidence,
                4,
            ),
            "source": "unicode_text_analysis",
            "status": "detected",
        }