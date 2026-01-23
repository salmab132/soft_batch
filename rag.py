"""
RAG (Retrieval Augmented Generation) system for soft_batch.

Handles document chunking, embedding generation, storage, and retrieval.
"""
import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

from chunking import chunk_document, Chunk, ChunkingStrategy
from database import (
    save_document_chunk,
    get_document_chunks,
    save_notion_document,
    get_db,
    DEFAULT_DB_PATH
)


def _get_embedding_client() -> OpenAI:
    """Get OpenAI client configured for OpenRouter."""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )


def generate_embedding(text: str, model: str = "text-embedding-3-small") -> np.ndarray:
    """
    Generate an embedding vector for the given text.
    
    Args:
        text: Text to embed
        model: Embedding model to use (OpenAI compatible)
        
    Returns:
        Numpy array of embedding values
    """
    client = _get_embedding_client()
    
    # Clean up text
    text = text.replace("\n", " ").strip()
    if not text:
        raise ValueError("Cannot generate embedding for empty text")
    
    try:
        response = client.embeddings.create(
            input=[text],
            model=model
        )
        embedding = response.data[0].embedding
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        raise RuntimeError(f"Failed to generate embedding: {e}") from e


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def chunk_and_embed_document(
    text: str,
    source_id: str,
    source_type: str = "notion",
    strategy: ChunkingStrategy = "paragraphs",
    chunk_size: int = 500,
    db_path: str = DEFAULT_DB_PATH
) -> List[int]:
    """
    Chunk a document and generate embeddings for each chunk.
    
    Args:
        text: Document text to process
        source_id: Unique identifier for the source document
        source_type: Type of source ('notion', 'article', etc.)
        strategy: Chunking strategy to use
        chunk_size: Size parameter for chunking
        db_path: Database path
        
    Returns:
        List of chunk IDs that were saved to the database
    """
    # First, delete existing chunks for this document
    with get_db(db_path) as conn:
        conn.execute("""
            DELETE FROM document_chunks
            WHERE source_id = ? AND source_type = ?
        """, (source_id, source_type))
    
    # Chunk the document
    chunks = chunk_document(text, strategy=strategy, chunk_size=chunk_size)
    
    if not chunks:
        return []
    
    chunk_ids = []
    
    # Generate embeddings and save each chunk
    for chunk in chunks:
        try:
            # Generate embedding
            embedding_vector = generate_embedding(chunk.text)
            
            # Serialize embedding as bytes
            embedding_bytes = pickle.dumps(embedding_vector)
            
            # Serialize metadata as JSON
            metadata_json = json.dumps(chunk.metadata)
            
            # Save to database
            chunk_id = save_document_chunk(
                source_id=source_id,
                source_type=source_type,
                chunk_text=chunk.text,
                chunk_number=chunk.chunk_number,
                chunk_strategy=strategy,
                embedding=embedding_bytes,
                metadata=metadata_json,
                db_path=db_path
            )
            chunk_ids.append(chunk_id)
            
        except Exception as e:
            print(f"Warning: Failed to process chunk {chunk.chunk_number}: {e}")
            continue
    
    return chunk_ids


def retrieve_relevant_chunks(
    query: str,
    source_type: Optional[str] = None,
    top_k: int = 5,
    db_path: str = DEFAULT_DB_PATH
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant document chunks for a query.
    
    Args:
        query: Search query text
        source_type: Optional filter by source type
        top_k: Number of top results to return
        db_path: Database path
        
    Returns:
        List of chunks with similarity scores, sorted by relevance
    """
    # Generate embedding for the query
    query_embedding = generate_embedding(query)
    
    # Retrieve all chunks with embeddings
    with get_db(db_path) as conn:
        if source_type:
            rows = conn.execute("""
                SELECT id, source_id, source_type, chunk_text, chunk_number,
                       chunk_strategy, embedding, metadata
                FROM document_chunks
                WHERE source_type = ? AND embedding IS NOT NULL
            """, (source_type,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, source_id, source_type, chunk_text, chunk_number,
                       chunk_strategy, embedding, metadata
                FROM document_chunks
                WHERE embedding IS NOT NULL
            """).fetchall()
    
    if not rows:
        return []
    
    # Calculate similarity scores
    results = []
    for row in rows:
        try:
            # Deserialize embedding
            chunk_embedding = pickle.loads(row["embedding"])
            
            # Calculate similarity
            similarity = cosine_similarity(query_embedding, chunk_embedding)
            
            # Deserialize metadata
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
            
            results.append({
                "id": row["id"],
                "source_id": row["source_id"],
                "source_type": row["source_type"],
                "chunk_text": row["chunk_text"],
                "chunk_number": row["chunk_number"],
                "chunk_strategy": row["chunk_strategy"],
                "metadata": metadata,
                "similarity": float(similarity)
            })
        except Exception as e:
            print(f"Warning: Failed to process chunk {row['id']}: {e}")
            continue
    
    # Sort by similarity (highest first) and return top_k
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def build_rag_context(query: str, top_k: int = 3, db_path: str = DEFAULT_DB_PATH) -> str:
    """
    Build a context string from relevant document chunks for RAG.
    
    Args:
        query: Search query
        top_k: Number of chunks to retrieve
        db_path: Database path
        
    Returns:
        Formatted context string
    """
    chunks = retrieve_relevant_chunks(query, top_k=top_k, db_path=db_path)
    
    if not chunks:
        return ""
    
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Context {i}]")
        context_parts.append(chunk["chunk_text"])
        context_parts.append("")  # Empty line for separation
    
    return "\n".join(context_parts)


