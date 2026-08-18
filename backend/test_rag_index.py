from app.services.ai.rag import RAGService

service = RAGService()

manuscript_text = """
यहाँ तुम्हारा वास्तविक OCR या Gemini द्वारा सुधारा गया
Devanagari manuscript text आएगा।
"""

result = service.index_text(
    page_id=1,
    manuscript_id=1,
    text=manuscript_text,
    script="Devanagari",
    language="Hindi",
    source="Gemini",
)

print(result)