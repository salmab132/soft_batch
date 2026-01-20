import requests
import os

def get_brand_docs():
    """
    Fetches blocks from a Notion page and turns them into plain text.
    """
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")

    HEADERS = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    blocks = response.json()["results"]
    text_chunks = []

    for block in blocks:
        block_type = block["type"]
        if "rich_text" in block[block_type]:
            for rt in block[block_type]["rich_text"]:
                text_chunks.append(rt["plain_text"])

    return "\n".join(text_chunks)
