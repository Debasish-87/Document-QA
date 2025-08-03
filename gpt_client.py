import os
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load .env file and configure Gemini
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

GEMINI_API_KEY = "AIzaSyCihQiZOBvVGHfPCOiTZPCdoxMpV4xsXE0"
API_TOKEN = "b57b1e7070937a460f4a0a5f98586be5bc8190724e1d80d137fe428ae7dba7c0"

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

Use ONLY the provided document excerpts to answer the question. Do not guess or assume. Extract the answer *verbatim* from the excerpts.

### Sum Insured: {sum_insured}

### Rules for Matching Table Entries:
- If the sum insured is **3L**, **4L**, or **5L** → match row labeled: **"3L/4L/5L"**
- If it's **10L**, **15L**, or **20L** → match: **"10L/15L/20L"**
- If it's **above 20L** → match: **">20L"**
- Do **not** match the wrong tier. Answer only if you find an exact tier.
- If a treatment name appears (e.g., cataract, cancer, robotic surgery), use the exact associated amount for the correct tier.
- If you can't find the answer, say: ❌ The document does not specify this.

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
