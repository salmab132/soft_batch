"""
FastAPI REST API for soft_batch application.

Provides endpoints for:
- Article management
- Post generation and management
- Comment generation and management
- Database statistics
- RSS feed fetching
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from database import (
    init_db, save_article, save_post, save_comment,
    mark_post_posted, mark_comment_posted, get_recent_posts,
    get_article_by_url, log_metric, get_stats, get_db,
    PostRecord, ArticleRecord, DEFAULT_DB_PATH
)
from articles import get_top_baking_articles, Article
from llm import generate_social_post, generate_article_comments
from notion import get_brand_docs

# Initialize database on startup
if not os.path.exists(DEFAULT_DB_PATH):
    init_db()

app = FastAPI(
    title="Soft Batch API",
    description="API for managing bakery social media content generation",
    version="1.0.0"
)


# Pydantic models for requests/responses
class ArticleResponse(BaseModel):
    id: int
    url: str
    title: str
    source: str
    first_seen_at: str
    last_seen_at: str
    published_at: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    id: int
    content: str
    status: str
    created_at: str
    posted_at: Optional[str] = None
    mastodon_id: Optional[str] = None
    image_path: Optional[str] = None

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: int
    article_id: int
    content: str
    status: str
    created_at: str
    posted_at: Optional[str] = None
    mastodon_id: Optional[str] = None

    class Config:
        from_attributes = True


class PostCreateRequest(BaseModel):
    content: str
    status: str = "draft"
    image_path: Optional[str] = None


class CommentCreateRequest(BaseModel):
    article_id: int
    content: str
    status: str = "draft"


class GeneratePostRequest(BaseModel):
    use_brand_docs: bool = True


class GenerateCommentsRequest(BaseModel):
    article_limit: int = Field(default=5, ge=1, le=20)
    comments_per_article: int = Field(default=2, ge=1, le=5)
    use_brand_docs: bool = True


class StatusResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


# Health check
@app.get("/", response_model=StatusResponse)
async def root():
    """Health check endpoint."""
    return StatusResponse(
        status="ok",
        message="Soft Batch API is running",
        data={"version": "1.0.0"}
    )


@app.get("/health")
async def health_check():
    """Detailed health check."""
    try:
        stats = get_stats()
        return {
            "status": "healthy",
            "database": "connected",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


# Statistics endpoints
@app.get("/stats", response_model=Dict[str, Any])
async def get_statistics():
    """Get overall database statistics."""
    try:
        stats = get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Article endpoints
@app.get("/articles", response_model=List[ArticleResponse])
async def list_articles(
    limit: int = 50,
    source: Optional[str] = None,
    offset: int = 0
):
    """List articles with optional filtering."""
    try:
        with get_db() as conn:
            if source:
                query = """
                    SELECT * FROM articles
                    WHERE source = ?
                    ORDER BY last_seen_at DESC
                    LIMIT ? OFFSET ?
                """
                rows = conn.execute(query, (source, limit, offset)).fetchall()
            else:
                query = """
                    SELECT * FROM articles
                    ORDER BY last_seen_at DESC
                    LIMIT ? OFFSET ?
                """
                rows = conn.execute(query, (limit, offset)).fetchall()

            return [ArticleResponse(**dict(row)) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int):
    """Get a specific article by ID."""
    try:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Article not found")
            return ArticleResponse(**dict(row))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/fetch", response_model=StatusResponse)
async def fetch_articles(
    background_tasks: BackgroundTasks,
    limit: int = 5
):
    """Fetch fresh articles from RSS feeds."""
    def _fetch_and_save():
        try:
            articles = get_top_baking_articles(limit=limit)
            article_ids = []
            for article in articles:
                article_id = save_article(
                    url=article.url,
                    title=article.title,
                    source=article.source,
                    published_at=article.published_at,
                    summary=article.summary
                )
                article_ids.append(article_id)
            log_metric("articles_fetched_api", len(articles))
            return article_ids
        except Exception as e:
            log_metric("articles_fetch_error", 1.0, metadata=str(e))

    background_tasks.add_task(_fetch_and_save)

    return StatusResponse(
        status="success",
        message=f"Fetching up to {limit} articles in background"
    )


# Post endpoints
@app.get("/posts", response_model=List[PostResponse])
async def list_posts(
    limit: int = 50,
    status: Optional[str] = None,
    offset: int = 0
):
    """List posts with optional status filtering."""
    try:
        posts = get_recent_posts(limit=limit, status=status)
        return [PostResponse(**post.__dict__) for post in posts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int):
    """Get a specific post by ID."""
    try:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Post not found")
            return PostResponse(**dict(row))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/posts", response_model=StatusResponse)
async def create_post(post: PostCreateRequest):
    """Create a new post manually."""
    try:
        post_id = save_post(
            content=post.content,
            status=post.status,
            image_path=post.image_path
        )
        log_metric("post_created_api", 1.0)
        return StatusResponse(
            status="success",
            message="Post created",
            data={"post_id": post_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/posts/generate", response_model=StatusResponse)
async def generate_post(request: GeneratePostRequest):
    """Generate a new post using AI."""
    try:
        brand_docs = ""
        if request.use_brand_docs:
            try:
                brand_docs = get_brand_docs()
            except Exception:
                pass  # Continue without brand docs

        content = generate_social_post(brand_docs)
        post_id = save_post(content, status="draft")
        log_metric("post_generated_api", 1.0)

        return StatusResponse(
            status="success",
            message="Post generated",
            data={
                "post_id": post_id,
                "content": content
            }
        )
    except Exception as e:
        log_metric("post_generation_error", 1.0)
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/posts/{post_id}/status", response_model=StatusResponse)
async def update_post_status(
    post_id: int,
    status: str,
    mastodon_id: Optional[str] = None
):
    """Update post status."""
    if status not in ["draft", "posted", "discarded"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    try:
        with get_db() as conn:
            # Check if post exists
            row = conn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Post not found")

            if status == "posted":
                mark_post_posted(post_id, mastodon_id)
            else:
                conn.execute("UPDATE posts SET status = ? WHERE id = ?", (status, post_id))

        return StatusResponse(
            status="success",
            message=f"Post status updated to {status}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Comment endpoints
@app.get("/comments", response_model=List[CommentResponse])
async def list_comments(
    limit: int = 50,
    status: Optional[str] = None,
    article_id: Optional[int] = None,
    offset: int = 0
):
    """List comments with optional filtering."""
    try:
        with get_db() as conn:
            query = "SELECT * FROM comments WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            if article_id:
                query += " AND article_id = ?"
                params.append(article_id)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()
            return [CommentResponse(**dict(row)) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/comments", response_model=StatusResponse)
async def create_comment(comment: CommentCreateRequest):
    """Create a new comment manually."""
    try:
        comment_id = save_comment(
            article_id=comment.article_id,
            content=comment.content,
            status=comment.status
        )
        log_metric("comment_created_api", 1.0)
        return StatusResponse(
            status="success",
            message="Comment created",
            data={"comment_id": comment_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/comments/generate", response_model=StatusResponse)
async def generate_comments(request: GenerateCommentsRequest):
    """Generate comments for articles using AI."""
    try:
        brand_docs = ""
        if request.use_brand_docs:
            try:
                brand_docs = get_brand_docs()
            except Exception:
                pass

        # Fetch articles
        articles = get_top_baking_articles(limit=request.article_limit)
        if not articles:
            raise HTTPException(status_code=404, detail="No articles found")

        # Save articles to database
        article_ids = {}
        for article in articles:
            article_id = save_article(
                url=article.url,
                title=article.title,
                source=article.source,
                published_at=article.published_at,
                summary=article.summary
            )
            article_ids[article.url] = article_id

        # Generate comments
        comment_items = generate_article_comments(
            brand_docs,
            articles,
            comments_per_article=request.comments_per_article
        )

        # Save comments
        created_comments = []
        for item in comment_items:
            article_id = article_ids.get(item.url)
            if article_id:
                for comment_text in item.comments:
                    comment_id = save_comment(article_id, comment_text, status="draft")
                    created_comments.append(comment_id)

        log_metric("comments_generated_api", len(created_comments))

        return StatusResponse(
            status="success",
            message=f"Generated {len(created_comments)} comments for {len(comment_items)} articles",
            data={
                "comment_count": len(created_comments),
                "article_count": len(comment_items),
                "comment_ids": created_comments
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        log_metric("comments_generation_error", 1.0)
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/comments/{comment_id}/status", response_model=StatusResponse)
async def update_comment_status(
    comment_id: int,
    status: str,
    mastodon_id: Optional[str] = None
):
    """Update comment status."""
    if status not in ["draft", "posted", "discarded"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    try:
        with get_db() as conn:
            # Check if comment exists
            row = conn.execute("SELECT id FROM comments WHERE id = ?", (comment_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Comment not found")

            if status == "posted":
                mark_comment_posted(comment_id, mastodon_id)
            else:
                conn.execute("UPDATE comments SET status = ? WHERE id = ?", (status, comment_id))

        return StatusResponse(
            status="success",
            message=f"Comment status updated to {status}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Metrics endpoints
@app.get("/metrics", response_model=List[Dict[str, Any]])
async def get_metrics(
    metric_type: Optional[str] = None,
    limit: int = 100
):
    """Get metrics/analytics data."""
    try:
        with get_db() as conn:
            if metric_type:
                query = """
                    SELECT * FROM metrics
                    WHERE metric_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                rows = conn.execute(query, (metric_type, limit)).fetchall()
            else:
                query = """
                    SELECT * FROM metrics
                    ORDER BY created_at DESC
                    LIMIT ?
                """
                rows = conn.execute(query, (limit,)).fetchall()

            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/metrics", response_model=StatusResponse)
async def log_custom_metric(
    metric_type: str,
    metric_value: Optional[float] = None,
    metadata: Optional[str] = None
):
    """Log a custom metric."""
    try:
        log_metric(metric_type, metric_value, metadata)
        return StatusResponse(
            status="success",
            message="Metric logged"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
