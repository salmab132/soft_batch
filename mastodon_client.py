from mastodon import Mastodon, MastodonError
import os

def get_mastodon_client():
    """Creates and returns a Mastodon client instance."""
    access_token = os.getenv("MASTODON_ACCESS_TOKEN")
    api_base_url = os.getenv("MASTODON_BASE_URL")

    if not access_token:
        raise ValueError("MASTODON_ACCESS_TOKEN environment variable is not set")
    if not api_base_url:
        raise ValueError("MASTODON_BASE_URL environment variable is not set")

    try:
        return Mastodon(
            access_token=access_token,
            api_base_url=api_base_url,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to create Mastodon client: {str(e)}") from e

def post_to_mastodon(client, text):
    """Posts text to Mastodon. Raises exception on failure."""
    if not client:
        raise ValueError("Mastodon client is required")
    if not text or not text.strip():
        raise ValueError("Post text cannot be empty")

    try:
        post_text = text + "\n\n🤖 AI-generated content"
        result = client.status_post(post_text)
        return result
    except MastodonError as e:
        raise RuntimeError(f"Mastodon API error: {str(e)}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to post to Mastodon: {str(e)}") from e
