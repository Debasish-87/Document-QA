from document_loader import download_and_extract_text
from vectorizer import build_vector_index
from retriever import get_top_chunks
from gpt_client import get_gemini_response
from submitter import submit_answers
import json
import os
from dotenv import load_dotenv

load_dotenv()

document_url = "BAJHLIP23020V012223.pdf"
questions = json.load(open("questions.json"))

# Step 1: Download and extract text
print("📄 Extracting document...")
doc_text = download_and_extract_text(document_url)

# Step 2: Vectorize
print("🔢 Embedding and indexing...")
index, chunks, model = build_vector_index(doc_text)

# Step 3: Ask questions
answers = []
for q in questions:
    top_chunks = get_top_chunks(q, index, chunks, model)
    ans = get_gemini_response(q, top_chunks)
    print(f"Q: {q}\nA: {ans}\n")
    answers.append(ans)

# Step 4: Submit
# print("📤 Submitting answers...")
# status, response = submit_answers(os.getenv("TEAM_TOKEN"), document_url, questions, answers)
# print(f"✅ Status: {status}\nResponse: {response}")
print("🚫 Skipping submission for now (testing mode).")


with open("answers_output.json", "w", encoding="utf-8") as f:
    json.dump({"questions": questions, "answers": answers}, f, indent=2, ensure_ascii=False)
print("📝 Answers saved to answers_output.json")