def sync_notion_document_to_rag(
    notion_page_id: str,
    content: str,
    title: str = "",
    chunking_strategy: ChunkingStrategy = "paragraphs",
    chunk_size: int = 500,
    db_path: str = DEFAULT_DB_PATH
) -> Tuple[int, List[int]]:
    """
    Sync a Notion document to the RAG system.
    
    Saves the document and creates embedded chunks.
    
    Args:
        notion_page_id: Notion page ID
        content: Document content
        title: Document title
        chunking_strategy: How to chunk the document
        chunk_size: Chunk size parameter
        db_path: Database path
        
    Returns:
        Tuple of (document_id, list of chunk_ids)
    """
    # Save the full document
    doc_id = save_notion_document(notion_page_id, title, content, db_path=db_path)
    
    # Chunk and embed
    chunk_ids = chunk_and_embed_document(
        text=content,
        source_id=notion_page_id,
        source_type="notion",
        strategy=chunking_strategy,
        chunk_size=chunk_size,
        db_path=db_path
    )
    
    return doc_id, chunk_ids


if __name__ == "__main__":
    """Test RAG functionality."""
    import sys
    
    # Sample test document
    test_doc = """
Soft Batch is a modern artisanal bakery focused on creating warm, cozy experiences through our baked goods.

Our Philosophy:
We believe in using only the finest ingredients. Every cookie, pastry, and bread is made fresh daily using traditional techniques combined with modern innovation.

Our Specialties:
- Chocolate chip cookies with a perfectly soft center
- Sourdough bread with a crispy crust
- Seasonal fruit tarts made with local ingredients
- Custom celebration cakes

Community Focus:
We're more than just a bakery. We're a gathering place for our neighborhood. Every Sunday, we host baking workshops where customers can learn our techniques.

Sustainability:
All our packaging is compostable. We source ingredients from local farms whenever possible and donate unsold items to local food banks.
""".strip()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Testing RAG system...\n")
        
        # Initialize database if needed
        from database import init_db
        if not os.path.exists(DEFAULT_DB_PATH):
            init_db()
        
        print("1. Syncing test document to RAG system...")
        doc_id, chunk_ids = sync_notion_document_to_rag(
            notion_page_id="test_page_123",
            content=test_doc,
            title="Soft Batch Brand Guide",
            chunking_strategy="paragraphs",
            chunk_size=300
        )
        print(f"   Saved document (ID: {doc_id}) with {len(chunk_ids)} chunks")
        
        print("\n2. Testing retrieval...")
        queries = [
            "What ingredients do you use?",
            "Tell me about your cookies",
            "What do you do for the community?"
        ]
        
        for query in queries:
            print(f"\n   Query: '{query}'")
            chunks = retrieve_relevant_chunks(query, source_type="notion", top_k=2)
            for i, chunk in enumerate(chunks, 1):
                print(f"   Result {i} (similarity: {chunk['similarity']:.3f}):")
                preview = chunk['chunk_text'][:100].replace('\n', ' ')
                print(f"   {preview}...")
        
        print("\n3. Building RAG context...")
        context = build_rag_context("What makes your bakery special?", top_k=2)
        print(context)
        
        print("\n✅ RAG system test complete!")
