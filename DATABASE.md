# Database Schema Documentation

## Overview

The `soft_batch` application uses SQLite to track articles, generated posts, comments, and analytics. The database is automatically initialized on first run.

## Database Location

- **Default path**: `soft_batch.db` (in the project root)
- **Backup format**: `soft_batch.db.backup_YYYYMMDD_HHMMSS`

## Schema

### Tables

#### `articles`
Tracks all articles fetched from RSS feeds.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| url | TEXT | Unique article URL |
| title | TEXT | Article title |
| source | TEXT | Source name (e.g., "Sally's Baking Addiction") |
| published_at | TEXT | ISO-8601 publication timestamp |
| summary | TEXT | Article summary/description |
| first_seen_at | TEXT | When we first discovered this article |
| last_seen_at | TEXT | Last time this article appeared in feeds |
| created_at | TEXT | Database record creation time |

**Indices:**
- `idx_articles_url` - Fast URL lookups
- `idx_articles_source` - Filter by source
- `idx_articles_published_at` - Sort by publication date
- `idx_articles_last_seen` - Find recently active articles

#### `posts`
Tracks generated social media posts.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| content | TEXT | Post content |
| status | TEXT | `draft`, `posted`, or `discarded` |
| created_at | TEXT | When the post was generated |
| posted_at | TEXT | When the post was published (if posted) |
| mastodon_id | TEXT | Mastodon post ID (if posted) |
| image_path | TEXT | Path to attached image (if any) |
| error_message | TEXT | Error details if posting failed |

**Indices:**
- `idx_posts_status` - Filter by status
- `idx_posts_created_at` - Sort by creation date
- `idx_posts_posted_at` - Sort by post date

#### `comments`
Tracks generated comments on articles.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| article_id | INTEGER | Foreign key to `articles.id` |
| content | TEXT | Comment content |
| status | TEXT | `draft`, `posted`, or `discarded` |
| created_at | TEXT | When the comment was generated |
| posted_at | TEXT | When the comment was posted (if posted) |
| mastodon_id | TEXT | Mastodon post ID (if posted) |
| error_message | TEXT | Error details if posting failed |

**Indices:**
- `idx_comments_article_id` - Fast article lookups
- `idx_comments_status` - Filter by status
- `idx_comments_created_at` - Sort by creation date

#### `posting_queue`
Optional: Schedule posts/comments for future posting.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| post_id | INTEGER | Foreign key to `posts.id` (nullable) |
| comment_id | INTEGER | Foreign key to `comments.id` (nullable) |
| scheduled_for | TEXT | ISO-8601 timestamp to post at |
| priority | INTEGER | Priority (higher = more important) |
| created_at | TEXT | When scheduled |

**Indices:**
- `idx_queue_scheduled` - Sort by schedule
- `idx_queue_priority` - Sort by priority

#### `metrics`
Analytics and logging.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| metric_type | TEXT | Metric name (e.g., `post_generated`, `api_call`) |
| metric_value | REAL | Numeric value (optional) |
| metadata | TEXT | JSON string for additional data |
| created_at | TEXT | When the metric was logged |

**Indices:**
- `idx_metrics_type` - Filter by metric type
- `idx_metrics_created_at` - Sort by time

### Views

#### `v_recent_posts`
Last 50 posts ordered by creation date.

#### `v_recent_articles`
Last 100 articles ordered by last_seen_at.

#### `v_pending_queue`
Scheduled posts/comments with their content (joined with posts/comments/articles).

## CLI Tools

### Database Migration Tool (`db_migrate.py`)

```bash
# Initialize database (creates tables, indices, views)
python db_migrate.py init

# Show all tables, indices, and row counts
python db_migrate.py tables

# Show detailed statistics
python db_migrate.py stats

# Create a backup
python db_migrate.py backup

# Interactive SQL query interface
python db_migrate.py query

# Show full schema SQL
python db_migrate.py schema
```

### Database Module (`database.py`)

Can also be used directly:

```bash
# Initialize database
python database.py init

# Show schema
python database.py schema

# Show statistics
python database.py stats
```

## Python API

### Initialization

```python
from database import init_db

# Initialize database (safe to call multiple times)
init_db()
```

