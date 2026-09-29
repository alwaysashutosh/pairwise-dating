from __future__ import annotations

from backend.llm import AgentTurn, LLMProvider, NormalizedProfile


class PersonAgent:
    """A simulated representative whose only private context is its normalized profile."""

    def __init__(self, profile: NormalizedProfile, provider: LLMProvider):
        self.profile = profile
        self.provider = provider

    async def respond(self, history: list[dict[str, str]], latest_message: str | None) -> AgentTurn:
        return await self.provider.generate_message(self.profile, history, latest_message)
