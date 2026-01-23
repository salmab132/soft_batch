# Soft Batch FastAPI Documentation

## Overview

The Soft Batch API provides REST endpoints for managing articles, posts, comments, and analytics for your bakery social media automation.

**Base URL:** `http://VM_IP:8000`

**API Docs:** `http://VM_IP:8000/docs` (interactive Swagger UI)

**Alternative Docs:** `http://VM_IP:8000/redoc`

## Quick Start

### Health Check

```bash
curl http://localhost:8000/health
```

### Get Statistics

```bash
curl http://localhost:8000/stats
```

## Endpoints

### General

#### `GET /`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "message": "Soft Batch API is running",
  "data": {"version": "1.0.0"}
}
```

#### `GET /health`
Detailed health check with database stats.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "stats": {...},
  "timestamp": "2026-01-22T20:00:00"
}
```

#### `GET /stats`
Get overall database statistics.

**Response:**
```json
{
  "total_articles": 10,
  "unique_sources": 3,
  "posts_by_status": {"draft": 5, "posted": 2},
  "comments_by_status": {"draft": 15},
  "new_articles_last_7_days": 8,
  "posts_last_7_days": 3
}
```

### Articles

#### `GET /articles`
List articles with optional filtering.

**Query Parameters:**
- `limit` (int): Number of results (default: 50)
- `source` (string): Filter by source name
- `offset` (int): Pagination offset (default: 0)

**Example:**
```bash
curl "http://localhost:8000/articles?limit=10&source=Sally's Baking Addiction"
```

**Response:**
```json
[
  {
    "id": 1,
    "url": "https://example.com/recipe",
    "title": "Amazing Cupcakes",
    "source": "Sally's Baking Addiction",
    "first_seen_at": "2026-01-22T10:00:00",
    "last_seen_at": "2026-01-22T10:00:00",
    "published_at": "2026-01-22T09:00:00",
    "summary": "Learn how to make..."
  }
]
```

#### `GET /articles/{article_id}`
Get a specific article by ID.

**Example:**
```bash
curl http://localhost:8000/articles/1
```

#### `POST /articles/fetch`
Fetch fresh articles from RSS feeds (runs in background).

**Body:**
```json
{
  "limit": 5
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/articles/fetch?limit=5"
```

### Posts

#### `GET /posts`
List posts with optional filtering.

**Query Parameters:**
- `limit` (int): Number of results (default: 50)
- `status` (string): Filter by status (draft/posted/discarded)
- `offset` (int): Pagination offset (default: 0)

**Example:**
```bash
curl "http://localhost:8000/posts?status=draft&limit=10"
```

**Response:**
```json
[
  {
    "id": 1,
    "content": "Check out our new recipe!",
    "status": "draft",
    "created_at": "2026-01-22T10:00:00",
    "posted_at": null,
    "mastodon_id": null,
    "image_path": null
  }
]
```

#### `GET /posts/{post_id}`
Get a specific post by ID.

**Example:**
```bash
curl http://localhost:8000/posts/1
```

#### `POST /posts`
Create a new post manually.

**Body:**
```json
{
  "content": "Fresh sourdough bread available today!",
  "status": "draft",
  "image_path": "/path/to/image.png"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -d '{"content": "Fresh bread today!", "status": "draft"}'
```

#### `POST /posts/generate`
Generate a new post using AI.

**Body:**
```json
{
  "use_brand_docs": true
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/posts/generate \
  -H "Content-Type: application/json" \
  -d '{"use_brand_docs": true}'
```

**Response:**
```json
{
  "status": "success",
  "message": "Post generated",
  "data": {
    "post_id": 5,
    "content": "There's something magical about..."
  }
}
```

#### `PATCH /posts/{post_id}/status`
Update post status.

**Query Parameters:**
- `status` (string): New status (draft/posted/discarded)
- `mastodon_id` (string, optional): Mastodon post ID if posted

**Example:**
```bash
curl -X PATCH "http://localhost:8000/posts/1/status?status=posted&mastodon_id=12345"
```

### Comments

#### `GET /comments`
List comments with optional filtering.

**Query Parameters:**
- `limit` (int): Number of results (default: 50)
- `status` (string): Filter by status
- `article_id` (int): Filter by article
- `offset` (int): Pagination offset

**Example:**
```bash
curl "http://localhost:8000/comments?status=draft&article_id=1"
```

**Response:**
```json
[
  {
    "id": 1,
    "article_id": 5,
    "content": "This looks amazing!",
    "status": "draft",
    "created_at": "2026-01-22T10:00:00",
    "posted_at": null,
    "mastodon_id": null
  }
]
```

#### `POST /comments`
Create a new comment manually.

**Body:**
```json
{
  "article_id": 1,
  "content": "Great recipe!",
  "status": "draft"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/comments \
  -H "Content-Type: application/json" \
  -d '{"article_id": 1, "content": "Love this!", "status": "draft"}'
```

#### `POST /comments/generate`
Generate comments for articles using AI.

