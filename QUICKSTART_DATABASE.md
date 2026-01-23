# Database Quick Start Guide

## Setup (Automatic)

The database is **automatically initialized** the first time you run `main.py`. No manual setup required!

```bash
# First run will create the database
python main.py baking
```

## Manual Initialization

If you want to manually initialize or reset the database:

```bash
# Initialize database
python database.py init

# Or use the migration tool
python db_migrate.py init
```

## Quick Commands

### View Database Status

```bash
# Show tables and row counts
python db_migrate.py tables

# Show detailed statistics
python db_migrate.py stats

# Show statistics from main app
python main.py stats
```

### Backup Database

```bash
# Create a timestamped backup
python db_migrate.py backup
```

### Query Database

```bash
# Interactive SQL interface
python db_migrate.py query

# Example queries in the interactive mode:
SQL> SELECT * FROM articles LIMIT 5;
SQL> SELECT status, COUNT(*) FROM posts GROUP BY status;
SQL> exit
```

## What Gets Tracked

### Articles
- Every article fetched from RSS feeds
- URL, title, source, publication date
- First/last seen timestamps
- Prevents duplicate fetching

### Posts
- All generated social media posts
- Status: draft, posted, or discarded
- Posted timestamp and Mastodon ID
- Image attachments

### Comments
- Generated comments on articles
- Linked to specific articles
- Status tracking (draft/posted/discarded)
- Mastodon post IDs

### Metrics
- API calls
- Content generation events
- Custom analytics

## File Locations

- **Database**: `soft_batch.db` (in project root)
- **Backups**: `soft_batch.db.backup_YYYYMMDD_HHMMSS`
- **Schema**: See `DATABASE.md` for full documentation

## Common Tasks

### Find draft comments

```bash
python db_migrate.py query
SQL> SELECT c.content, a.title
     FROM comments c
     JOIN articles a ON c.article_id = a.id
     WHERE c.status = 'draft'
     LIMIT 10;
```

### See recent activity

```bash
python main.py stats
```

### Export data

```bash
python db_migrate.py query
SQL> SELECT * FROM articles;
# Copy the output or redirect to file
```

## Troubleshooting

### Database locked
- Close other connections to the database
- Make sure no other instances of the app are running

### Reset database
```bash
python db_migrate.py backup  # Safety first!
python db_migrate.py init    # This will prompt for confirmation
```

### Check schema
```bash
python db_migrate.py schema
```

## Deploy to VM

The database files are already set up on your VM. When you update the code:

```bash
# Transfer new database files
gcloud compute scp --zone=us-central1-a database.py db_migrate.py DATABASE.md soft-batch-vm:~

# SSH and run
gcloud compute ssh soft-batch-vm --zone=us-central1-a
python3 main.py baking
```

The database will be created automatically on the VM on first run.

## Next Steps

See `DATABASE.md` for:
- Complete schema documentation
- Advanced queries
- Python API reference
- Migration strategies
