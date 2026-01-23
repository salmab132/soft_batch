# Soft Batch - Enhanced with RAG & Automation

A social media automation tool for bakeries, now enhanced with **RAG (Retrieval Augmented Generation)** and **automated listeners** for Notion and Mastodon.

## 🎉 What's New (Version 2.0)

### Core Enhancements

1. **📚 Document Chunking System** - Multiple strategies for splitting documents
2. **🧠 RAG System** - Embeddings-based retrieval for better context
3. **🔔 Notion Listener** - Auto-generate posts when Notion content changes
4. **💬 Mastodon Listener** - Auto-reply to comments and mentions
5. **💾 Enhanced Database** - New tables for chunks, embeddings, and interactions

## Quick Start

### Installation

```bash
# Clone/navigate to project
cd soft_batch

# Install dependencies (includes new numpy dependency)
pip install -r requirements.txt

# Set up environment variables (same as before)
cp .env.example .env
# Edit .env with your API keys
```

### First-Time Setup

```bash
# Initialize database (creates new tables automatically)
python main.py

# Sync your Notion docs to RAG system
python main.py sync
```

## Usage

### Generate Posts (Enhanced with RAG)

```bash
# Interactive mode (will ask if you want to use RAG)
python main.py

# Output:
# Use RAG for context retrieval? (y/n, default=n): y
# 📄 Fetching brand docs from Notion...
# 🤖 Generating draft post...
#    (Using RAG for context retrieval)
```

### Automated Notion Listener

Monitor Notion pages and auto-generate posts when content changes:

```bash
# Start listener (checks every 5 minutes)
python main.py notion-listen --interval 300

# What it does:
# 1. Polls your Notion page for changes
# 2. Syncs updated content to RAG system
# 3. Auto-generates draft posts
# 4. Saves to database for review
```

**Use Case**: Update your brand guide in Notion → Get a draft post automatically!

### Automated Mastodon Listener

Monitor mentions and auto-generate replies:

```bash
# Start listener in DRAFT mode (safer, default)
python main.py mastodon-listen --interval 180

# Start listener in AUTO-REPLY mode (posts automatically)
python main.py mastodon-listen --interval 180 --auto-reply

# What it does:
# 1. Checks for new mentions/comments
# 2. Uses RAG to find relevant brand context
# 3. Generates contextual reply
# 4. Posts or saves as draft (based on mode)
```

**Use Case**: Customer asks "Do you use organic flour?" → System retrieves ingredient info from your docs → Auto-generates accurate reply

### Existing Features (Still Work!)

```bash
# Fetch baking articles and generate comments
python main.py baking --articles 5 --comments 2

# View statistics
python main.py stats
```

## New Modules

### 1. Chunking (`chunking.py`)

Split documents using different strategies:

```python
from chunking import chunk_document

# By paragraphs (recommended for structured docs)
chunks = chunk_document(text, strategy="paragraphs", chunk_size=500)

# By fixed characters (with overlap)
chunks = chunk_document(text, strategy="fixed_chars", chunk_size=500, overlap=50)

# By sentences
chunks = chunk_document(text, strategy="sentences", chunk_size=5)
```

**Test it**:
```bash
python chunking.py
```

### 2. RAG System (`rag.py`)

Embeddings-based retrieval:

```python
from rag import sync_notion_document_to_rag, retrieve_relevant_chunks

# Sync document
doc_id, chunk_ids = sync_notion_document_to_rag(
    notion_page_id="abc123",
    content=document_text,
    title="Brand Guide"
)

# Retrieve relevant chunks
chunks = retrieve_relevant_chunks(
    query="What are our values?",
    top_k=5
)
```

**Test it**:
```bash
python rag.py test
```

### 3. Notion Listener (`notion_listener.py`)

Automated Notion monitoring:

```bash
# One-time sync
python notion_listener.py sync

# Generate post from current content
python notion_listener.py generate

# Start continuous listener
python notion_listener.py listen 300
```

### 4. Mastodon Listener (`mastodon_listener.py`)

Automated comment monitoring:

