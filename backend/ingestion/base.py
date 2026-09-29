from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field


class ProfileSourceResult(BaseModel):
    source_url: str | None = None
    source_type: str
    platform: str
    status: str
    raw_data: Any = None
    text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ProfileSource(ABC):
    @abstractmethod
    async def fetch_linkedin(self, url: str | None) -> ProfileSourceResult: ...

    @abstractmethod
    async def fetch_instagram(self, url: str | None) -> ProfileSourceResult: ...
