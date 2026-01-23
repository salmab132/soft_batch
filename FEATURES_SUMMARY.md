# Soft Batch - New Features Summary

This document summarizes the new features added to enhance soft_batch with RAG (Retrieval Augmented Generation) and automated listeners.

## What's New

### 1. Advanced Document Chunking

**File**: `chunking.py`

Multiple strategies for splitting documents into semantic chunks:

- **Fixed Character Count** (e.g., 500 chars with overlap)
- **Paragraph Boundaries** (splits on double newlines)
- **Sentence Count** (e.g., 5 sentences per chunk)
- **Hybrid Strategy** (combines paragraph + sentence methods)

**Why**: Proper chunking enables effective RAG by creating meaningful, retrievable text segments.

**Usage**:
```python
from chunking import chunk_document

# Paragraph-based chunking
chunks = chunk_document(text, strategy="paragraphs", chunk_size=500)

# Fixed character chunking with overlap
chunks = chunk_document(text, strategy="fixed_chars", chunk_size=500, overlap=50)

# Sentence-based chunking
chunks = chunk_document(text, strategy="sentences", chunk_size=5)
```

### 2. RAG System

**File**: `rag.py`

Complete RAG implementation with:

- **Embedding Generation**: Converts text chunks to vector embeddings
- **Similarity Search**: Finds most relevant chunks using cosine similarity
- **Context Building**: Assembles context for LLM prompts
- **Notion Sync**: Automatic sync of Notion pages to RAG system

**Why**: RAG improves post generation by retrieving only relevant context instead of sending entire documents to the LLM.

**Usage**:
```python
from rag import sync_notion_document_to_rag, retrieve_relevant_chunks

# Sync a Notion page
doc_id, chunk_ids = sync_notion_document_to_rag(
    notion_page_id="abc123",
    content=document_text,
    title="Brand Guide"
)

# Retrieve relevant chunks
chunks = retrieve_relevant_chunks(
    query="What are our bakery values?",
    top_k=5
)
```

### 3. Enhanced Post Generation

**File**: `llm.py` (updated)

Post generation now supports RAG:

```python
from llm import generate_social_post

# Generate with RAG
post = generate_social_post(
    brand_docs=docs,
    use_rag=True,
    rag_query="What makes our bakery special?"
)
```

**New Function**: `generate_comment_reply()` for auto-replying to comments with RAG context.

### 4. Notion Listener

**File**: `notion_listener.py`

Automated monitoring of Notion pages:

- Polls Notion pages for changes
- Syncs updated content to RAG system
- Auto-generates social media posts from changes
- Saves posts as drafts for review

**Why**: Enables content workflow: Update Notion → Auto-generate posts

**Usage**:
```bash
# One-time sync
python notion_listener.py sync

# Start listener (checks every 5 minutes)
python notion_listener.py listen 300

# Via main.py
python main.py notion-listen --interval 300
```

### 5. Mastodon Listener

**File**: `mastodon_listener.py`

Automated comment/mention monitoring:

- Polls Mastodon for mentions and replies
- Stores interactions in database
- Auto-generates contextual replies using RAG
- Supports draft mode (default) or auto-reply mode

**Why**: Enables automated customer engagement without constant monitoring

**Usage**:
```bash
# Check for mentions once
python mastodon_listener.py check

# Start listener (draft mode)
python mastodon_listener.py listen 180

# Start listener (auto-reply mode)
python mastodon_listener.py listen-auto 180

# Via main.py
python main.py mastodon-listen --interval 180 [--auto-reply]
```

### 6. Enhanced Database Schema

**File**: `database.py` (updated)

New tables:

- **`document_chunks`**: Stores chunked text with embeddings
- **`notion_documents`**: Tracks synced Notion pages
- **`mastodon_interactions`**: Records mentions/replies and responses

New functions:
- `save_notion_document()`
- `save_document_chunk()`
- `save_mastodon_interaction()`
- `get_unresponded_interactions()`
- `mark_interaction_responded()`

### 7. Updated CLI

