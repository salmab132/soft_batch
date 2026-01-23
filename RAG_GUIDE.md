# RAG System Guide

This guide covers the new **Retrieval Augmented Generation (RAG)** features added to soft_batch.

## Overview

The RAG system enhances post generation by:

1. **Chunking** documents into smaller, semantic pieces
2. **Embedding** chunks using OpenAI-compatible models
3. **Retrieving** relevant context based on queries
4. **Augmenting** LLM prompts with retrieved context

## Features

### 1. Document Chunking

Multiple chunking strategies are available via `chunking.py`:

#### Fixed Character Chunking
```python
from chunking import chunk_document

chunks = chunk_document(
    text=document,
    strategy="fixed_chars",
    chunk_size=500,
    overlap=50
)
```

- Splits text into fixed-size chunks (e.g., 500 characters)
- Supports overlap between chunks for context preservation
- Respects word boundaries when possible

#### Paragraph Chunking
```python
chunks = chunk_document(
    text=document,
    strategy="paragraphs",
    chunk_size=500
)
```

- Splits on paragraph boundaries (double newlines)
- Combines small paragraphs up to `chunk_size`
- Best for documents with clear paragraph structure

#### Sentence Chunking
```python
chunks = chunk_document(
    text=document,
    strategy="sentences",
    chunk_size=5  # Number of sentences per chunk
)
```

- Splits into groups of sentences
- `chunk_size` = number of sentences per chunk
- Handles various sentence endings (., !, ?)

#### Hybrid Chunking
```python
from chunking import chunk_document_hybrid

chunks = chunk_document_hybrid(
    text=document,
    target_chunk_size=500,
    max_chunk_size=1000
)
```

- Combines paragraph and sentence strategies
- Tries paragraph chunking first
- Falls back to sentence chunking for oversized paragraphs

### 2. RAG System

The `rag.py` module handles embeddings and retrieval:

#### Syncing Documents
```python
from rag import sync_notion_document_to_rag

doc_id, chunk_ids = sync_notion_document_to_rag(
    notion_page_id="abc123",
    content=document_text,
    title="Brand Guide",
    chunking_strategy="paragraphs",
    chunk_size=500
)
```

This:
1. Saves the document to the database
2. Chunks the document
3. Generates embeddings for each chunk
4. Stores everything for retrieval

#### Retrieving Relevant Chunks
```python
from rag import retrieve_relevant_chunks

chunks = retrieve_relevant_chunks(
    query="What are our bakery's values?",
    source_type="notion",  # Optional filter
    top_k=5
)

for chunk in chunks:
    print(f"Similarity: {chunk['similarity']:.3f}")
    print(f"Text: {chunk['chunk_text']}")
```

Returns chunks sorted by semantic similarity to the query.

#### Building Context for LLM
```python
from rag import build_rag_context

context = build_rag_context(
    query="Tell me about our cookies",
    top_k=3
)

# Use in LLM prompt
prompt = f"""
Context:
{context}

Task: Write a social media post about our cookies.
"""
```

### 3. Enhanced Post Generation

Posts can now use RAG for better context:

```python
from llm import generate_social_post

post = generate_social_post(
    brand_docs=full_brand_docs,
    use_rag=True,
    rag_query="What makes our bakery unique?"
)
```

The system will:
1. Retrieve the most relevant chunks based on the query
2. Add them to the prompt context
3. Generate a more focused, relevant post

### 4. Comment Reply Generation

Auto-generate replies to comments using RAG:

```python
from llm import generate_comment_reply

reply = generate_comment_reply(
    original_comment="Do you use organic flour?",
    brand_docs=brand_docs,
    use_rag=True
)
```

RAG retrieves relevant context from your docs to help answer accurately.

## Database Schema

New tables support the RAG system:

### `document_chunks`
Stores chunked documents with embeddings:
- `source_id` - Identifier for the source document
- `source_type` - Type (e.g., 'notion', 'article')
- `chunk_text` - The chunk content
- `chunk_number` - Order in document
- `chunk_strategy` - Chunking method used
- `embedding` - Binary embedding vector
- `metadata` - JSON metadata

### `notion_documents`
Tracks synced Notion pages:
- `notion_page_id` - Notion page ID
- `title` - Document title
- `content` - Full document text
- `last_synced_at` - Last sync timestamp

### `mastodon_interactions`
Tracks comments/mentions:
- `mastodon_id` - Toot ID
- `interaction_type` - 'mention', 'reply', or 'comment'
- `author_account` - Who posted it
- `content` - The comment text
- `responded` - Whether we've replied
- `response_post_id` - Our reply post ID

## CLI Commands

### Sync Notion to RAG
```bash
python main.py sync
```

Syncs your Notion page to the RAG system (one-time).

### Generate Post with RAG
```bash
python main.py
# When prompted: "Use RAG for context retrieval? (y/n)"
# Type: y
```

## Testing

Test the chunking module:
```bash
python chunking.py
```

Test the RAG system:
```bash
python rag.py test
```

## How It Works

1. **Chunking**: Documents are split using semantic boundaries (paragraphs, sentences) or fixed sizes
2. **Embedding**: Each chunk is converted to a vector using OpenAI embeddings
3. **Storage**: Vectors are stored as binary blobs in SQLite
4. **Retrieval**: 
   - Query is embedded
   - Cosine similarity computed against all chunks
   - Top-k most similar chunks returned
5. **Generation**: Retrieved chunks provide focused context to the LLM

## Configuration

No special configuration needed. The system uses:
- `OPENROUTER_API_KEY` - For embeddings and generation
- `NOTION_API_KEY` and `NOTION_PAGE_ID` - For Notion integration

## Best Practices

1. **Chunk Size**: 300-700 characters works well for most documents
2. **Top-k**: Retrieve 3-5 chunks for balanced context
3. **Strategy**: Use `paragraphs` for structured docs, `sentences` for less structured text
4. **Re-sync**: Re-sync Notion docs after significant changes

## Troubleshooting

**Issue**: "Failed to generate embedding"
- Check `OPENROUTER_API_KEY` is set
- Verify the model supports embeddings

**Issue**: No results from retrieval
- Check that documents have been synced: `python main.py sync`
- Verify chunks exist: Check database `document_chunks` table

**Issue**: Poor retrieval quality
- Try different chunk sizes
- Use more specific queries
- Increase `top_k` parameter
