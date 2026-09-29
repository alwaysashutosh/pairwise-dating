from __future__ import annotations

from .base import ProfileSource, ProfileSourceResult


class FixtureSource(ProfileSource):
    async def _fetch(self, platform: str, url: str | None) -> ProfileSourceResult:
        return ProfileSourceResult(source_url=url, source_type="fixture", platform=platform,
            status="fixture", metadata={"notice": "Synthetic demo source; not a real person."})

    async def fetch_linkedin(self, url: str | None) -> ProfileSourceResult:
        return await self._fetch("linkedin", url)

    async def fetch_instagram(self, url: str | None) -> ProfileSourceResult:
        return await self._fetch("instagram", url)
