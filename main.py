import os
import sys
import argparse

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None  # type: ignore

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from notion import get_brand_docs
from llm import generate_social_post, generate_article_comments
from mastodon_client import get_mastodon_client, post_to_mastodon
from articles import get_top_baking_articles
from replicate_client import generate_image
from database import (
    init_db, save_article, save_post, save_comment,
    mark_post_posted, mark_comment_posted, log_metric, get_stats
)

if load_dotenv:
    load_dotenv()

def run_post_flow():
    print("📄 Fetching brand docs from Notion...")
    brand_docs = get_brand_docs()

    print("\n🤖 Generating draft post...")
    post = generate_social_post(brand_docs)
    log_metric("post_generated", 1.0)

    print("\n================ DRAFT POST ================\n")
    print(post)
    print("\n===========================================\n")

    # Optional: generate an image to attach
    media_path = None
    try:
        make_image = input("Generate an image with Replicate to attach? (y/n): ").strip().lower()
        if make_image == "y":
            prompt = input("Image prompt (press Enter to use the post text): ").strip()
            if not prompt:
                prompt = post
            print("🎨 Generating image...")
            img = generate_image(prompt=prompt, output_format="png")
            media_path = img.path
            print(f"🖼️ Image saved: {media_path}")
            log_metric("image_generated", 1.0)
    except Exception as e:
        print(f"⚠️ Image generation failed (will continue without image): {e}")
        media_path = None

    # Save post to database
    post_id = save_post(post, status="draft", image_path=media_path)
    print(f"💾 Saved to database (post_id: {post_id})")

    # ✅ HUMAN-IN-THE-LOOP APPROVAL (final gate)
    approve = input("Post this to Mastodon? (y/n): ").strip().lower()

    if approve == "y":
        print("🚀 Posting...")
        mastodon = get_mastodon_client()
        result = post_to_mastodon(mastodon, post, media_path=media_path, alt_text="AI-generated bakery illustration")

        # Mark as posted in database
        mastodon_id = result.get('id') if isinstance(result, dict) else None
        mark_post_posted(post_id, mastodon_id=mastodon_id)
        log_metric("post_published", 1.0)

        print("✅ Posted successfully!")
    else:
        # Update status to discarded
        from database import get_db
        with get_db() as conn:
            conn.execute("UPDATE posts SET status = 'discarded' WHERE id = ?", (post_id,))
        print("❌ Post discarded.")


def run_baking_flow(args: argparse.Namespace) -> None:
    try:
        brand_docs = get_brand_docs()
    except Exception:
        # Allow running without Notion configured; we'll still generate comments.
        brand_docs = ""

    print("🧁 Fetching top baking articles (RSS)...")
    articles = get_top_baking_articles(limit=args.articles)

    if not articles:
        print("No articles found (feeds may be unavailable).")
        return

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

    log_metric("articles_fetched", len(articles))

    print("\n🤖 Generating comment drafts...")
    items = generate_article_comments(
        brand_docs,
        articles,
        comments_per_article=args.comments,
    )

    # Save comments to database
    for item in items:
        article_id = article_ids.get(item.url)
        if article_id:
            for comment_text in item.comments:
                save_comment(article_id, comment_text, status="draft")

    log_metric("comments_generated", sum(len(item.comments) for item in items))

    print("\n================ TOP BAKING ARTICLES ================\n")
    for i, a in enumerate(articles, start=1):
        print(f"{i}. {a.title}")
        print(f"   Source: {a.source}")
        print(f"   URL: {a.url}")
        if a.published_at:
            print(f"   Published: {a.published_at}")
        print()

    print("\n================ COMMENT DRAFTS ================\n")
    for item in items:
        print(f"- {item.title}")
        print(f"  {item.url}")
        if item.source:
            print(f"  ({item.source})")
        for c in item.comments:
            print(f"  • {c}")
        print()

    # Show database stats
    print("\n================ DATABASE STATS ================\n")
    stats = get_stats()
    print(f"Total articles tracked: {stats['total_articles']}")
    print(f"Draft comments: {stats.get('comments_by_status', {}).get('draft', 0)}")
    print(f"Draft posts: {stats.get('posts_by_status', {}).get('draft', 0)}")
    print()


def main():
    # Initialize database if it doesn't exist
    import os
    from database import DEFAULT_DB_PATH
    if not os.path.exists(DEFAULT_DB_PATH):
        print("🔧 First run detected. Initializing database...")
        init_db()
        print()

    parser = argparse.ArgumentParser(prog="soft_batch")
    subparsers = parser.add_subparsers(dest="command")

    baking = subparsers.add_parser("baking", help="Get top baking articles + generate comment drafts")
    baking.add_argument("--articles", type=int, default=5, help="How many top articles to fetch")
    baking.add_argument("--comments", type=int, default=2, help="How many comments per article")

    stats_cmd = subparsers.add_parser("stats", help="Show database statistics")

    args = parser.parse_args()

    if args.command == "baking":
        run_baking_flow(args)
        return

    if args.command == "stats":
        stats = get_stats()
        print("\n================ DATABASE STATISTICS ================\n")
        print(f"📰 Total articles: {stats['total_articles']}")
        print(f"📝 Unique sources: {stats['unique_sources']}")
        print(f"🆕 New articles (7d): {stats['new_articles_last_7_days']}")
        print(f"📊 Posts (7d): {stats['posts_last_7_days']}")
        print(f"\n📝 Posts by status:")
        for status, count in stats.get('posts_by_status', {}).items():
            print(f"   {status}: {count}")
        print(f"\n💬 Comments by status:")
        for status, count in stats.get('comments_by_status', {}).items():
            print(f"   {status}: {count}")
        print()
        return

    # Default behavior (no subcommand): generate a single post from Notion brand docs.
    run_post_flow()

if __name__ == "__main__":
    main()
