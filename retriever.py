def get_top_chunks(query, index, chunks, model, k=3):
    query_vec = model.encode([query])
    D, I = index.search(query_vec, k)

    print(f"\n🔍 DEBUG: Top {k} Chunk Distances:\n", D[0])
    print(f"\n📦 DEBUG: Top {k} Retrieved Chunks:\n")
    for i in I[0]:
        print("---\n", chunks[i][:500], "\n")

    return [chunks[i] for i in I[0]]
