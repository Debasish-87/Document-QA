from flask import Flask, request, jsonify
from document_loader import extract_structured_table_with_fallback, extract_text_and_urls_fallback
from vectorizer import build_vector_index
from retriever import get_top_chunks
from gpt_client import get_gemini_response
import os
import tempfile
import requests
from dotenv import load_dotenv

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
            <p>Usage: Send a POST request to <code>/api/v1/hackrx/run</code> with Bearer Token and JSON body containing <code>'documents'</code> (array) and <code>'questions'</code>.</p>
            <p>Documents can be either URLs or local file paths.</p>
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

    # Handle both single document (backward compatible) and multiple documents
    doc_paths = data["documents"]
    if isinstance(doc_paths, str):
        doc_paths = [doc_paths]
    elif not isinstance(doc_paths, list):
        return jsonify({"error": "'documents' should be either a string or an array of strings"}), 400

    questions = data["questions"]
    print(f"📄 Processing {len(doc_paths)} documents")

    all_table_text = []
    all_fallback_text = []
    temp_files = []  # To keep track of temp files for cleanup

    for doc_path in doc_paths:
        try:
            # ✅ Step 3: Download PDF if URL
            if doc_path.startswith("http"):
                print(f"🌐 Downloading document from URL: {doc_path}")
                response = requests.get(doc_path)
                if response.status_code != 200:
                    print(f"❌ Failed to download document: {doc_path}")
                    continue
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                tmp_file.write(response.content)
                tmp_file.close()
                local_path = tmp_file.name
                temp_files.append(local_path)
                print(f"✅ Downloaded to temp file: {local_path}")
            else:
                print(f"📂 Using local file path: {doc_path}")
                local_path = doc_path

            # ✅ Step 4: Extract content from each document
            table_text = extract_structured_table_with_fallback(local_path)
            fallback_text = extract_text_and_urls_fallback(local_path)
            
            if table_text:
                all_table_text.append(f"--- Document: {doc_path} ---\n{table_text}")
            if fallback_text:
                all_fallback_text.append(f"--- Document: {doc_path} ---\n{fallback_text}")

        except Exception as e:
            print(f"❌ Error processing document {doc_path}: {str(e)}")
            continue

    # Clean up temporary files
    for temp_file in temp_files:
        try:
            os.unlink(temp_file)
        except:
            pass

    if not all_table_text and not all_fallback_text:
        return jsonify({"error": "❌ Failed to extract meaningful content from any document."}), 400

    # Combine all documents' content with clear separators
    combined_table_text = "\n\n".join(all_table_text)
    combined_fallback_text = "\n\n".join(all_fallback_text)

    # ✅ Step 5: Build vector index from all documents
    index, chunks, model = build_vector_index(combined_table_text, combined_fallback_text)

    answers = []
    for q in questions:
        print(f"\n🧪 Q: {q}")
        try:
            top_chunks = get_top_chunks(q, index, chunks, model, k=10)

            print("🔍 Top Chunks Used:")
            for i, ch in enumerate(top_chunks, start=1):
                print(f"\n--- Chunk #{i} ---\n{ch[:500]}\n")

            raw_ans = get_gemini_response(q, top_chunks)

            if "not specify" in raw_ans.lower() or not raw_ans.strip():
                print("⚠️ Fallback: trying full document context.")
                raw_ans = get_gemini_response(q, [combined_table_text + "\n" + combined_fallback_text])

            cleaned_ans = raw_ans.replace("✅", "").replace("❌", "").replace("₹", "").strip()

            if not cleaned_ans:
                cleaned_ans = "The document does not specify this."

            answers.append(cleaned_ans)
            print(f"✅ A: {cleaned_ans}")

        except Exception as err:
            print(f"❌ Error answering question: {err}")
            answers.append("The document does not specify this.")

    return jsonify({
        "answers": answers,
        "documents_processed": len(doc_paths),
        "documents_with_content": len(all_table_text) + len(all_fallback_text)
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)