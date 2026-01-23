# Listeners Guide

This guide covers the **automated listeners** for Notion and Mastodon that enable auto-posting and auto-replies.

## Overview

Two listeners are available:

1. **Notion Listener** - Monitors Notion pages for changes and auto-generates posts
2. **Mastodon Listener** - Monitors Mastodon for mentions/comments and auto-generates replies

## Notion Listener

The Notion listener polls your Notion pages for updates and can automatically generate social media posts when content changes.

### Quick Start

#### One-Time Sync
```bash
python notion_listener.py sync
```

Syncs your Notion page once to the RAG system.

#### Generate Post from Current Content
```bash
python notion_listener.py generate
```

Generates a social media post from current Notion content (saved as draft).

#### Start Continuous Listener
```bash
# Check every 300 seconds (5 minutes)
python notion_listener.py listen

# Custom interval (600 seconds = 10 minutes)
python notion_listener.py listen 600
```

Or via main.py:
```bash
python main.py notion-listen --interval 300
```

### How It Works

1. **Polling**: Checks Notion page(s) at regular intervals
2. **Change Detection**: Compares `last_edited_time` to detect updates
3. **Sync**: Downloads changed content and syncs to RAG system
4. **Generate**: Automatically generates a draft post from new content
5. **Storage**: Saves post as 'draft' in database for review

### Configuration

```python
from notion_listener import NotionListener

listener = NotionListener(
    api_key=None,              # Defaults to NOTION_API_KEY env var
    poll_interval=300,         # Check every 5 minutes
    auto_generate_posts=True,  # Auto-generate posts on change
    use_rag=True              # Use RAG for post generation
)

# Monitor multiple pages
listener.start_polling(
    page_ids=["page_id_1", "page_id_2"],
    max_iterations=None  # Run forever (or set a limit)
)
```

### Features

- **Smart Change Detection**: Only processes pages that have changed
- **RAG Integration**: Uses RAG to generate focused posts
- **Draft Mode**: All posts saved as drafts for human review
- **Error Handling**: Continues running even if individual pages fail
- **Metrics**: Logs sync and generation events to database

### Use Cases

1. **Content Calendar**: Update Notion doc with upcoming promotions → auto-generate posts
2. **Brand Updates**: Modify brand voice docs → auto-generate posts reflecting changes
3. **Seasonal Content**: Add seasonal content to Notion → get draft posts automatically

## Mastodon Listener

The Mastodon listener monitors your Mastodon account for mentions and replies, then auto-generates contextual responses.

### Quick Start

#### Check for Mentions Once
```bash
python mastodon_listener.py check
```

Checks for new mentions and saves them (no replies generated).

#### Start Listener (Draft Mode)
```bash
# Check every 180 seconds (3 minutes)
python mastodon_listener.py listen

# Custom interval
python mastodon_listener.py listen 600
```

Or via main.py:
```bash
python main.py mastodon-listen --interval 180
```

Generates reply drafts (not posted automatically).

#### Start Listener (Auto-Reply Mode)
```bash
python mastodon_listener.py listen-auto 180
```

Or via main.py:
```bash
python main.py mastodon-listen --interval 180 --auto-reply
```

⚠️ **Warning**: This posts replies automatically without human review!

### How It Works

1. **Fetch**: Gets recent notifications (mentions, replies)
2. **Store**: Saves interactions to database (deduplicates)
3. **Filter**: Identifies unresponded interactions
4. **Generate**: Creates contextual reply using RAG + brand docs
5. **Post/Draft**: Either posts reply or saves as draft

### Configuration

```python
from mastodon_listener import MastodonListener

listener = MastodonListener(
    client=None,           # Defaults to creating from env vars
    auto_reply=False,      # True = auto-post, False = draft
    use_rag=True,          # Use RAG for context
    poll_interval=180      # Check every 3 minutes
)

listener.start_polling(max_iterations=None)
```

### Reply Generation

The system generates contextual replies:

```python
# User: "@soft_batch Do you use organic flour?"
# System retrieves docs about ingredients
# Reply: "@user Yes! We use organic flour sourced from local mills..."
```

Features:
- **RAG Context**: Retrieves relevant brand info to answer accurately
- **Brand Voice**: Maintains warm, artisanal tone
- **@ Mentions**: Automatically includes proper @ mentions
- **Character Limit**: Keeps replies under 280 characters

