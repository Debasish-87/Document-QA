from flask import Flask, request, jsonify
from document_loader import extract_structured_table_with_fallback, extract_text_and_urls_fallback
from vectorizer import build_vector_index
from retriever import get_top_chunks
from gpt_client import get_gemini_response
from urllib.parse import urlparse
import os
import requests
import time
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# 🔐 Load environment variables
load_dotenv()
EXPECTED_TOKEN = os.getenv("API_TOKEN")

# 📂 Ensure PDF storage folder exists
PDF_STORAGE_DIR = "pdfs"
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

# 📂 Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__)

# Set up logging
def setup_logging():
    # Create a file handler that writes to log.txt
    log_file = os.path.join(LOG_DIR, 'log.txt')
    
    # Rotating file handler with max size of 1MB and keeping 5 backup copies
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=1024*1024, 
        backupCount=5,
        encoding='utf-8'
    )
    
    # Set the logging level and format
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Get the root logger and add the file handler
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # Also log to console for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

setup_logging()

@app.route("/", methods=["GET"])
def home():
    app.logger.info("Home page accessed")
    return """
    <html>
        <head><title>HackRX Document QA API</title></head>
        <body>
            <h1>🚀 Welcome to the HackRX Document QA API</h1>
            <p>Usage: Send a POST request to <code>/api/v1/hackrx/run</code> with Bearer Token and JSON body containing <code>'documents'</code> (array) and <code>'questions'</code>.</p>
        </body>
    </html>
    """

@app.route("/api/v1/hackrx/run", methods=["POST"])
def hackrx_run():
    # ✅ Step 1: Token validation
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        app.logger.warning("Missing or invalid Authorization header")
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.split("Bearer ")[1].strip()
    if token != EXPECTED_TOKEN:
        app.logger.warning(f"Unauthorized access attempt with token: {token}")
        return jsonify({"error": "Unauthorized invalid token"}), 403

    # ✅ Step 2: Extract payload
    data = request.get_json()
    if not data or "documents" not in data or "questions" not in data:
        app.logger.warning("Invalid request format - missing documents or questions")
        return jsonify({"error": "Invalid request format. Required: 'documents' and 'questions'."}), 400

    doc_paths = data["documents"]
    if isinstance(doc_paths, str):
        doc_paths = [doc_paths]
    elif not isinstance(doc_paths, list):
        app.logger.warning("Invalid documents format - not a string or list")
        return jsonify({"error": "'documents' should be a string or a list of strings"}), 400

    questions = data["questions"]
    app.logger.info(f"Processing {len(doc_paths)} documents and {len(questions)} questions")

    all_table_text = []
    all_fallback_text = []

    for doc_path in doc_paths:
        try:
            # ✅ Step 3: Download or use local
            if doc_path.startswith("http"):
                app.logger.info(f"Downloading document: {doc_path}")
                response = requests.get(doc_path)
                if response.status_code != 200:
                    app.logger.error(f"Download failed for {doc_path} with status {response.status_code}")
                    continue

                filename = os.path.basename(urlparse(doc_path).path) or f"file_{int(time.time())}.pdf"
                safe_filename = f"{int(time.time())}_{filename}"
                local_path = os.path.join(PDF_STORAGE_DIR, safe_filename)

                with open(local_path, "wb") as f:
                    f.write(response.content)

                app.logger.info(f"Successfully saved document to: {local_path}")
            else:
                app.logger.info(f"Using local file path: {doc_path}")
                local_path = doc_path

            # ✅ Step 4: Extract content
            table_text = extract_structured_table_with_fallback(local_path)
            fallback_text = extract_text_and_urls_fallback(local_path)

            if table_text:
                all_table_text.append(f"--- Document: {doc_path} ---\n{table_text}")
            if fallback_text:
                all_fallback_text.append(f"--- Document: {doc_path} ---\n{fallback_text}")

        except Exception as e:
            app.logger.error(f"Error processing document {doc_path}: {str(e)}", exc_info=True)
            continue

    if not all_table_text and not all_fallback_text:
        app.logger.error("Failed to extract content from any document")
        return jsonify({"error": "❌ Failed to extract content from any document."}), 400

    combined_table_text = "\n\n".join(all_table_text)
    combined_fallback_text = "\n\n".join(all_fallback_text)

    # ✅ Step 5: Build vector index
    try:
        index, chunks, model = build_vector_index(combined_table_text, combined_fallback_text)
        app.logger.info("Successfully built vector index")
    except Exception as e:
        app.logger.error(f"Failed to build vector index: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to process documents"}), 500

    answers = []
    for q in questions:
        app.logger.info(f"Processing question: {q}")
        try:
            top_chunks = get_top_chunks(q, index, chunks, model, k=10)
            app.logger.debug(f"Retrieved {len(top_chunks)} top chunks for question")

            raw_ans = get_gemini_response(q, top_chunks)

            if "not specify" in raw_ans.lower() or not raw_ans.strip():
                app.logger.info("Falling back to full context for question")
                raw_ans = get_gemini_response(q, [combined_table_text + "\n" + combined_fallback_text])

            cleaned_ans = raw_ans.replace("✅", "").replace("❌", "").replace("₹", "").strip()
            if not cleaned_ans:
                cleaned_ans = "The document does not specify this."

            answers.append(cleaned_ans)
            app.logger.info(f"Answered question: {q}")

        except Exception as err:
            app.logger.error(f"Error answering question {q}: {str(err)}", exc_info=True)
            answers.append("The document does not specify this.")

    app.logger.info("Successfully processed all questions")
    return jsonify({
        "answers": answers,
        "documents_processed": len(doc_paths),
        "documents_with_content": len(all_table_text) + len(all_fallback_text)
    })

if __name__ == '__main__':
    app.logger.info("Starting HackRX Document QA API")
    app.run(host="0.0.0.0", port=8000)