### Saving Data

```python
from database import save_article, save_post, save_comment

# Save an article
article_id = save_article(
    url="https://example.com/article",
    title="Amazing Cupcakes",
    source="Sally's Baking Addiction",
    published_at="2026-01-22T10:00:00Z",
    summary="How to make perfect cupcakes..."
)

# Save a post
post_id = save_post(
    content="Check out our new recipe!",
    status="draft",  # or "posted", "discarded"
    image_path="/path/to/image.png"
)

# Save a comment
comment_id = save_comment(
    article_id=article_id,
    content="This looks amazing!",
    status="draft"
)
```

### Updating Status

```python
from database import mark_post_posted, mark_comment_posted

# Mark a post as successfully posted
mark_post_posted(post_id, mastodon_id="123456")

# Mark a comment as posted
mark_comment_posted(comment_id, mastodon_id="789012")
```

### Querying Data

```python
from database import get_recent_posts, get_article_by_url, get_stats

# Get recent posts
posts = get_recent_posts(limit=10, status="draft")
for post in posts:
    print(f"{post.id}: {post.content[:50]}...")

# Find article by URL
article = get_article_by_url("https://example.com/article")
if article:
    print(f"Found: {article.title}")

# Get overall statistics
stats = get_stats()
print(f"Total articles: {stats['total_articles']}")
print(f"Posts by status: {stats['posts_by_status']}")
```

### Logging Metrics

```python
from database import log_metric

# Log a metric
log_metric("post_generated", metric_value=1.0)
log_metric("api_call", metadata='{"endpoint": "/v1/chat", "tokens": 150}')
```

### Direct SQL Access

```python
from database import get_db

# Use context manager for safe database access
with get_db() as conn:
    cursor = conn.execute("""
        SELECT title, source, published_at
        FROM articles
        WHERE source = ?
        ORDER BY published_at DESC
        LIMIT 5
    """, ("Sally's Baking Addiction",))

    for row in cursor.fetchall():
        print(f"{row['title']} - {row['published_at']}")
```

## Integration with Main App

The database is automatically integrated into `main.py`:

1. **First run**: Database is auto-initialized
2. **Baking flow**: Articles and comments are saved
3. **Post flow**: Posts are saved and status is tracked
4. **Metrics**: API calls and generations are logged

### New Commands

```bash
# Show database statistics
python main.py stats
```

## Backup Strategy

```bash
# Create backup before major changes
python db_migrate.py backup

# Backups are named: soft_batch.db.backup_20260122_143025
```

## Migration Guide

If you have existing data you want to import:

1. Initialize the database:
   ```bash
   python db_migrate.py init
   ```

2. Use the interactive SQL interface:
   ```bash
   python db_migrate.py query
   ```

3. Or write a custom Python script using the database API.

## Performance Notes

- All timestamps are stored as ISO-8601 TEXT (SQLite's recommended format)
- Indices are created on frequently queried columns
- Foreign key constraints ensure data integrity
- Views provide convenient pre-joined queries
- Use `EXPLAIN QUERY PLAN` to optimize custom queries

## Example Queries

```sql
-- Find all draft comments for a specific article
SELECT c.content, c.created_at
FROM comments c
JOIN articles a ON c.article_id = a.id
WHERE a.url = 'https://example.com/article'
  AND c.status = 'draft';

-- Get posting activity by day (last 7 days)
SELECT
    DATE(posted_at) as day,
    COUNT(*) as posts_count
FROM posts
WHERE posted_at > datetime('now', '-7 days')
  AND status = 'posted'
GROUP BY DATE(posted_at)
ORDER BY day DESC;

-- Find articles we haven't commented on yet
SELECT a.title, a.url, a.source
FROM articles a
LEFT JOIN comments c ON a.id = c.article_id
WHERE c.id IS NULL
  AND a.first_seen_at > datetime('now', '-7 days')
ORDER BY a.published_at DESC;

-- Metrics summary by type (last 24 hours)
SELECT
    metric_type,
    COUNT(*) as count,
    SUM(metric_value) as total
FROM metrics
WHERE created_at > datetime('now', '-1 day')
GROUP BY metric_type
ORDER BY count DESC;
```
