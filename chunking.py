"""
Document chunking utilities for RAG system.

Provides multiple chunking strategies:
- Fixed character count
- Paragraph boundaries
- Sentence count
"""
import re
from typing import List, Literal
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a chunk of text from a document."""
    text: str
    start_index: int
    end_index: int
    chunk_number: int
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


ChunkingStrategy = Literal["fixed_chars", "paragraphs", "sentences"]


def chunk_document(
    text: str,
    strategy: ChunkingStrategy = "paragraphs",
    chunk_size: int = 500,
    overlap: int = 50
) -> List[Chunk]:
    """
    Chunk a document using the specified strategy.
    
    Args:
        text: The document text to chunk
        strategy: Chunking strategy to use
            - "fixed_chars": Fixed character count with overlap
            - "paragraphs": Split by paragraph boundaries
            - "sentences": Split by sentence count
        chunk_size: For fixed_chars (characters) or sentences (sentence count)
        overlap: Number of characters to overlap between chunks (for fixed_chars)
    
    Returns:
        List of Chunk objects
    """
    if not text or not text.strip():
        return []
    
    if strategy == "fixed_chars":
        return _chunk_by_fixed_chars(text, chunk_size, overlap)
    elif strategy == "paragraphs":
        return _chunk_by_paragraphs(text, max_chars=chunk_size)
    elif strategy == "sentences":
        return _chunk_by_sentences(text, sentences_per_chunk=chunk_size)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")


def _chunk_by_fixed_chars(text: str, chunk_size: int, overlap: int) -> List[Chunk]:
    """
    Chunk text into fixed-size character chunks with overlap.
    
    Args:
        text: Text to chunk
        chunk_size: Number of characters per chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of Chunk objects
    """
    chunks = []
    text_length = len(text)
    start = 0
    chunk_number = 0
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        
        # If not the last chunk and we'd split in the middle of a word,
        # try to find a word boundary
        if end < text_length:
            # Look for whitespace within last 50 chars
            search_start = max(start, end - 50)
            last_space = text.rfind(' ', search_start, end)
            if last_space > start:
                end = last_space + 1
        
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                text=chunk_text,
                start_index=start,
                end_index=end,
                chunk_number=chunk_number,
                metadata={"strategy": "fixed_chars", "chunk_size": chunk_size}
            ))
            chunk_number += 1
        
        # Move start forward, accounting for overlap
        start = end - overlap if overlap > 0 else end
        
        # Prevent infinite loop if overlap >= chunk_size
        if start <= chunks[-1].start_index if chunks else False:
            start = end
    
    return chunks


def _chunk_by_paragraphs(text: str, max_chars: int = 1000) -> List[Chunk]:
    """
    Chunk text by paragraph boundaries.
    
    Splits on double newlines. Combines small paragraphs if they're under max_chars.
    
    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk (will combine paragraphs up to this limit)
        
    Returns:
        List of Chunk objects
    """
    # Split by double newlines (paragraph boundaries)
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    start_index = 0
    chunk_number = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        para_length = len(para)
        
        # If adding this paragraph would exceed max_chars, save current chunk
        if current_chunk and current_length + para_length + 1 > max_chars:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(Chunk(
                text=chunk_text,
                start_index=start_index,
                end_index=start_index + len(chunk_text),
                chunk_number=chunk_number,
                metadata={"strategy": "paragraphs", "paragraph_count": len(current_chunk)}
            ))
            chunk_number += 1
            
            # Start new chunk
            current_chunk = [para]
            current_length = para_length
            start_index = start_index + len(chunk_text) + 2  # +2 for \n\n
        else:
            current_chunk.append(para)
            current_length += para_length + 2  # +2 for separator
    
    # Add final chunk
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        chunks.append(Chunk(
            text=chunk_text,
            start_index=start_index,
            end_index=start_index + len(chunk_text),
            chunk_number=chunk_number,
            metadata={"strategy": "paragraphs", "paragraph_count": len(current_chunk)}
        ))
    
    return chunks


def _chunk_by_sentences(text: str, sentences_per_chunk: int = 5) -> List[Chunk]:
    """
    Chunk text by sentence count.
    
    Args:
        text: Text to chunk
        sentences_per_chunk: Number of sentences per chunk
        
    Returns:
        List of Chunk objects
    """
    # Split into sentences using regex
    # This handles periods, question marks, and exclamation points
    sentence_endings = re.compile(r'([.!?]+[\s\n]+)')
    
    parts = sentence_endings.split(text)
    
    # Reconstruct sentences by combining text and punctuation
    sentences = []
    for i in range(0, len(parts) - 1, 2):
        sentence = parts[i]
        if i + 1 < len(parts):
            sentence += parts[i + 1]
        sentence = sentence.strip()
        if sentence:
            sentences.append(sentence)
    
    # Handle last part if no ending punctuation
    if len(parts) % 2 == 1 and parts[-1].strip():
        sentences.append(parts[-1].strip())
    
    chunks = []
    chunk_number = 0
    start_index = 0
    
    for i in range(0, len(sentences), sentences_per_chunk):
        chunk_sentences = sentences[i:i + sentences_per_chunk]
        chunk_text = ' '.join(chunk_sentences)
        
        chunks.append(Chunk(
            text=chunk_text,
            start_index=start_index,
            end_index=start_index + len(chunk_text),
            chunk_number=chunk_number,
            metadata={
                "strategy": "sentences",
                "sentence_count": len(chunk_sentences)
            }
        ))
        chunk_number += 1
        start_index += len(chunk_text) + 1
    
    return chunks


def chunk_document_hybrid(
    text: str,
    target_chunk_size: int = 500,
    max_chunk_size: int = 1000,
    overlap: int = 50
) -> List[Chunk]:
    """
    Hybrid chunking strategy that respects semantic boundaries.
    
    Tries to chunk by paragraphs first, but falls back to sentence-based
    chunking if paragraphs are too large.
    
    Args:
        text: Text to chunk
        target_chunk_size: Target size in characters
        max_chunk_size: Maximum allowed chunk size
        overlap: Characters to overlap between chunks
        
    Returns:
        List of Chunk objects
    """
    # First try paragraph chunking
    para_chunks = _chunk_by_paragraphs(text, max_chars=target_chunk_size)
    
    # If any chunks are too large, re-chunk them by sentences
    final_chunks = []
    chunk_number = 0
    
    for chunk in para_chunks:
        if len(chunk.text) <= max_chunk_size:
            # Chunk is good as-is
            chunk.chunk_number = chunk_number
            final_chunks.append(chunk)
            chunk_number += 1
        else:
            # Chunk is too large, split by sentences
            sentence_chunks = _chunk_by_sentences(
                chunk.text,
                sentences_per_chunk=3
            )
            for sc in sentence_chunks:
                sc.chunk_number = chunk_number
                sc.metadata["strategy"] = "hybrid"
                final_chunks.append(sc)
                chunk_number += 1
    
    return final_chunks


if __name__ == "__main__":
    # Test the chunking functions
    sample_text = """
