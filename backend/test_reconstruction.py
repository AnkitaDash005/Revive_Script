# from app.services.ai.reconstruction import ReconstructionService

# service = ReconstructionService()

# result = service.process(
#     page_id=1,
#     input_data={
#         "ocr_text": "यह एक पुराना हस्तलिखित...",
#         "corrected_text": "यह एक पुराना हस्तलिखित...",
#         "rag_context": (
#             "This manuscript contains historical Hindi text "
#             "from a traditional literary collection."
#         ),
#         "script": "Devanagari",
#     },
# )

# print("Model:", result["model"])
# print()
# print(result["reconstruction"])

from app.services.ai.reconstruction import ReconstructionService


service = ReconstructionService()

result = service.process(
    page_id=1,
    input_data={
        "ocr_text": "यह एक पुराना हस्तलिखित...",
        "corrected_text": "यह एक पुराना हस्तलिखित ग्रंथ है...",
        "rag_context": (
            "Historical Hindi manuscripts often contain "
            "literary and religious texts written in Devanagari."
        ),
        "script": "Devanagari",
    },
)

print("\n=== RECONSTRUCTION TEST ===")
print("Model:", result["model"])
print("Page ID:", result["page_id"])
print("\nOCR:")
print(result["ocr_text"])

print("\nCorrected:")
print(result["corrected_text"])

print("\nReconstruction:")
print(result["reconstruction"])