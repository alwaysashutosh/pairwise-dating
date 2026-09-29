from __future__ import annotations

import os
from urllib.parse import quote
from urllib.parse import urlparse
import httpx
from .apify_client import run_actor_dataset
from .base import ProfileSource, ProfileSourceResult
from .normalizer import normalize_apify_item


class ApifySource(ProfileSource):
    """Calls the official Apify API; Actor-specific input stays in this adapter."""

    def __init__(self, api_token: str | None = None, linkedin_actor_id: str | None = None,
                 instagram_actor_id: str | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.api_token = api_token if api_token is not None else os.getenv("APIFY_API_TOKEN", "")
        self.actors = {"linkedin": linkedin_actor_id if linkedin_actor_id is not None else os.getenv("APIFY_LINKEDIN_ACTOR_ID", ""),
                       "instagram": instagram_actor_id if instagram_actor_id is not None else os.getenv("APIFY_INSTAGRAM_ACTOR_ID", "")}
        self.url_fields = {"linkedin": os.getenv("APIFY_LINKEDIN_URL_FIELD", "startUrls"),
                           "instagram": os.getenv("APIFY_INSTAGRAM_URL_FIELD", "startUrls")}
        self.transport = transport

    async def _fetch(self, platform: str, url: str | None) -> ProfileSourceResult:
        result = dict(source_url=url, source_type="apify", platform=platform, status="unavailable", raw_data=None, text="", metadata={})
        if not url:
            return ProfileSourceResult(**result, error="No profile URL supplied.")
        parsed = urlparse(url)
        allowed_host = "linkedin.com" if platform == "linkedin" else "instagram.com"
        if parsed.scheme != "https" or not parsed.hostname or not (parsed.hostname == allowed_host or parsed.hostname.endswith("." + allowed_host)):
            return ProfileSourceResult(**{**result, "status": "failed"}, error=f"Only HTTPS public {platform} profile URLs are accepted.")
        if not self.api_token:
            return ProfileSourceResult(**result, error="APIFY_API_TOKEN is not configured.")
        actor = self.actors[platform]
        if not actor:
            return ProfileSourceResult(**result, error=f"APIFY_{platform.upper()}_ACTOR_ID is not configured.")
        try:
            output = await run_actor_dataset(actor, self.api_token,
                {self.url_fields[platform]: [{"url": url}]}, self.transport)
            data = output.items
            text = "\n".join(filter(None, (normalize_apify_item(item) for item in data)))[:12000]
            if not text:
                return ProfileSourceResult(**{**result, "status": "empty", "metadata": {"actor_id": actor}}, error="No usable public profile content was returned.")
            return ProfileSourceResult(**{**result, "status": "success", "raw_data": data, "text": text,
                "metadata": {"actor_id": actor, "dataset_id": output.dataset_id, "item_count": len(data)}})
        except (httpx.HTTPError, ValueError, KeyError, RuntimeError) as exc:
            return ProfileSourceResult(**{**result, "status": "failed"}, error=f"Apify request failed: {str(exc)[:300]}")

    async def fetch_linkedin(self, url: str | None) -> ProfileSourceResult:
        return await self._fetch("linkedin", url)

    async def fetch_instagram(self, url: str | None) -> ProfileSourceResult:
        return await self._fetch("instagram", url)