```bash
# Check for mentions once
python mastodon_listener.py check

# Start listener (draft mode)
python mastodon_listener.py listen 180

# Start listener (auto-reply mode) 
python mastodon_listener.py listen-auto 180
```

## How RAG Works

Traditional approach (sends entire doc to LLM):
```
Notion Doc (5000 chars) → LLM → Post
```

With RAG (sends only relevant parts):
```
Notion Doc → Chunks → Embeddings → Storage
                                       ↓
Query → Embedding → Similarity Search → Top 3 relevant chunks → LLM → Post
```

**Benefits**:
- ✅ More focused, relevant posts
- ✅ Better context for replies
- ✅ Works with larger documents
- ✅ Lower token costs

## Database Schema Updates

Three new tables:

### `document_chunks`
Stores chunked text with embeddings:
```sql
CREATE TABLE document_chunks (
    id INTEGER PRIMARY KEY,
    source_id TEXT,           -- e.g., notion_page_id
    source_type TEXT,         -- 'notion', 'article', etc.
    chunk_text TEXT,
    chunk_number INTEGER,
    chunk_strategy TEXT,      -- 'paragraphs', 'sentences', etc.
    embedding BLOB,           -- Vector embedding
    metadata TEXT,            -- JSON metadata
    created_at TEXT,
    updated_at TEXT
);
```

### `notion_documents`
Tracks synced Notion pages:
```sql
CREATE TABLE notion_documents (
    id INTEGER PRIMARY KEY,
    notion_page_id TEXT UNIQUE,
    title TEXT,
    content TEXT,
    last_synced_at TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

### `mastodon_interactions`
Records mentions and replies:
```sql
CREATE TABLE mastodon_interactions (
    id INTEGER PRIMARY KEY,
    mastodon_id TEXT UNIQUE,
    interaction_type TEXT,    -- 'mention', 'reply', 'comment'
    author_account TEXT,
    content TEXT,
    in_reply_to_id TEXT,
    our_post_id INTEGER,
    responded BOOLEAN,
    response_post_id INTEGER,
    created_at TEXT,
    processed_at TEXT
);
```

## Migration

If you have an existing database:

```bash
# Backup first
python db_migrate.py backup

# Initialize (creates new tables)
python db_migrate.py init

# Or just run main.py (auto-migrates)
python main.py
```

The schema is designed to be additive - existing tables remain unchanged.

## Configuration

No new environment variables needed! Uses existing:

```bash
# Notion
NOTION_API_KEY=secret_xxx
NOTION_PAGE_ID=abc123

# Mastodon
MASTODON_ACCESS_TOKEN=xxx
MASTODON_BASE_URL=https://mastodon.social

# OpenRouter (now also used for embeddings)
OPENROUTER_API_KEY=sk-xxx
```

## Production Deployment

### Option 1: Manual (Development)

Run listeners in separate terminal windows:

**Terminal 1** (Notion):
```bash
python main.py notion-listen --interval 300
```

**Terminal 2** (Mastodon):
```bash
python main.py mastodon-listen --interval 180
```

### Option 2: Systemd (Linux Production)

Create service files in `/etc/systemd/system/`:

**soft-batch-notion.service**:
```ini
[Unit]
Description=Soft Batch Notion Listener
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/soft_batch
EnvironmentFile=/path/to/.env
ExecStart=/usr/bin/python3 main.py notion-listen --interval 300
Restart=always

[Install]
WantedBy=multi-user.target
```

**soft-batch-mastodon.service**:
```ini
[Unit]
Description=Soft Batch Mastodon Listener
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/soft_batch
EnvironmentFile=/path/to/.env
ExecStart=/usr/bin/python3 main.py mastodon-listen --interval 180
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable soft-batch-notion soft-batch-mastodon
sudo systemctl start soft-batch-notion soft-batch-mastodon
```

### Option 3: PM2 (Cross-platform)

```bash
# Install pm2
npm install -g pm2

# Start listeners
pm2 start "python main.py notion-listen --interval 300" --name soft-batch-notion
pm2 start "python main.py mastodon-listen --interval 180" --name soft-batch-mastodon

