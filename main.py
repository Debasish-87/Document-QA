from document_loader import extract_structured_table_with_fallback, extract_text_from_pdf
from vectorizer import build_vector_index
from retriever import get_top_chunks
from gpt_client import get_gemini_response
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Input
document_path = "ICIHLIP22012V012223.pdf"  # Change if needed
questions = json.load(open("temp.json", encoding="utf-8"))

# ✅ Step 1: Extract text & tables
print("📄 Extracting document...")
table_text = extract_structured_table_with_fallback(document_path)
doc_text = extract_text_from_pdf(document_path)
# combined_text, table_text = download_and_extract_text(document_path)

# ✅ Step 2: Embed and index
print("🔢 Embedding and indexing...")
index, chunks, model = build_vector_index(doc_text + "\n\n" + table_text)

# ✅ Step 3: Ask Questions
answers = []
for question in questions:
    print(f"\n🧪 Processing Question: {question}")
    top_chunks = get_top_chunks(question, index, chunks, model)
    answer = get_gemini_response(question, top_chunks)
    print("✅", answer)
    answers.append(answer)

# ✅ Save locally (skip submission for now)
with open("answers_output.json", "w", encoding="utf-8") as f:
    json.dump({"questions": questions, "answers": answers}, f, indent=2, ensure_ascii=False)

print("📝 Answers saved to answers_output.json")
