import os
from openai import OpenAI

def generate_social_post(brand_docs):
    """
    Uses brand docs to generate a single social media post.
    """
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

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
