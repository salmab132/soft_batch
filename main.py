import os
import sys
from dotenv import load_dotenv

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from notion import get_brand_docs
from llm import generate_social_post
from mastodon_client import get_mastodon_client, post_to_mastodon

load_dotenv()

def main():
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

if __name__ == "__main__":
    main()
