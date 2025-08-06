from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import re
from typing import List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into meaningful chunks with improved handling of document structure.
    
    Args:
        text: Input text to be chunked
        chunk_size: Maximum size of each chunk
        overlap: Overlap between consecutive chunks
        
    Returns:
        List of text chunks
    """
    # First try to split by sections (for structured documents)
    section_pattern = r"\n\s*\d+\.\d+(?:\.\d+)?\s+[^\n]+"  # Pattern for section headers
    matches = list(re.finditer(section_pattern, text))
    
    chunks = []
    if len(matches) >= 3:  # Only use section-based chunking if we find enough sections
        for i in range(len(matches)):
            start = matches[i].start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()
            if len(section_text) > 100:
                chunks.append(section_text)
        logger.info(f"Created {len(chunks)} chunks using section-based chunking")
    else:
        # Fallback to sliding window chunking
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size].strip()
            if len(chunk) > 100:
                # Try to split at sentence boundaries within the chunk
                sentences = re.split(r'(?<=[.!?])\s+', chunk)
                if len(sentences) > 1:
                    current_chunk = ""
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) <= chunk_size:
                            current_chunk += sentence + " "
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence + " "
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                else:
                    chunks.append(chunk)
        logger.info(f"Created {len(chunks)} chunks using sliding window approach")
    
    return chunks

def build_vector_index(table_text: Optional[str], fallback_text: Optional[str]) -> Tuple[faiss.Index, List[str], SentenceTransformer]:
    """
    Build a FAISS vector index from combined table and text content.
    
    Args:
        table_text: Extracted structured table text
        fallback_text: Fallback extracted text
        
    Returns:
        Tuple containing:
        - FAISS index
        - List of text chunks
        - SentenceTransformer model
    """
    logger.info("🔧 Building vector index...")
    
    # Handle None inputs
    table_text = table_text or ""
    fallback_text = fallback_text or ""
    
    all_text = table_text + "\n" + fallback_text
    
    if not all_text.strip():
        raise ValueError("No text content provided for indexing")
    
    chunks = chunk_text(all_text)
    
    if not chunks:
        raise ValueError("No valid chunks created from input text")
    
    logger.info(f"Processing {len(chunks)} text chunks")
    
    # Initialize model with more robust settings
    model = SentenceTransformer(
        "all-MiniLM-L6-v2",
        device="cpu",
        cache_folder="./model_cache"
    )
    
    # Encode chunks with progress indication
    logger.info("Encoding text chunks...")
    embeddings = model.encode(
        chunks,
        show_progress_bar=True,
        batch_size=32,
        convert_to_numpy=True
    )
    
    # Normalize embeddings for better similarity search
    faiss.normalize_L2(embeddings)
    
    # Build index with improved configuration
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Using Inner Product for normalized vectors
    index.add(np.array(embeddings).astype("float32"))
    
    logger.info(f"Built index with {index.ntotal} vectors")
    
    return index, chunks, model