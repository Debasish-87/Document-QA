import os
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load .env file and configure Gemini
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise EnvironmentError("Missing GEMINI_API_KEY in .env")

genai.configure(api_key=api_key)

# Use official model name explicitly
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

def get_gemini_response(question: str, context_chunks: list[str]) -> str:
    context = "\n---\n".join(context_chunks)
    
    sum_insured_match = re.search(r'(\d+(?:\.\d+)?)\s*[Ll]', question)
    sum_insured = f"{sum_insured_match.group(1)}L" if sum_insured_match else "unknown"

    prompt = f"""
You are a health insurance expert assistant.

Use ONLY the provided document excerpts to answer the question. Do not guess.

### Rules:
- The sum insured is: {sum_insured}
- Do not return multiple amounts like ₹1L/₹1.75L/₹2.5L.
- Only return the exact amount that corresponds to the sum insured (e.g., 10L → ₹1,75,000).
- If table is detected, match columns like:
  • 3L/4L/5L → for 3L
  • 10L/15L/20L → for 10L
  • >20L → for >20L
- If answer is not found, respond with: ❌ The document does not specify this.

### Format:
✅ Yes, [treatment] is covered, up to ₹[amount].
❌ The document does not specify this.

### Question:
{question}

### Document Excerpts:
{context}
"""

    print("🧾 DEBUG: Prompt Sent to Gemini (truncated):\n", prompt[:1200], "\n...\n")
    response = model.generate_content(prompt)
    return response.text.strip()

