"""
Mastodon comments listener for auto-replying to mentions and comments.

This module provides functionality to:
1. Monitor Mastodon for mentions and replies
2. Auto-generate contextual replies using RAG
3. Post replies automatically or save as drafts
"""
import os
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from mastodon import Mastodon
from mastodon_client import get_mastodon_client, post_to_mastodon
from llm import generate_comment_reply
from notion import get_brand_docs
from database import (
    save_mastodon_interaction,
    get_unresponded_interactions,
    mark_interaction_responded,
    save_post,
    mark_post_posted,
    log_metric,
    get_db,
    DEFAULT_DB_PATH
)


class MastodonListener:
    """
    Listener for Mastodon mentions and comments.
    
    Monitors timeline for interactions and can auto-reply.
    """
    
    def __init__(
        self,
        client: Optional[Mastodon] = None,
        auto_reply: bool = False,
        use_rag: bool = True,
        poll_interval: int = 180,  # 3 minutes default
        db_path: str = DEFAULT_DB_PATH
    ):
        """
        Initialize Mastodon listener.
        
        Args:
            client: Mastodon client (defaults to creating one from env)
            auto_reply: Whether to automatically post replies (vs save as draft)
            use_rag: Whether to use RAG for generating replies
            poll_interval: How often to check for new interactions (seconds)
            db_path: Database path
        """
        self.client = client or get_mastodon_client()
        self.auto_reply = auto_reply
        self.use_rag = use_rag
        self.poll_interval = poll_interval
        self.db_path = db_path
        
        # Get our account info
        self.account = self.client.me()
        self.account_id = self.account["id"]
        
        # Track last seen notification ID
        self._last_notification_id: Optional[str] = None
    
    def fetch_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch recent notifications (mentions, replies, etc).
        
        Args:
            limit: Max number of notifications to fetch
            
        Returns:
            List of notification dicts
        """
        try:
            notifications = self.client.notifications(
                limit=limit,
                exclude_types=["follow", "favourite", "reblog", "poll"]
            )
            return [dict(n) for n in notifications]
        except Exception as e:
            print(f"[Mastodon] Error fetching notifications: {e}")
            return []
    
    def fetch_mentions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch mentions from notifications.
        
        Args:
            limit: Max mentions to return
            
        Returns:
            List of mention status dicts
        """
        notifications = self.fetch_notifications(limit=limit)
        
        mentions = []
        for notif in notifications:
            if notif.get("type") == "mention":
                status = notif.get("status")
                if status:
                    mentions.append(dict(status))
        
        return mentions
    
    def store_interaction(self, status: Dict[str, Any]) -> Optional[int]:
        """
        Store a Mastodon interaction in the database.
        
        Args:
            status: Status dict from Mastodon API
            
        Returns:
            Interaction ID or None if already exists
        """
        try:
            # Determine interaction type
            in_reply_to = status.get("in_reply_to_id")
            interaction_type = "reply" if in_reply_to else "mention"
            
            # Check if this is a reply to one of our posts
            our_post_id = None
            if in_reply_to:
                # Check if we have this post in our database
                with get_db(self.db_path) as conn:
                    row = conn.execute(
                        "SELECT id FROM posts WHERE mastodon_id = ?",
                        (in_reply_to,)
                    ).fetchone()
                    if row:
                        our_post_id = row["id"]
                        interaction_type = "comment"
            
            # Save to database
            interaction_id = save_mastodon_interaction(
                mastodon_id=status["id"],
                interaction_type=interaction_type,
                author_account=status["account"]["acct"],
                content=status["content"],
                in_reply_to_id=in_reply_to,
                our_post_id=our_post_id,
                db_path=self.db_path
            )
            
            return interaction_id
            
        except Exception as e:
            print(f"[Mastodon] Error storing interaction: {e}")
            return None
    
    def generate_reply(self, content: str, author: str) -> str:
        """
        Generate a reply to a comment/mention.
        
        Args:
            content: Original comment content
            author: Author's account handle
            
        Returns:
            Generated reply text
        """
        try:
            # Get brand docs for context
            brand_docs = ""
            try:
                brand_docs = get_brand_docs()
            except Exception:
                # Continue without brand docs if Notion isn't configured
                pass
            
            # Strip HTML tags from content
            import re
            clean_content = re.sub(r'<[^>]+>', '', content)
            
            # Generate reply
            reply = generate_comment_reply(
                original_comment=clean_content,
                brand_docs=brand_docs,
                use_rag=self.use_rag
            )
            
            # Add @ mention at the start
            if not reply.startswith(f"@{author}"):
                reply = f"@{author} {reply}"
            
            return reply
            
        except Exception as e:
            print(f"[Mastodon] Error generating reply: {e}")
            # Fallback reply
            return f"@{author} Thanks for reaching out! We'll get back to you soon."
    
    def process_interaction(
        self,
        interaction_id: int,
        mastodon_id: str,
        content: str,
        author: str
    ) -> Optional[int]:
        """
        Process a single interaction and generate a reply.
        
        Args:
            interaction_id: Database interaction ID
            mastodon_id: Mastodon status ID
            content: Comment content
            author: Author account
            
        Returns:
            Post ID if reply was created, None otherwise
        """
        try:
            print(f"[Mastodon] Processing interaction from @{author}")
            
            # Generate reply
            reply_text = self.generate_reply(content, author)
            
            print(f"[Mastodon] Generated reply: {reply_text[:100]}...")
            
            if self.auto_reply:
                # Post reply directly
                print(f"[Mastodon] Posting reply...")
                result = self.client.status_post(
                    status=reply_text,
                    in_reply_to_id=mastodon_id
                )
                
                # Save to posts table
                post_id = save_post(
                    content=reply_text,
                    status="posted",
                    db_path=self.db_path
                )
                
                # Mark as posted
                mastodon_reply_id = result["id"]
                mark_post_posted(post_id, mastodon_id=mastodon_reply_id, db_path=self.db_path)
                
                # Mark interaction as responded
                mark_interaction_responded(
                    interaction_id,
                    response_post_id=post_id,
                    db_path=self.db_path
                )
                
                log_metric("auto_reply_posted", 1.0, db_path=self.db_path)
                print(f"[Mastodon] ✓ Posted reply")
                
                return post_id
            else:
                # Save as draft
                post_id = save_post(
                    content=reply_text,
                    status="draft",
                    db_path=self.db_path
                )
                
                log_metric("auto_reply_drafted", 1.0, db_path=self.db_path)
                print(f"[Mastodon] ✓ Saved reply as draft (ID: {post_id})")
                
                return post_id
                
        except Exception as e:
            print(f"[Mastodon] Error processing interaction: {e}")
            return None
    
    def poll_once(self) -> Dict[str, Any]:
        """
        Poll for new interactions once.
        
        Returns:
            Dict with results summary
        """
        results = {
            "new_interactions": [],
            "replies_generated": [],
            "errors": []
        }
        
        try:
            # Fetch recent mentions
            mentions = self.fetch_mentions(limit=20)
            
            for status in mentions:
                try:
                    # Store in database (will skip if already exists)
                    interaction_id = self.store_interaction(status)
                    
                    if interaction_id:
                        results["new_interactions"].append({
                            "id": interaction_id,
                            "author": status["account"]["acct"],
                            "mastodon_id": status["id"]
                        })
                        
                except Exception as e:
                    results["errors"].append({
                        "status_id": status.get("id"),
                        "error": str(e)
                    })
            
            # Process unresponded interactions
            unresponded = get_unresponded_interactions(limit=5, db_path=self.db_path)
            
            for interaction in unresponded:
                try:
                    post_id = self.process_interaction(
                        interaction_id=interaction["id"],
                        mastodon_id=interaction["mastodon_id"],
                        content=interaction["content"],
                        author=interaction["author_account"]
                    )
                    
                    if post_id:
                        results["replies_generated"].append({
                            "interaction_id": interaction["id"],
                            "post_id": post_id
                        })
                        
                except Exception as e:
                    results["errors"].append({
                        "interaction_id": interaction["id"],
                        "error": str(e)
                    })
            
        except Exception as e:
            print(f"[Mastodon] Error in poll cycle: {e}")
            results["errors"].append({"general": str(e)})
        
        return results
    
    def start_polling(self, max_iterations: Optional[int] = None):
        """
        Start continuous polling for Mastodon interactions.
        
        Args:
            max_iterations: Max poll cycles (None = infinite)
        """
        print(f"[Mastodon] Starting listener for @{self.account['acct']}")
        print(f"[Mastodon] Poll interval: {self.poll_interval}s")
        print(f"[Mastodon] Auto-reply: {self.auto_reply}")
        print(f"[Mastodon] Use RAG: {self.use_rag}")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"\n[Mastodon] Poll #{iteration} at {datetime.now(timezone.utc).isoformat()}")
                
                results = self.poll_once()
                
                # Print summary
                if results["new_interactions"]:
                    print(f"[Mastodon] Found {len(results['new_interactions'])} new interaction(s)")
                if results["replies_generated"]:
                    print(f"[Mastodon] Generated {len(results['replies_generated'])} reply(ies)")
                if results["errors"]:
                    print(f"[Mastodon] Errors: {len(results['errors'])}")
                
                if not results["new_interactions"] and not results["replies_generated"]:
                    print("[Mastodon] No new interactions")
                
                # Check if we should stop
                if max_iterations and iteration >= max_iterations:
                    print(f"[Mastodon] Reached max iterations ({max_iterations})")
                    break
                
                # Wait for next poll
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n[Mastodon] Listener stopped by user")


