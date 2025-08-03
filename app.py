from flask import Flask, request, jsonify
from document_loader import download_and_extract_text
from vectorizer import build_vector_index
from retriever import get_top_chunks
from gpt_client import get_gemini_response
import re
import os
from dotenv import load_dotenv

# 🔐 Load the expected API token from .env
load_dotenv()
EXPECTED_TOKEN = os.getenv("API_TOKEN")

GEMINI_API_KEY = "AIzaSyCihQiZOBvVGHfPCOiTZPCdoxMpV4xsXE0"
API_TOKEN = "b57b1e7070937a460f4a0a5f98586be5bc8190724e1d80d137fe428ae7dba7c0"


app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return """
    <html>
        <head><title>HackRX Document QA API</title></head>
        <body>
            <h1>🚀 Welcome to the HackRX Document QA API</h1>
            <p>Usage: Send a POST request to <code>/api/v1/hackrx/run</code> with Bearer Token and JSON body containing <code>'documents'</code> and <code>'questions'</code>.</p>
        </body>
    </html>
    """

@app.route("/api/v1/hackrx/run", methods=["POST"])
def hackrx_run():
    # 🔐 Token validation
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.split("Bearer ")[1].strip()
    if token != EXPECTED_TOKEN:
        return jsonify({"error": "Unauthorized  invalid token"}), 403

    # ✅ Parse and validate JSON payload
    data = request.get_json()
    if not data or "documents" not in data or "questions" not in data:
        return jsonify({"error": "Invalid request format. Required: 'documents' and 'questions'."}), 400

    doc_path = data["documents"]
    questions = data["questions"]

    print(f"📄 Processing document: {doc_path}")
    full_text = download_and_extract_text(doc_path)

    if not full_text:
        return jsonify({"error": "❌ Failed to extract text from document."}), 400

    index, chunks, model = build_vector_index(full_text)

    answers = []
    for q in questions:
        print(f"🧪 Q: {q}")
        top_chunks = get_top_chunks(q, index, chunks, model)
        raw_ans = get_gemini_response(q, top_chunks)

        # ✅ Clean output: remove ✅, ❌, ₹ and strip whitespace
        cleaned_ans = raw_ans.replace("✅", "").replace("❌", "").replace("₹", "").strip()
        answers.append(cleaned_ans)

        print(f"✅ A: {cleaned_ans}")

    return jsonify({"answers": answers})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