### Interaction Tracking

All interactions are stored in `mastodon_interactions` table:

```python
from database import get_unresponded_interactions

# Get pending interactions
pending = get_unresponded_interactions(limit=10)

for interaction in pending:
    print(f"{interaction['author_account']}: {interaction['content']}")
```

### Safety Features

1. **Draft Mode Default**: Replies are drafts unless `--auto-reply` is set
2. **Deduplication**: Won't process same interaction twice
3. **Error Recovery**: Continues running even if individual replies fail
4. **Human Review**: Draft mode allows you to review before posting

### Use Cases

1. **Customer Service**: Auto-respond to common questions
2. **Engagement**: Maintain conversation without constant monitoring
3. **After-Hours**: Keep account responsive outside business hours
4. **FAQ**: Answer frequent questions consistently using brand docs

## Running Both Listeners

You can run both listeners simultaneously in separate terminals:

**Terminal 1** (Notion):
```bash
python main.py notion-listen --interval 300
```

**Terminal 2** (Mastodon):
```bash
python main.py mastodon-listen --interval 180
```

Or use a process manager like `systemd` (Linux) or `pm2` (Node.js-based, works on Windows).

## Best Practices

### Notion Listener

1. **Interval**: 5-10 minutes is reasonable (Notion API rate limits apply)
2. **Review Drafts**: Always review auto-generated posts before publishing
3. **Page Structure**: Use clear paragraphs for better RAG chunking
4. **Multiple Pages**: Monitor brand guide + seasonal content separately

### Mastodon Listener

1. **Interval**: 2-5 minutes for responsive customer service
2. **Start with Draft Mode**: Test reply quality before enabling auto-reply
3. **Monitor Database**: Check `mastodon_interactions` table regularly
4. **Brand Docs**: Keep Notion docs updated for accurate replies

## Monitoring

Check listener activity:

```bash
# View recent posts (including auto-generated)
python main.py stats

# Check database directly
python database.py stats
```

View metrics in database:
```sql
SELECT * FROM metrics WHERE metric_type IN (
    'notion_page_synced',
    'auto_post_generated',
    'auto_reply_posted',
    'auto_reply_drafted'
) ORDER BY created_at DESC LIMIT 20;
```

## Troubleshooting

### Notion Listener

**Issue**: "Failed to sync page"
- Verify `NOTION_API_KEY` and `NOTION_PAGE_ID` are set
- Check page sharing settings in Notion (must be shared with integration)
- Verify API key permissions

**Issue**: "No posts generated"
- Check `auto_generate_posts=True`
- Verify page content isn't empty
- Check database for error logs

### Mastodon Listener

**Issue**: "No notifications found"
- Verify `MASTODON_ACCESS_TOKEN` and `MASTODON_BASE_URL`
- Check that your account has notifications
- May need to wait for new mentions

**Issue**: "Reply generation failed"
- Check `OPENROUTER_API_KEY` is set
- Verify brand docs are accessible
- Review error messages in output

## Environment Variables Required

```bash
# Notion
NOTION_API_KEY=secret_xxx
NOTION_PAGE_ID=abc123

# Mastodon
MASTODON_ACCESS_TOKEN=xxx
MASTODON_BASE_URL=https://mastodon.social

# OpenRouter (for LLM + embeddings)
OPENROUTER_API_KEY=sk-xxx
```

## Advanced: Production Deployment

For production use, consider:

1. **Process Manager**: Use systemd, supervisor, or pm2
2. **Logging**: Redirect output to log files
3. **Monitoring**: Set up health checks
4. **Error Alerts**: Send notifications on failures
5. **Rate Limiting**: Respect API rate limits
6. **Database Backups**: Regular backups of soft_batch.db

Example systemd service:
```ini
[Unit]
Description=Soft Batch Notion Listener
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/soft_batch
Environment="NOTION_API_KEY=xxx"
Environment="OPENROUTER_API_KEY=xxx"
ExecStart=/usr/bin/python3 main.py notion-listen --interval 300
Restart=always

[Install]
WantedBy=multi-user.target
```

## Summary

- **Notion Listener**: Auto-generates posts from Notion page changes
- **Mastodon Listener**: Auto-replies to mentions/comments
- **Both**: Use RAG for context-aware, on-brand content
- **Safety**: Draft mode by default for human review
- **Flexible**: Configurable intervals, multiple pages, error recovery
