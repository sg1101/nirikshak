"""LLM API wrapper using OpenAI-compatible endpoint (OpenCode Go) with caching and retries."""

import base64
import hashlib
import json
import logging
from pathlib import Path

from openai import OpenAI, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from nirikshak.core.config import get_settings

logger = logging.getLogger(__name__)

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return _client


def _cache_dir() -> Path:
    d = get_settings().storage_dir / "llm_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(system: str | None, prompt: str, model: str, temperature: float) -> str:
    raw = json.dumps({"system": system, "prompt": prompt, "model": model, "temperature": temperature}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str) -> str | None:
    path = _cache_dir() / f"{key}.json"
    if path.exists():
        data = json.loads(path.read_text())
        return data["response"]
    return None


def _cache_set(key: str, response: str):
    path = _cache_dir() / f"{key}.json"
    path.write_text(json.dumps({"response": response}))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(RateLimitError),
)
def call_llm(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> str:
    settings = get_settings()
    model = model or settings.llm_model

    key = _cache_key(system, prompt, model, temperature)
    cached = _cache_get(key)
    if cached is not None:
        logger.debug("LLM cache hit: %s", key[:12])
        return cached

    client = get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = response.choices[0].message.content

    _cache_set(key, text)
    logger.debug("LLM call completed and cached: %s", key[:12])
    return text


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(RateLimitError),
)
def call_llm_vision(
    images: list[bytes],
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> str:
    """Call LLM with images. Uses vision-capable model."""
    settings = get_settings()
    # Use a vision-capable model — mimo-v2-omni supports images
    model = model or "mimo-v2-omni"

    # Build cache key from image hashes + prompt
    img_hashes = [hashlib.sha256(img).hexdigest()[:16] for img in images]
    raw = json.dumps({"images": img_hashes, "system": system, "prompt": prompt, "model": model}, sort_keys=True)
    key = hashlib.sha256(raw.encode()).hexdigest()

    cached = _cache_get(key)
    if cached is not None:
        logger.debug("LLM vision cache hit: %s", key[:12])
        return cached

    client = get_client()
    content = []
    for img in images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64.b64encode(img).decode()}",
            },
        })
    content.append({"type": "text", "text": prompt})

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = response.choices[0].message.content

    _cache_set(key, text)
    return text


# Backward-compatible aliases
call_claude = call_llm
call_claude_vision = call_llm_vision
