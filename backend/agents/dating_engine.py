from __future__ import annotations

from backend.agents.person_agent import PersonAgent


async def run_date(agent_a: PersonAgent, agent_b: PersonAgent, turns: int = 6) -> list[dict[str, str | int]]:
    if turns < 2 or turns > 8:
        raise ValueError("Agent dates must contain between 2 and 8 turns.")
    transcript: list[dict[str, str | int]] = []
    history: list[dict[str, str]] = []
    for index in range(turns):
        agent_index = index % 2
        agent = agent_a if agent_index == 0 else agent_b
        latest = str(transcript[-1]["message"]) if transcript else None
        response = await agent.respond(history=history.copy(), latest_message=latest)
        turn = {"agent_index": agent_index, "message": response.message}
        transcript.append(turn)
        history.append({"speaker": f"Agent {'A' if agent_index == 0 else 'B'}", "message": response.message})
    return transcript
