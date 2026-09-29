from __future__ import annotations

from typing import Any
from .base import ProfileSourceResult


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return " ".join(filter(None, (_text(item) for item in value)))
    if isinstance(value, dict):
        return " ".join(f"{key}: {_text(item)}" for key, item in value.items() if item is not None)
    return ""


def normalize_apify_item(item: dict[str, Any]) -> str:
    preferred = ("text", "description", "about", "bio", "summary", "headline", "title",
                 "experience", "education", "interests", "posts", "caption", "content")
    chunks = [_text(item[key]) for key in preferred if item.get(key) is not None]
    if not chunks:
        chunks = [_text(value) for value in item.values() if isinstance(value, (str, list, dict))]
    return " ".join(dict.fromkeys(chunk.strip() for chunk in chunks if chunk.strip()))[:12000]


def normalize_sources(linkedin: ProfileSourceResult, instagram: ProfileSourceResult) -> dict[str, Any]:
    return {"linkedin": linkedin.model_dump(mode="json"), "instagram": instagram.model_dump(mode="json"),
            "linkedin_text": linkedin.text[:12000], "instagram_text": instagram.text[:12000]}
