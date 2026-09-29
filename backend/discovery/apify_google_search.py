from __future__ import annotations

import json
import os
from typing import Any

from backend.ingestion.apify_client import run_actor_dataset


class ApifyGoogleSearchSource:
    """Google-search Actor adapter; input JSON comes from the selected Actor schema."""

    def __init__(self, actor_id: str | None = None, api_token: str | None = None,
                 input_template: str | dict[str, Any] | None = None, transport=None):
        self.actor_id = actor_id if actor_id is not None else os.getenv("APIFY_GOOGLE_SEARCH_ACTOR_ID", "")
        self.api_token = api_token if api_token is not None else os.getenv("APIFY_API_TOKEN", "")
        self.input_template = input_template if input_template is not None else os.getenv("APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE", "")
        self.transport = transport

    def _input(self, query: str, limit: int) -> dict[str, Any]:
        if isinstance(self.input_template, str):
            try:
                template = json.loads(self.input_template)
            except json.JSONDecodeError as exc:
                raise ValueError("APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE must be valid JSON from the configured Actor's input schema.") from exc
        else:
            template = self.input_template
        if not isinstance(template, dict) or not template:
            raise ValueError("APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE is required; configure it using the Actor input schema and the {{query}} placeholder.")

        def render(value):
            if isinstance(value, str):
                if value == "{{query}}":
                    return query
                if value == "{{limit}}":
                    return limit
                if "{{limit}}" in value:
                    return value.replace("{{limit}}", str(limit))
                if "{{query}}" in value:
                    return value.replace("{{query}}", query)
                return value
            if isinstance(value, list):
                return [render(item) for item in value]
            if isinstance(value, dict):
                return {key: render(item) for key, item in value.items()}
            return value

        return render(template)

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN is missing.")
        if not self.actor_id:
            raise ValueError("APIFY_GOOGLE_SEARCH_ACTOR_ID is missing.")
        if not query.strip():
            raise ValueError("Search query cannot be empty.")
        actor_input = self._input(query, limit)
        result = await run_actor_dataset(self.actor_id, self.api_token, actor_input, self.transport)
        return result.items[:max(1, limit)]
