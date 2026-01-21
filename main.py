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

if load_dotenv:
    load_dotenv()

def run_post_flow():
    print("📄 Fetching brand docs from Notion...")
    brand_docs = get_brand_docs()

    print("\n🤖 Generating draft post...")
    post = generate_social_post(brand_docs)

    print("\n================ DRAFT POST ================\n")
    print(post)
    print("\n===========================================\n")

    # ✅ HUMAN-IN-THE-LOOP APPROVAL
    approve = input("Post this to Mastodon? (y/n): ").strip().lower()

    if approve == "y":
        print("🚀 Posting...")
        mastodon = get_mastodon_client()
        post_to_mastodon(mastodon, post)
        print("✅ Posted successfully!")
    else:
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

    print("\n🤖 Generating comment drafts...")
    items = generate_article_comments(
        brand_docs,
        articles,
        comments_per_article=args.comments,
    )

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


def main():
    parser = argparse.ArgumentParser(prog="soft_batch")
    subparsers = parser.add_subparsers(dest="command")

    baking = subparsers.add_parser("baking", help="Get top baking articles + generate comment drafts")
    baking.add_argument("--articles", type=int, default=5, help="How many top articles to fetch")
    baking.add_argument("--comments", type=int, default=2, help="How many comments per article")

    args = parser.parse_args()

    if args.command == "baking":
        run_baking_flow(args)
        return

    # Default behavior (no subcommand): generate a single post from Notion brand docs.
    run_post_flow()

if __name__ == "__main__":
    main()
