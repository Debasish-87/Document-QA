from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import re

def chunk_text(text, chunk_size=1000, overlap=200):
    pattern = r"\n\s*\d+\.\d+(?:\.\d+)?\s+[^\n]+"
    matches = list(re.finditer(pattern, text))

    chunks = []
    if len(matches) >= 3:
        for i in range(len(matches)):
            start = matches[i].start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()
            if len(section_text) > 100:
                chunks.append(section_text)
    else:
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size].strip()
            if len(chunk) > 100:
                chunks.append(chunk)

    return chunks

def build_vector_index(table_text, fallback_text):
    print("🔧 Building vector index...")
    all_text = table_text + "\n" + fallback_text
    chunks = chunk_text(all_text)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(chunks, show_progress_bar=False)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))

    return index, chunks, model