def run_mastodon_listener(
    auto_reply: bool = False,
    poll_interval: int = 180
):
    """
    Convenience function to run the Mastodon listener.
    
    Args:
        auto_reply: Whether to auto-post replies (vs draft)
        poll_interval: Poll interval in seconds
    """
    listener = MastodonListener(
        auto_reply=auto_reply,
        use_rag=True,
        poll_interval=poll_interval
    )
    
    listener.start_polling()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "check":
            # Check for new mentions once
            listener = MastodonListener(auto_reply=False)
            results = listener.poll_once()
            
            print("\n=== Poll Results ===")
            print(f"New interactions: {len(results['new_interactions'])}")
            print(f"Replies generated: {len(results['replies_generated'])}")
            if results['errors']:
                print(f"Errors: {len(results['errors'])}")
                for err in results['errors']:
                    print(f"  - {err}")
        
        elif sys.argv[1] == "listen":
            # Start continuous polling (draft mode)
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 180
            run_mastodon_listener(auto_reply=False, poll_interval=interval)
        
        elif sys.argv[1] == "listen-auto":
            # Start continuous polling (auto-reply mode)
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 180
            print("⚠️  AUTO-REPLY MODE - Replies will be posted automatically!")
            confirm = input("Continue? (yes/no): ").strip().lower()
            if confirm == "yes":
                run_mastodon_listener(auto_reply=True, poll_interval=interval)
            else:
                print("Cancelled")
        
        else:
            print("Unknown command")
            sys.exit(1)
    else:
        print("Usage:")
        print("  python mastodon_listener.py check              - Check for mentions once")
        print("  python mastodon_listener.py listen [interval]  - Start polling (draft mode)")
        print("  python mastodon_listener.py listen-auto [interval]  - Start polling (auto-reply mode)")
