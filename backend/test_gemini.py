import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("\n--- Testing Active Model Generation ---")
for model_name in ["gemini-2.5-flash", "gemini-3.6-flash"]:
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'API Connected' in 2 words",
        )
        print(f" SUCCESS: {model_name} -> {response.text.strip()}")
        break
    except Exception as e:
        print(f" FAILED: {model_name} -> {e}")