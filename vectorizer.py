from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def build_vector_index(text):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    chunks = chunk_text(text)
    embeddings = model.encode(chunks)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))

    return index, chunks, model
