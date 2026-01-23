"""
SQLite database schema and operations for soft_batch.

Tracks articles, generated posts, comments, and posting history.
"""
import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass


DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "soft_batch.db")


@dataclass
class PostRecord:
    """Represents a generated social media post."""
    id: int
    content: str
    status: str  # draft, posted, discarded
    created_at: str
    posted_at: Optional[str] = None
    mastodon_id: Optional[str] = None
    image_path: Optional[str] = None


@dataclass
class ArticleRecord:
    """Represents a fetched article."""
    id: int
    url: str
    title: str
    source: str
    first_seen_at: str
    last_seen_at: str
    published_at: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class CommentRecord:
    """Represents a generated comment on an article."""
    id: int
    article_id: int
    content: str
    status: str  # draft, posted, discarded
    created_at: str
    posted_at: Optional[str] = None


# SQL Schema Definition
SCHEMA_SQL = """
-- Articles table: tracks all articles we've seen from RSS feeds
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    published_at TEXT,
    summary TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Posts table: tracks generated social media posts
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, posted, discarded
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    posted_at TEXT,
    mastodon_id TEXT,
    image_path TEXT,
    error_message TEXT,

    CHECK (status IN ('draft', 'posted', 'discarded'))
);

-- Comments table: tracks generated comments on articles
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, posted, discarded
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    posted_at TEXT,
    mastodon_id TEXT,
    error_message TEXT,

    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    CHECK (status IN ('draft', 'posted', 'discarded'))
);

-- Posting schedule/queue table
CREATE TABLE IF NOT EXISTS posting_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    comment_id INTEGER,
    scheduled_for TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
    CHECK ((post_id IS NOT NULL AND comment_id IS NULL) OR
           (post_id IS NULL AND comment_id IS NOT NULL))
);

-- Analytics/metrics table
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_type TEXT NOT NULL,  -- e.g., 'post_generated', 'article_fetched', 'api_call'
    metric_value REAL,
    metadata TEXT,  -- JSON string for additional data
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indices for better performance
CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_last_seen ON articles(last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_comments_article_id ON comments(article_id);
CREATE INDEX IF NOT EXISTS idx_comments_status ON comments(status);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_queue_scheduled ON posting_queue(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_queue_priority ON posting_queue(priority DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON metrics(created_at DESC);

-- Views for common queries
CREATE VIEW IF NOT EXISTS v_recent_posts AS
SELECT
    id,
    content,
    status,
    created_at,
    posted_at,
    mastodon_id
FROM posts
ORDER BY created_at DESC
LIMIT 50;

CREATE VIEW IF NOT EXISTS v_recent_articles AS
SELECT
    id,
    url,
    title,
    source,
    published_at,
    last_seen_at
FROM articles
ORDER BY last_seen_at DESC
LIMIT 100;

CREATE VIEW IF NOT EXISTS v_pending_queue AS
SELECT
    q.id,
    q.scheduled_for,
    q.priority,
    p.content AS post_content,
    c.content AS comment_content,
    a.title AS article_title
FROM posting_queue q
LEFT JOIN posts p ON q.post_id = p.id
LEFT JOIN comments c ON q.comment_id = c.id
LEFT JOIN articles a ON c.article_id = a.id
WHERE q.scheduled_for > datetime('now')
ORDER BY q.scheduled_for ASC, q.priority DESC;
"""


@contextmanager
def get_db(db_path: str = DEFAULT_DB_PATH):
    """
    Context manager for database connections.

    Usage:
        with get_db() as conn:
            conn.execute("SELECT * FROM articles")
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize the database with schema."""
    print(f"[*] Initializing database at {db_path}...")

    with get_db(db_path) as conn:
        conn.executescript(SCHEMA_SQL)

    print("[+] Database initialized successfully!")