**File**: `main.py` (updated)

New commands:

```bash
# Sync Notion docs to RAG system
python main.py sync

# Start Notion listener
python main.py notion-listen --interval 300

# Start Mastodon listener
python main.py mastodon-listen --interval 180 [--auto-reply]

# Existing commands still work
python main.py baking
python main.py stats
python main.py  # Default: generate post (now with RAG option)
```

## Architecture Overview

```
┌─────────────────┐
│  Notion Pages   │
└────────┬────────┘
         │ (Notion Listener polls)
         ▼
┌─────────────────┐
│  RAG System     │
│  - Chunking     │
│  - Embeddings   │
│  - Retrieval    │
└────────┬────────┘
         │ (Provides context)
         ▼
┌─────────────────┐      ┌──────────────────┐
│  LLM Generation │ ───► │  Social Posts    │
│  - Posts        │      │  (Mastodon)      │
│  - Replies      │      └──────────────────┘
└─────────────────┘               │
         ▲                        │ (Comments)
         │                        ▼
         │              ┌──────────────────┐
         └──────────────│ Mastodon         │
                        │ Listener         │
                        └──────────────────┘
```

## Workflow Examples

### Content Publishing Workflow

1. Update brand guide in Notion
2. Notion Listener detects change
3. Syncs to RAG system (chunks + embeds)
4. Auto-generates draft post
5. Review and approve draft
6. Post to Mastodon

### Customer Engagement Workflow

1. Customer mentions @soft_batch on Mastodon
2. Mastodon Listener detects mention
3. Retrieves relevant brand context via RAG
4. Generates contextual reply
5. (Draft mode) Review reply → Approve → Post
6. (Auto mode) Posts immediately

## Dependencies Added

- **numpy**: For embedding vector operations

## Migration Notes

### Database Migration

The database schema has been updated with new tables. If you have an existing database:

```bash
# Backup your database first
cp soft_batch.db soft_batch.db.backup

# Run migration (creates new tables)
python db_migrate.py
```

Or delete the old database to recreate from scratch:
```bash
rm soft_batch.db
python main.py  # Will auto-initialize
```

### Environment Variables

No new environment variables required! Uses existing:
- `NOTION_API_KEY`, `NOTION_PAGE_ID`
- `MASTODON_ACCESS_TOKEN`, `MASTODON_BASE_URL`
- `OPENROUTER_API_KEY`

## Testing

Test each component:

```bash
# Test chunking
python chunking.py

# Test RAG system
python rag.py test

# Test Notion sync
python notion_listener.py sync

# Test Mastodon check
python mastodon_listener.py check
```

## Documentation

- **RAG_GUIDE.md**: Detailed RAG system documentation
- **LISTENERS_GUIDE.md**: Notion and Mastodon listener guides
- **DATABASE.md**: Database schema reference
- **QUICKSTART_DATABASE.md**: Database quick start

## Key Benefits

1. **Better Context**: RAG retrieves only relevant info instead of dumping entire docs
2. **Automation**: Listeners reduce manual work for posting and replies
3. **Consistency**: On-brand responses using your actual brand docs
4. **Scalability**: Handle more interactions without proportional time increase
5. **Flexibility**: Multiple chunking strategies for different content types
6. **Safety**: Draft mode by default for human review

## Next Steps

1. **Sync your Notion docs**: `python main.py sync`
2. **Test post generation with RAG**: `python main.py` → type 'y' for RAG
3. **Start Notion listener** (optional): `python main.py notion-listen`
4. **Start Mastodon listener** (optional): `python main.py mastodon-listen`
5. **Review drafts**: Check database for auto-generated content
6. **Iterate**: Adjust chunk sizes, intervals, and strategies based on results

## Support

- Check the guides: `RAG_GUIDE.md` and `LISTENERS_GUIDE.md`
- Run tests: `python chunking.py`, `python rag.py test`
- View stats: `python main.py stats`
- Check database: `python database.py stats`

---

**Version**: 2.0 (with RAG + Listeners)  
**Date**: 2026-01-23