This is the first paragraph. It contains multiple sentences. Each sentence adds information.

This is the second paragraph. It's a bit shorter than the first one.

The third paragraph is here. It demonstrates paragraph-based chunking. We want to see how it handles multiple paragraphs.

Fourth paragraph! This one has an exclamation. It's exciting.

And finally, the fifth paragraph wraps things up. It's the conclusion of our test text.
""".strip()
    
    print("=" * 60)
    print("FIXED CHARACTER CHUNKING (200 chars, 50 overlap)")
    print("=" * 60)
    chunks = chunk_document(sample_text, strategy="fixed_chars", chunk_size=200, overlap=50)
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i} ({len(chunk.text)} chars):")
        print(chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text)
    
    print("\n" + "=" * 60)
    print("PARAGRAPH CHUNKING (300 chars max)")
    print("=" * 60)
    chunks = chunk_document(sample_text, strategy="paragraphs", chunk_size=300)
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i} ({len(chunk.text)} chars, {chunk.metadata.get('paragraph_count')} paragraphs):")
        print(chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text)
    
    print("\n" + "=" * 60)
    print("SENTENCE CHUNKING (3 sentences per chunk)")
    print("=" * 60)
    chunks = chunk_document(sample_text, strategy="sentences", chunk_size=3)
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i} ({chunk.metadata.get('sentence_count')} sentences):")
        print(chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text)
    
    print("\n" + "=" * 60)
    print("HYBRID CHUNKING (500 target, 1000 max)")
    print("=" * 60)
    chunks = chunk_document_hybrid(sample_text, target_chunk_size=500, max_chunk_size=1000)
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i} ({len(chunk.text)} chars, strategy: {chunk.metadata.get('strategy')}):")
        print(chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text)
