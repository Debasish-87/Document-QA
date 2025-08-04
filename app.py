from flask import Flask, request, jsonify
from document_loader import extract_structured_table_with_fallback, extract_text_and_urls_fallback
from vectorizer import build_vector_index
from retriever import get_top_chunks
from gpt_client import get_gemini_response
import re
import os
import tempfile
import requests
from dotenv import load_dotenv

# 🔐 Load the expected API token from .env
load_dotenv()
EXPECTED_TOKEN = os.getenv("API_TOKEN")


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
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.split("Bearer ")[1].strip()
    if token != EXPECTED_TOKEN:
        return jsonify({"error": "Unauthorized  invalid token"}), 403

    data = request.get_json()
    if not data or "documents" not in data or "questions" not in data:
        return jsonify({"error": "Invalid request format. Required: 'documents' and 'questions'."}), 400

    doc_path = data["documents"]
    questions = data["questions"]

    print(f"📄 Processing document: {doc_path}")

    # 🔽 Download if URL
    if doc_path.startswith("http"):
        print("🌐 Detected URL. Downloading...")
        response = requests.get(doc_path)
        if response.status_code != 200:
            return jsonify({"error": "❌ Failed to download document."}), 400

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(response.content)
            local_path = tmp_file.name
        print(f"✅ Downloaded to temp file: {local_path}")
    else:
        print("📂 Detected local file path.")
        local_path = doc_path

    # Extract table and fallback text separately
    table_text = extract_structured_table_with_fallback(local_path)
    fallback_text = extract_text_and_urls_fallback(local_path)

    if not table_text and not fallback_text:
        return jsonify({"error": "❌ Failed to extract meaningful content from document."}), 400

    # Vector search setup
    index, chunks, model = build_vector_index(table_text, fallback_text)

    answers = []
    for q in questions:
        print(f"🧪 Q: {q}")
        top_chunks = get_top_chunks(q, index, chunks, model)
        raw_ans = get_gemini_response(q, top_chunks)

        cleaned_ans = raw_ans.replace("✅", "").replace("❌", "").replace("₹", "").strip()
        answers.append(cleaned_ans)
        print(f"✅ A: {cleaned_ans}")

    return jsonify({"answers": answers})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