**Body:**
```json
{
  "article_limit": 5,
  "comments_per_article": 2,
  "use_brand_docs": true
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/comments/generate \
  -H "Content-Type: application/json" \
  -d '{"article_limit": 5, "comments_per_article": 2}'
```

**Response:**
```json
{
  "status": "success",
  "message": "Generated 10 comments for 5 articles",
  "data": {
    "comment_count": 10,
    "article_count": 5,
    "comment_ids": [1, 2, 3, ...]
  }
}
```

#### `PATCH /comments/{comment_id}/status`
Update comment status.

**Query Parameters:**
- `status` (string): New status (draft/posted/discarded)
- `mastodon_id` (string, optional): Mastodon post ID if posted

**Example:**
```bash
curl -X PATCH "http://localhost:8000/comments/1/status?status=posted&mastodon_id=67890"
```

### Metrics

#### `GET /metrics`
Get metrics/analytics data.

**Query Parameters:**
- `metric_type` (string, optional): Filter by metric type
- `limit` (int): Number of results (default: 100)

**Example:**
```bash
curl "http://localhost:8000/metrics?metric_type=post_generated_api&limit=50"
```

**Response:**
```json
[
  {
    "id": 1,
    "metric_type": "post_generated_api",
    "metric_value": 1.0,
    "metadata": null,
    "created_at": "2026-01-22T10:00:00"
  }
]
```

#### `POST /metrics`
Log a custom metric.

**Body:**
```json
{
  "metric_type": "custom_event",
  "metric_value": 42.5,
  "metadata": "{\"key\": \"value\"}"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/metrics \
  -H "Content-Type: application/json" \
  -d '{"metric_type": "api_call", "metric_value": 1.0}'
```

## Common Workflows

### Workflow 1: Generate and Publish a Post

```bash
# 1. Generate a post
POST_ID=$(curl -s -X POST http://localhost:8000/posts/generate \
  -H "Content-Type: application/json" \
  -d '{"use_brand_docs": true}' | jq -r '.data.post_id')

# 2. Review the post
curl http://localhost:8000/posts/$POST_ID

# 3. Mark as posted
curl -X PATCH "http://localhost:8000/posts/$POST_ID/status?status=posted&mastodon_id=12345"
```

### Workflow 2: Generate Comments for Articles

```bash
# 1. Fetch fresh articles
curl -X POST "http://localhost:8000/articles/fetch?limit=10"

# 2. Wait a moment for background task
sleep 2

# 3. Generate comments
curl -X POST http://localhost:8000/comments/generate \
  -H "Content-Type: application/json" \
  -d '{"article_limit": 5, "comments_per_article": 2}'

# 4. Get draft comments
curl "http://localhost:8000/comments?status=draft&limit=20"
```

### Workflow 3: Monitor Activity

```bash
# Get overall stats
curl http://localhost:8000/stats

# Get recent posts
curl "http://localhost:8000/posts?limit=10"

# Get recent metrics
curl "http://localhost:8000/metrics?limit=50"
```

## Service Management

### Start/Stop Service

```bash
# Check status
sudo systemctl status soft-batch-api

# Start service
sudo systemctl start soft-batch-api

# Stop service
sudo systemctl stop soft-batch-api

# Restart service
sudo systemctl restart soft-batch-api

# View logs
sudo journalctl -u soft-batch-api -f
```

### Firewall Configuration

To access the API from outside the VM:

```bash
# Create firewall rule
gcloud compute firewall-rules create allow-soft-batch-api \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --target-tags=http-server

# Get VM external IP
gcloud compute instances describe soft-batch-vm \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI:** `http://VM_IP:8000/docs`
  - Interactive API testing
  - Request/response examples
  - Try out endpoints directly in browser

- **ReDoc:** `http://VM_IP:8000/redoc`
  - Clean, readable documentation
  - Detailed schemas

## Error Handling

All endpoints return standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable

Error response format:
```json
{
  "detail": "Error message here"
}
```

## Authentication

Currently, the API has no authentication. For production use, consider adding:
- API keys
- OAuth2
- JWT tokens
- IP whitelisting (via firewall)

## Rate Limiting

No rate limiting is currently implemented. For production, consider:
- Using nginx as a reverse proxy with rate limiting
- Implementing application-level rate limiting
- Cloud-based API gateway

## Performance Tips

1. Use pagination for large result sets
2. Filter by status/source when possible
3. Use background tasks for expensive operations
4. Monitor metrics to track API usage
5. Set up log rotation for the service

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u soft-batch-api -n 50

# Check if port is in use
sudo lsof -i :8000

# Verify Python dependencies
python3 -m pip list | grep -E '(fastapi|uvicorn)'
```

### Can't access externally

```bash
# Check firewall rules
gcloud compute firewall-rules list

# Verify service is listening
sudo netstat -tlnp | grep 8000

# Test locally first
curl http://localhost:8000/health
```

### Database errors

```bash
# Check database file
ls -lh ~/soft_batch.db

# Verify database schema
python3 db_migrate.py tables

# Check database stats
python3 db_migrate.py stats
```
