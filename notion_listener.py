"""
Notion API listener for auto-creating posts when content changes.

This module provides functionality to:
1. Poll Notion pages for changes
2. Sync changed content to the RAG system
3. Auto-generate social media posts from new/updated content
"""
import os
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from notion import get_brand_docs
from rag import sync_notion_document_to_rag
from llm import generate_social_post
from database import (
    save_post,
    save_notion_document,
    get_db,
    DEFAULT_DB_PATH,
    log_metric
)


class NotionListener:
    """
    Listener for Notion page changes.
    
    Can poll pages for updates and trigger actions when content changes.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        poll_interval: int = 300,  # 5 minutes default
        auto_generate_posts: bool = True,
        use_rag: bool = True,
        db_path: str = DEFAULT_DB_PATH
    ):
        """
        Initialize Notion listener.
        
        Args:
            api_key: Notion API key (defaults to env var)
            poll_interval: How often to check for changes (seconds)
            auto_generate_posts: Whether to auto-generate posts on change
            use_rag: Whether to use RAG when generating posts
            db_path: Database path
        """
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        self.poll_interval = poll_interval
        self.auto_generate_posts = auto_generate_posts
        self.use_rag = use_rag
        self.db_path = db_path
        
        if not self.api_key:
            raise ValueError("NOTION_API_KEY environment variable or api_key parameter required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        # Track last known state of pages
        self._last_modified: Dict[str, str] = {}
    
    def fetch_page_content(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch page content from Notion.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            Dict with 'content', 'title', 'last_edited_time'
        """
        # Get page metadata
        page_url = f"https://api.notion.com/v1/pages/{page_id}"
        page_response = requests.get(page_url, headers=self.headers)
        page_response.raise_for_status()
        page_data = page_response.json()
        
        last_edited = page_data.get("last_edited_time", "")
        
        # Extract title if available
        title = ""
        properties = page_data.get("properties", {})
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_array = prop_data.get("title", [])
                if title_array:
                    title = title_array[0].get("plain_text", "")
                break
        
        # Get page blocks (content)
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_response = requests.get(blocks_url, headers=self.headers)
        blocks_response.raise_for_status()
        
        blocks = blocks_response.json()["results"]
        text_chunks = []
        
        for block in blocks:
            block_type = block["type"]
            if "rich_text" in block.get(block_type, {}):
                for rt in block[block_type]["rich_text"]:
                    text_chunks.append(rt["plain_text"])
        
        content = "\n".join(text_chunks)
        
        return {
            "content": content,
            "title": title or f"Notion Page {page_id}",
            "last_edited_time": last_edited
        }
    
    def has_page_changed(self, page_id: str, last_edited_time: str) -> bool:
        """
        Check if a page has changed since we last saw it.
        
        Args:
            page_id: Notion page ID
            last_edited_time: Current last_edited_time from Notion
            
        Returns:
            True if page has changed
        """
        if page_id not in self._last_modified:
            return True
        
        return self._last_modified[page_id] != last_edited_time
    
    def sync_page(self, page_id: str, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Sync a Notion page to the local system.
        
        Fetches content, stores in database, chunks and embeds for RAG.
        
        Args:
            page_id: Notion page ID
            force: Force sync even if page hasn't changed
            
        Returns:
            Dict with sync results or None if no changes
        """
        try:
            page_data = self.fetch_page_content(page_id)
            
            # Check if changed
            if not force and not self.has_page_changed(page_id, page_data["last_edited_time"]):
                return None
            
            print(f"[Notion] Syncing page '{page_data['title']}'...")
            
            # Sync to RAG system
            doc_id, chunk_ids = sync_notion_document_to_rag(
                notion_page_id=page_id,
                content=page_data["content"],
                title=page_data["title"],
                chunking_strategy="paragraphs",
                chunk_size=500,
                db_path=self.db_path
            )
            
            # Update last modified timestamp
            self._last_modified[page_id] = page_data["last_edited_time"]
            
            log_metric("notion_page_synced", 1.0, db_path=self.db_path)
            
            print(f"[Notion] ✓ Synced {len(chunk_ids)} chunks")
            
            return {
                "page_id": page_id,
                "title": page_data["title"],
                "doc_id": doc_id,
                "chunk_count": len(chunk_ids),
                "last_edited": page_data["last_edited_time"]
            }
            
        except Exception as e:
            print(f"[Notion] Error syncing page {page_id}: {e}")
            return None
    
    def generate_post_from_update(self, page_id: str) -> Optional[int]:
        """
        Generate a social media post from a page update.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            Post ID if generated, None otherwise
        """
        try:
            # Fetch current content
            page_data = self.fetch_page_content(page_id)
            
            print(f"[Notion] Generating post from '{page_data['title']}'...")
            
            # Generate post using RAG
            post_text = generate_social_post(
                brand_docs=page_data["content"],
                use_rag=self.use_rag,
                rag_query=f"What's new or interesting about {page_data['title']}?"
            )
            
            # Save as draft
            post_id = save_post(
                content=post_text,
                status="draft",
                db_path=self.db_path
            )
            
            log_metric("auto_post_generated", 1.0, db_path=self.db_path)
            
            print(f"[Notion] ✓ Generated draft post (ID: {post_id})")
            print(f"[Notion] Preview: {post_text[:100]}...")
            
            return post_id
            
        except Exception as e:
            print(f"[Notion] Error generating post: {e}")
            return None
    
    def poll_once(self, page_ids: List[str]) -> Dict[str, Any]:
        """
        Poll Notion pages once for changes.
        
        Args:
            page_ids: List of Notion page IDs to check
            
        Returns:
            Dict with results summary
        """
        results = {
            "synced": [],
            "posts_generated": [],
            "errors": []
        }
        
        for page_id in page_ids:
            try:
                # Sync the page
                sync_result = self.sync_page(page_id)
                
                if sync_result:
                    results["synced"].append(sync_result)
                    
                    # Auto-generate post if enabled
                    if self.auto_generate_posts:
                        post_id = self.generate_post_from_update(page_id)
                        if post_id:
                            results["posts_generated"].append({
                                "page_id": page_id,
                                "post_id": post_id
                            })
                
            except Exception as e:
                results["errors"].append({
                    "page_id": page_id,
                    "error": str(e)
                })
        
        return results
    
    def start_polling(self, page_ids: List[str], max_iterations: Optional[int] = None):
        """
        Start continuous polling of Notion pages.
        
        Args:
            page_ids: List of Notion page IDs to monitor
            max_iterations: Max poll cycles (None = infinite)
        """
        print(f"[Notion] Starting listener for {len(page_ids)} page(s)")
        print(f"[Notion] Poll interval: {self.poll_interval}s")
        print(f"[Notion] Auto-generate posts: {self.auto_generate_posts}")
        print(f"[Notion] Use RAG: {self.use_rag}")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"\n[Notion] Poll #{iteration} at {datetime.now(timezone.utc).isoformat()}")
                
                results = self.poll_once(page_ids)
                
                # Print summary
                if results["synced"]:
                    print(f"[Notion] Synced {len(results['synced'])} page(s)")
                if results["posts_generated"]:
                    print(f"[Notion] Generated {len(results['posts_generated'])} post(s)")
                if results["errors"]:
                    print(f"[Notion] Errors: {len(results['errors'])}")
                    for err in results["errors"]:
                        print(f"  - {err['page_id']}: {err['error']}")
                
                if not results["synced"] and not results["errors"]:
                    print("[Notion] No changes detected")
                
                # Check if we should stop
                if max_iterations and iteration >= max_iterations:
                    print(f"[Notion] Reached max iterations ({max_iterations})")
                    break
                
                # Wait for next poll
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n[Notion] Listener stopped by user")


def run_notion_listener(
    page_ids: Optional[List[str]] = None,
    poll_interval: int = 300,
    auto_generate: bool = True
):
    """
    Convenience function to run the Notion listener.
    
    Args:
        page_ids: List of page IDs (defaults to NOTION_PAGE_ID env var)
        poll_interval: Poll interval in seconds
        auto_generate: Auto-generate posts on changes
    """
    if not page_ids:
        page_id = os.getenv("NOTION_PAGE_ID")
        if not page_id:
            raise ValueError("NOTION_PAGE_ID environment variable required")
        page_ids = [page_id]
    
    listener = NotionListener(
        poll_interval=poll_interval,
        auto_generate_posts=auto_generate,
        use_rag=True
    )
    
    listener.start_polling(page_ids)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "sync":
            # One-time sync
            page_id = os.getenv("NOTION_PAGE_ID")
            if not page_id:
                print("Error: NOTION_PAGE_ID environment variable required")
                sys.exit(1)
            
            listener = NotionListener()
            result = listener.sync_page(page_id, force=True)
            if result:
                print(f"\n✓ Synced successfully:")
                print(f"  Title: {result['title']}")
                print(f"  Chunks: {result['chunk_count']}")
            else:
                print("✗ Sync failed")
        
        elif sys.argv[1] == "generate":
            # Generate post from current content
            page_id = os.getenv("NOTION_PAGE_ID")
            if not page_id:
                print("Error: NOTION_PAGE_ID environment variable required")
                sys.exit(1)
            
            listener = NotionListener()
            post_id = listener.generate_post_from_update(page_id)
            if post_id:
                print(f"\n✓ Generated draft post (ID: {post_id})")
            else:
                print("✗ Post generation failed")
        
        elif sys.argv[1] == "listen":
            # Start continuous polling
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
            run_notion_listener(poll_interval=interval)
        
        else:
            print("Unknown command")
            sys.exit(1)
    else:
        print("Usage:")
        print("  python notion_listener.py sync      - One-time sync")
        print("  python notion_listener.py generate  - Generate post from current content")
        print("  python notion_listener.py listen [interval]  - Start polling (default 300s)")
