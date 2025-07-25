def get_top_chunks(query, index, chunks, model, k=3):
    query_vec = model.encode([query])
    _, I = index.search(query_vec, k)
    return [chunks[i] for i in I[0]]
