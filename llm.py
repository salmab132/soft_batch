import os
import json
from typing import List, Optional
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from articles import Article


def _get_client() -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )


def _extract_json_object(text: str) -> Optional[str]:
    """
    Best-effort extraction of a JSON object from model output.
    """
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


class ArticleComments(BaseModel):
    url: str
    title: str
    source: Optional[str] = None
    comments: List[str]


class ArticleCommentsResult(BaseModel):
    items: List[ArticleComments]

def generate_social_post(brand_docs):
    """
    Uses brand docs to generate a single social media post.
    """
    client = _get_client()

    prompt = f"""
        You are the social media manager for a bakery called Soft Batch.

        Brand documentation:
        {brand_docs}

        Write ONE short social media post.
        Tone: warm, artisanal, cozy, modern bakery.
        Do not include hashtags.
        """

    response = client.chat.completions.create(
        model="z-ai/glm-4.5-air",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,  # Limit tokens for a short social media post
    )

    return response.choices[0].message.content.strip()


def generate_article_comments(
    brand_docs: str,
    articles: List[Article],
    *,
    comments_per_article: int = 2,
) -> List[ArticleComments]:
    """
    Generates a few cozy, bakery-voice comment drafts for each article.
    Returns structured results when possible; falls back to best-effort parsing.
    """
    client = _get_client()

    article_lines = []
    for idx, a in enumerate(articles, start=1):
        summary = (a.summary or "").strip()
        if len(summary) > 300:
            summary = summary[:300].rstrip() + "…"
        article_lines.append(
            f"{idx}. Title: {a.title}\n"
            f"   Source: {a.source}\n"
            f"   URL: {a.url}\n"
            f"   Summary: {summary}\n"
        )

    prompt = f"""
You are the social media manager for a bakery called Soft Batch.

Brand documentation:
{brand_docs}

Task:
Generate {comments_per_article} short, friendly comment drafts for SOME of the articles below (prefer the most interesting ones).
These are comments we could post under a link share (Mastodon-style), so they should be:
- warm, artisanal, cozy, modern bakery voice
- no hashtags
- no emojis
- avoid sounding like an ad; be genuinely helpful/curious
- do NOT invent facts beyond the title/summary
- keep each comment under 280 characters

Return VALID JSON ONLY using this schema:
{{
  "items": [
    {{
      "url": "https://...",
      "title": "…",
      "source": "…",
      "comments": ["…", "…"]
    }}
  ]
}}

Articles:
{chr(10).join(article_lines)}
""".strip()

    response = client.chat.completions.create(
        model="z-ai/glm-4.5-air",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900,
    )

    content = (response.choices[0].message.content or "").strip()
    extracted = _extract_json_object(content)
    if not extracted:
        # Hard fallback: return a single pseudo-item with raw output
        return [
            ArticleComments(
                url=articles[0].url if articles else "",
                title=articles[0].title if articles else "LLM output",
                source=articles[0].source if articles else None,
                comments=[content] if content else [],
            )
        ]

    try:
        data = json.loads(extracted)
        parsed = ArticleCommentsResult.model_validate(data)
        # Basic cleanup
        cleaned: List[ArticleComments] = []
        for item in parsed.items:
            comments = []
            for c in item.comments:
                c = (c or "").strip()
                if c:
                    comments.append(c)
            if comments:
                cleaned.append(
                    ArticleComments(
                        url=item.url.strip(),
                        title=item.title.strip(),
                        source=(item.source.strip() if item.source else None),
                        comments=comments[: max(1, comments_per_article)],
                    )
                )
        return cleaned
    except (json.JSONDecodeError, ValidationError):
        return [
            ArticleComments(
                url=articles[0].url if articles else "",
                title=articles[0].title if articles else "LLM output",
                source=articles[0].source if articles else None,
                comments=[content] if content else [],
            )
        ]
