from flask import Flask, request, jsonify
from document_loader import (
    download_and_extract_text,
    extract_text_and_urls_fallback
)
from vectorizer import build_vector_index
from retriever import get_top_chunks
from gpt_client import get_gemini_response
import os
from dotenv import load_dotenv
import sys

# 🔐 Load environment variables
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
    # ✅ Step 1: Token validation
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.split("Bearer ")[1].strip()
    if token != EXPECTED_TOKEN:
        return jsonify({"error": "Unauthorized invalid token"}), 403

    # ✅ Step 2: Extract payload
    data = request.get_json()
    if not data or "documents" not in data or "questions" not in data:
        return jsonify({"error": "Invalid request format. Required: 'documents' and 'questions'."}), 400

    doc_path = data["documents"]
    questions = data["questions"]
    print(f"📄 Processing document: {doc_path}")

    # ✅ Step 3: Download and Extract PDF to ./pdf directory
    try:
        print("📥 Using download_and_extract_text to handle PDF download and extraction...")
        table_text = download_and_extract_text(doc_path)

        # Construct the actual path to the saved file
        filename = os.path.basename(doc_path) if doc_path.startswith("http") else doc_path
        local_path = os.path.join("pdf", os.path.basename(filename))
        fallback_text = extract_text_and_urls_fallback(local_path)
    except Exception as e:
        return jsonify({"error": f"❌ Document parsing failed: {str(e)}"}), 500

    if not table_text and not fallback_text:
        return jsonify({"error": "❌ Failed to extract meaningful content from document."}), 400

    # ✅ Step 4: Build vector index
    index, chunks, model = build_vector_index(table_text, fallback_text)

    # ✅ Step 5: Answer questions
    answers = []
    for q in questions:
        print(f"\n🧪 Q: {q}")
        try:
            top_chunks = get_top_chunks(q, index, chunks, model, k=6)

            print("🔍 Top Chunks Used:")
            for i, ch in enumerate(top_chunks, start=1):
                print(f"\n--- Chunk #{i} ---\n{ch[:500]}\n")

            raw_ans = get_gemini_response(q, top_chunks)

            if "not specify" in raw_ans.lower() or not raw_ans.strip():
                print("⚠️ Fallback: trying full document context.")
                raw_ans = get_gemini_response(q, [table_text + "\n" + fallback_text])

            cleaned_ans = raw_ans.replace("✅", "").replace("❌", "").replace("₹", "").strip()

            if not cleaned_ans:
                cleaned_ans = "The document does not specify this."

            answers.append(cleaned_ans)
            print(f"✅ A: {cleaned_ans}")

        except Exception as err:
            print(f"❌ Error answering question: {err}")
            answers.append("The document does not specify this.")

    return jsonify({"answers": answers})

if __name__ == '__main__':
    log_file = open("log.txt", "a")  # Append mode
    sys.stdout = log_file
    sys.stderr = log_file

    # Start Flask app
    app.run(host="0.0.0.0", port=5000)
