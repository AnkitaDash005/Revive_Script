from app.services.ai.evaluation import EvaluationService


service = EvaluationService()

result = service.process(
    page_id=1,
    input_data={
        "predicted_text": (
            "यह एक पुराना हस्तलिखित ग्रंथ है"
        ),
        "reference_text": (
            "यह एक पुराना हस्तलिखित ग्रंथ है"
        ),
    },
)

print("=== EVALUATION ===")
print("Page:", result["page_id"])
print(
    "Character similarity:",
    result["character_similarity"],
)
print(
    "Word similarity:",
    result["word_similarity"],
)
print(
    "Confidence:",
    result["confidence"],
)