def get_schema_info(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Get information about the database schema."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("""
            SELECT name, sql
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = {row["name"]: row["sql"] for row in cursor.fetchall()}

        # Get all indices
        cursor.execute("""
            SELECT name, tbl_name, sql
            FROM sqlite_master
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
            ORDER BY tbl_name, name
        """)
        indices = [(row["name"], row["tbl_name"], row["sql"]) for row in cursor.fetchall()]

        # Get all views
        cursor.execute("""
            SELECT name, sql
            FROM sqlite_master
            WHERE type='view'
            ORDER BY name
        """)
        views = {row["name"]: row["sql"] for row in cursor.fetchall()}

        return {
            "tables": tables,
            "indices": indices,
            "views": views
        }


def save_article(url: str, title: str, source: str,
                published_at: Optional[str] = None,
                summary: Optional[str] = None,
                db_path: str = DEFAULT_DB_PATH) -> int:
    """
    Save or update an article. Returns article ID.
    If article exists (by URL), updates last_seen_at.
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Check if article exists
        cursor.execute("SELECT id FROM articles WHERE url = ?", (url,))
        existing = cursor.fetchone()

        if existing:
            # Update last_seen_at
            cursor.execute(
                "UPDATE articles SET last_seen_at = datetime('now') WHERE id = ?",
                (existing["id"],)
            )
            return existing["id"]
        else:
            # Insert new article
            cursor.execute("""
                INSERT INTO articles (url, title, source, published_at, summary)
                VALUES (?, ?, ?, ?, ?)
            """, (url, title, source, published_at, summary))
            return cursor.lastrowid


def save_post(content: str, status: str = "draft",
              image_path: Optional[str] = None,
              db_path: str = DEFAULT_DB_PATH) -> int:
    """Save a generated post. Returns post ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO posts (content, status, image_path)
            VALUES (?, ?, ?)
        """, (content, status, image_path))
        return cursor.lastrowid


def save_comment(article_id: int, content: str,
                status: str = "draft",
                db_path: str = DEFAULT_DB_PATH) -> int:
    """Save a generated comment. Returns comment ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comments (article_id, content, status)
            VALUES (?, ?, ?)
        """, (article_id, content, status))
        return cursor.lastrowid


def mark_post_posted(post_id: int, mastodon_id: Optional[str] = None,
                    db_path: str = DEFAULT_DB_PATH) -> None:
    """Mark a post as successfully posted."""
    with get_db(db_path) as conn:
        conn.execute("""
            UPDATE posts
            SET status = 'posted',
                posted_at = datetime('now'),
                mastodon_id = ?
            WHERE id = ?
        """, (mastodon_id, post_id))


def mark_comment_posted(comment_id: int, mastodon_id: Optional[str] = None,
                       db_path: str = DEFAULT_DB_PATH) -> None:
    """Mark a comment as successfully posted."""
    with get_db(db_path) as conn:
        conn.execute("""
            UPDATE comments
            SET status = 'posted',
                posted_at = datetime('now'),
                mastodon_id = ?
            WHERE id = ?
        """, (mastodon_id, comment_id))


def get_recent_posts(limit: int = 10, status: Optional[str] = None,
                    db_path: str = DEFAULT_DB_PATH) -> List[PostRecord]:
    """Get recent posts, optionally filtered by status."""
    with get_db(db_path) as conn:
        if status:
            query = "SELECT * FROM posts WHERE status = ? ORDER BY created_at DESC LIMIT ?"
            rows = conn.execute(query, (status, limit)).fetchall()
        else:
            query = "SELECT * FROM posts ORDER BY created_at DESC LIMIT ?"
            rows = conn.execute(query, (limit,)).fetchall()

        return [PostRecord(**dict(row)) for row in rows]


def get_article_by_url(url: str, db_path: str = DEFAULT_DB_PATH) -> Optional[ArticleRecord]:
    """Get an article by URL."""
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM articles WHERE url = ?", (url,)).fetchone()
        return ArticleRecord(**dict(row)) if row else None


def log_metric(metric_type: str, metric_value: Optional[float] = None,
              metadata: Optional[str] = None,
              db_path: str = DEFAULT_DB_PATH) -> None:
    """Log a metric for analytics."""
    with get_db(db_path) as conn:
        conn.execute("""
            INSERT INTO metrics (metric_type, metric_value, metadata)
            VALUES (?, ?, ?)
        """, (metric_type, metric_value, metadata))


def get_stats(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Get overall statistics about the database."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        stats = {}

        # Article stats
        cursor.execute("SELECT COUNT(*) as count FROM articles")
        stats["total_articles"] = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(DISTINCT source) as count FROM articles")
        stats["unique_sources"] = cursor.fetchone()["count"]

        # Post stats
        cursor.execute("SELECT status, COUNT(*) as count FROM posts GROUP BY status")
        stats["posts_by_status"] = {row["status"]: row["count"] for row in cursor.fetchall()}

        # Comment stats
        cursor.execute("SELECT status, COUNT(*) as count FROM comments GROUP BY status")
        stats["comments_by_status"] = {row["status"]: row["count"] for row in cursor.fetchall()}

        # Recent activity
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM posts
            WHERE created_at > datetime('now', '-7 days')
        """)
        stats["posts_last_7_days"] = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM articles
            WHERE first_seen_at > datetime('now', '-7 days')
        """)
        stats["new_articles_last_7_days"] = cursor.fetchone()["count"]

        return stats


if __name__ == "__main__":
    """CLI for database management."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        init_db()
    elif len(sys.argv) > 1 and sys.argv[1] == "schema":
        schema_info = get_schema_info()
        print("\n=== TABLES ===")
        for name, sql in schema_info["tables"].items():
            print(f"\n{name}:")
            print(sql)

        print("\n\n=== INDICES ===")
        for name, tbl, sql in schema_info["indices"]:
            print(f"{name} on {tbl}")

        print("\n\n=== VIEWS ===")
        for name in schema_info["views"].keys():
            print(f"- {name}")
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        stats = get_stats()
        print("\n=== DATABASE STATISTICS ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
    else:
        print("Usage:")
        print("  python database.py init    - Initialize database")
        print("  python database.py schema  - Show schema")
        print("  python database.py stats   - Show statistics")
