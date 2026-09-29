from __future__ import annotations

from dataclasses import dataclass
import asyncio
from urllib.parse import quote

import httpx


@dataclass
class ActorDataset:
    run_id: str
    dataset_id: str
    items: list[dict]


async def run_actor_dataset(actor_id: str, token: str, actor_input: dict,
                            transport: httpx.AsyncBaseTransport | None = None) -> ActorDataset:
    """Run an Actor through Apify's official REST API and fetch its dataset."""
    actor = quote(actor_id, safe="~")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=90, transport=transport) as client:
        response = await client.post(f"https://api.apify.com/v2/acts/{actor}/runs",
            params={"waitForFinish": 60}, headers=headers, json=actor_input)
        if response.is_error:
            raise RuntimeError(f"Apify Actor run failed with HTTP {response.status_code}.")
        run_data = response.json().get("data", {})
        run_id = run_data.get("id")
        status = run_data.get("status")
        for _ in range(4):
            if status in {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}:
                break
            if not run_id:
                break
            await asyncio.sleep(0.5)
            poll = await client.get(f"https://api.apify.com/v2/actor-runs/{quote(str(run_id), safe='')}",
                params={"waitForFinish": 60}, headers=headers)
            if poll.is_error:
                raise RuntimeError(f"Apify run status request failed with HTTP {poll.status_code}.")
            run_data = poll.json().get("data", {})
            status = run_data.get("status")
        if status != "SUCCEEDED":
            raise RuntimeError(f"Apify Actor run did not succeed (status: {status or 'unknown'}).")
        dataset_id = run_data.get("defaultDatasetId")
        if not dataset_id:
            raise RuntimeError("Apify Actor run returned no default dataset.")
        items_response = await client.get(f"https://api.apify.com/v2/datasets/{quote(str(dataset_id), safe='')}/items",
            params={"clean": "true", "format": "json", "limit": 1000}, headers=headers)
        if items_response.is_error:
            raise RuntimeError(f"Apify dataset request failed with HTTP {items_response.status_code}.")
        items = items_response.json()
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            raise RuntimeError("Apify dataset returned an unsupported result format.")
        return ActorDataset(str(run_id or ""), str(dataset_id), [item for item in items if isinstance(item, dict)])
