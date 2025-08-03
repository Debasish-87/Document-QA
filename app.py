from flask import Flask, request, jsonify
from document_loader import download_and_extract_text
from vectorizer import build_vector_index
from retriever import get_top_chunks
from gpt_client import get_gemini_response
import re  # Added to clean Unicode characters

app = Flask(__name__)

# ✅ Root route for demo or health check
@app.route("/", methods=["GET"])
def home():
    return """
    <html>
        <head><title>HackRX Document QA API</title></head>
        <body>
            <h1>🚀 Welcome to the HackRX Document QA API</h1>
            <p>Usage: Send a POST request to <code>/api/v1/hackrx/run</code> with JSON body containing <code>'documents'</code> and <code>'questions'</code>.</p>
        </body>
    </html>
    """


@app.route("/api/v1/hackrx/run", methods=["POST"])
def hackrx_run():
    data = request.get_json()
    doc_path = data["documents"]
    questions = data["questions"]

    # ✅ Step 1: Extract
    print(f"📄 Processing document: {doc_path}")
    full_text = download_and_extract_text(doc_path)

    if not full_text:
        return jsonify({"error": "❌ Failed to extract text from document."}), 400

    # ✅ Step 2: Build vector index
    index, chunks, model = build_vector_index(full_text)

    # ✅ Step 3: Get answers
    answers = []
    for q in questions:
        print(f"🧪 Q: {q}")
        top_chunks = get_top_chunks(q, index, chunks, model)
        raw_ans = get_gemini_response(q, top_chunks)

        # ✅ Clean output: remove ✅, ❌, ₹ and any extra spaces
        cleaned_ans = raw_ans.replace("✅", "").replace("❌", "").replace("₹", "").strip()
        answers.append(cleaned_ans)

        print(f"✅ A: {cleaned_ans}")

    return jsonify({"answers": answers})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)

