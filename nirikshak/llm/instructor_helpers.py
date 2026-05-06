"""Structured LLM output via Instructor + Pydantic schemas (OpenAI-compatible)."""

import logging
from typing import TypeVar

import instructor

from nirikshak.core.config import get_settings
from nirikshak.llm.client import get_client

logger = logging.getLogger(__name__)

T = TypeVar("T")

_instructor_client = None


def get_instructor_client():
    global _instructor_client
    if _instructor_client is None:
        # Use JSON mode instead of tool_choice — more compatible with providers
        _instructor_client = instructor.from_openai(get_client(), mode=instructor.Mode.JSON)
    return _instructor_client


def extract_structured(
    prompt: str,
    response_model: type[T],
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
    max_retries: int = 2,
) -> T:
    """Call LLM and parse response into a Pydantic model via Instructor."""
    settings = get_settings()
    model = model or settings.llm_model
    client = get_instructor_client()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    result = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        response_model=response_model,
        max_retries=max_retries,
    )
    logger.debug("Structured extraction completed: %s", response_model.__name__)
    return result
