from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


DEFAULT_MODEL_VERSION = (
    "sundai-club/sb00:"
    "04dcb1c60a24e279ad90bf9f34fbc21004f0d8151a67ef5af0e3efa3362028ec"
)


@dataclass(frozen=True)
class ReplicateImageResult:
    path: str
    url: Optional[str] = None


def _timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def generate_image(
    *,
    prompt: str,
    out_dir: str = "outputs",
    filename_prefix: str = "replicate",
    model_version: Optional[str] = None,
    output_format: str = "png",
    aspect_ratio: str = "1:1",
    megapixels: str = "1",
    num_inference_steps: int = 28,
    guidance_scale: float = 3,
    prompt_strength: float = 0.8,
    output_quality: int = 80,
    go_fast: bool = False,
    extra_input: Optional[dict[str, Any]] = None,
) -> ReplicateImageResult:
    """
    Generate an image via Replicate and write it to disk.

    Note: this file is intentionally NOT named `replicate.py` to avoid shadowing
    the official `replicate` SDK package.

    Requirements:
    - pip install replicate
    - set REPLICATE_API_TOKEN in environment

    Returns:
    - ReplicateImageResult(path=<local file>, url=<optional output url>)
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt is required")

    try:
        import replicate  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "Missing dependency 'replicate'. Install dependencies with: python -m pip install -r requirements.txt"
        ) from e

    mv = (model_version or os.getenv("REPLICATE_MODEL_VERSION") or DEFAULT_MODEL_VERSION).strip()
    if not mv:
        raise ValueError("model_version is required (or set REPLICATE_MODEL_VERSION)")

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    safe_ext = (output_format or "png").strip().lower()
    if safe_ext.startswith("."):
        safe_ext = safe_ext[1:]

    file_path = out_path / f"{filename_prefix}-{_timestamp_slug()}.{safe_ext}"

    input_payload: dict[str, Any] = {
        "model": "dev",
        "prompt": prompt,
        "go_fast": go_fast,
        "lora_scale": 1,
        "megapixels": megapixels,
        "num_outputs": 1,
        "aspect_ratio": aspect_ratio,
        "output_format": safe_ext,
        "guidance_scale": guidance_scale,
        "output_quality": output_quality,
        "prompt_strength": prompt_strength,
        "extra_lora_scale": 1,
        "num_inference_steps": num_inference_steps,
    }

    if extra_input:
        input_payload.update(extra_input)

    output = replicate.run(mv, input=input_payload)
    # Replicate commonly returns a list of file-like outputs
    item = output[0] if isinstance(output, list) and output else output

    url: Optional[str] = getattr(item, "url", None)
    data = item.read() if hasattr(item, "read") else None
    if not data:
        raise RuntimeError("Replicate returned no image bytes")

    file_path.write_bytes(data)
    return ReplicateImageResult(path=str(file_path), url=url)


if __name__ == "__main__":
    # Minimal manual test: python replicate_client.py
    result = generate_image(
        prompt="teddy bear in a cafe with a chef's hat rolling out dough",
    )
    print(result.url or result.path)

