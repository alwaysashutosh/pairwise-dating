from __future__ import annotations

from backend.sources import fetch_public_page
from .base import ProfileSource, ProfileSourceResult


class PlaywrightSource(ProfileSource):
    async def _fetch(self, platform: str, url: str | None) -> ProfileSourceResult:
        value = await fetch_public_page(url)
        return ProfileSourceResult(source_url=url, source_type="playwright", platform=platform,
            status=value["status"], raw_data=None, text=value.get("text", ""),
            metadata=value.get("metadata", {}), error=value.get("error"))

    async def fetch_linkedin(self, url: str | None) -> ProfileSourceResult:
        return await self._fetch("linkedin", url)

    async def fetch_instagram(self, url: str | None) -> ProfileSourceResult:
        return await self._fetch("instagram", url)