# Save and auto-start on boot
pm2 save
pm2 startup
```

## Safety Features

### Draft Mode by Default
- Notion listener saves posts as **drafts**
- Mastodon listener saves replies as **drafts** (unless `--auto-reply` is used)
- Human review required before posting

### Deduplication
- Won't process same Notion change twice
- Won't respond to same Mastodon mention twice

### Error Recovery
- Listeners continue running even if individual operations fail
- Errors logged but don't crash the system

## Testing

Test each component:

```bash
# Test chunking strategies
python chunking.py

# Test RAG system
python rag.py test

# Sync Notion (one-time)
python notion_listener.py sync

# Check Mastodon mentions
python mastodon_listener.py check

# View database stats
python main.py stats
```

## Monitoring

### View Activity

```bash
# Database statistics
python main.py stats

# Detailed database info
python db_migrate.py stats

# View tables
python db_migrate.py tables

# Interactive SQL
python db_migrate.py query
```

### Check Logs

When running listeners, watch the console output:

```
[Notion] Poll #1 at 2026-01-23T10:00:00Z
[Notion] Syncing page 'Brand Guide'...
[Notion] ✓ Synced 8 chunks
[Notion] Generating post from 'Brand Guide'...
[Notion] ✓ Generated draft post (ID: 42)
```

## Troubleshooting

### RAG System

**Q**: "No chunks retrieved"  
**A**: Run `python main.py sync` to sync your Notion docs first

**Q**: "Embedding generation failed"  
**A**: Check `OPENROUTER_API_KEY` is set correctly

### Notion Listener

**Q**: "Failed to sync page"  
**A**: Verify Notion page is shared with your integration

**Q**: "No posts generated"  
**A**: Check that page content has actually changed

### Mastodon Listener

**Q**: "No notifications found"  
**A**: Normal if you haven't been mentioned recently

**Q**: "Reply generation failed"  
**A**: Check `OPENROUTER_API_KEY` and brand docs availability

## Documentation

Detailed guides:

- **FEATURES_SUMMARY.md** - Overview of all new features
- **RAG_GUIDE.md** - Deep dive on RAG system
- **LISTENERS_GUIDE.md** - Detailed listener documentation
- **DATABASE.md** - Complete schema reference

## Examples

### Example: Content Workflow

1. Write new seasonal content in Notion
2. Notion listener detects change (within 5 minutes)
3. Content is chunked and embedded
4. Draft post generated highlighting new seasonal offerings
5. Review draft in database
6. Approve and post to Mastodon

### Example: Customer Engagement

1. Customer tweets: "@soft_batch Do you have gluten-free options?"
2. Mastodon listener detects mention (within 3 minutes)
3. RAG retrieves relevant chunks about gluten-free offerings
4. Reply generated: "@customer Yes! We offer gluten-free sourdough and cookies..."
5. (Draft mode) Review reply → Approve → Post
6. (Auto mode) Reply posted immediately

## Performance

- **Chunking**: Nearly instant
- **Embedding**: ~1-2 seconds per chunk
- **Retrieval**: ~0.5 seconds for 1000 chunks
- **Notion sync**: ~5-10 seconds for typical page
- **Reply generation**: ~2-5 seconds

## Contributing

When adding features:

1. Update schema in `database.py`
2. Add migration support in `db_migrate.py`
3. Update documentation
4. Add tests
5. Update `FEATURES_SUMMARY.md`

## License

Same as original project.

## Changelog

### Version 2.0 (2026-01-23)

- ✨ Added document chunking with multiple strategies
- ✨ Added RAG system with embeddings
- ✨ Added Notion listener for auto-posting
- ✨ Added Mastodon listener for auto-replies
- ✨ Enhanced post generation with RAG
- 💾 Added three new database tables
- 📚 Added comprehensive documentation

### Version 1.0

- Original soft_batch features
- RSS article fetching
- Manual post generation
- Mastodon posting
- Image generation

---

**Happy automating! 🍪**
