def get_top_chunks(query, index, chunks, model, k=15):
    """
    Retrieve the top-k most relevant chunks for a given query using vector similarity search.

    Args:
        query (str): The user's question.
        index (faiss.Index): The FAISS vector index.
        chunks (List[str]): The list of document chunks.
        model (SentenceTransformer): The sentence embedding model.
        k (int): Number of top chunks to retrieve (default = 10).

    Returns:
        List[str]: List of top-k most relevant text chunks.
    """
    query_vec = model.encode([query])
    D, I = index.search(query_vec, k)

    print(f"\n🔍 DEBUG: Top {k} Chunk Distances:\n", D[0])
    print(f"\n📦 DEBUG: Top {k} Retrieved Chunks:\n")
    for i in I[0]:
        if i < len(chunks):
            print("---\n", chunks[i][:500], "\n")  # Preview first 500 chars
        else:
            print(f"⚠️ Warning: Retrieved index {i} out of bounds.")

    return [chunks[i] for i in I[0] if i < len(chunks)]
