import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.agents.compatibility import weighted_score
from backend.agents.dating_engine import run_date
from backend.agents.person_agent import PersonAgent
from backend.llm import (AgentTurn, CompatibilityEvaluation, GeminiProvider, MockProvider,
                         NormalizedProfile, ProfileAnalysis)
from backend.ingestion.apify_source import ApifySource
from backend.ingestion.fixture_source import FixtureSource
from backend.main import Agent, Base, Person, Profile, app, get_db, person_json


def sample_profile(**changes) -> NormalizedProfile:
    data = {"profession": "Designer", "education": None, "interests": ["books", "music"],
            "hobbies": ["reading"], "lifestyle": ["city walks"], "conversation_topics": ["books"],
            "preferences": ["curious conversation"], "summary": "Enjoys design and books."}
    data.update(changes)
    return NormalizedProfile(**data)


def test_gemini_provider_uses_env_and_structured_requests(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen.append((request, payload))
        prompt = payload["contents"][0]["parts"][0]["text"]
        if prompt.startswith("Extract"):
            result = {"profession": "Designer", "education": None, "interests": ["books"], "hobbies": [],
                      "lifestyle": [], "conversation_topics": ["books"], "preferences": [], "summary": "Publicly listed designer."}
        elif prompt.startswith("You are an AI compatibility simulation"):
            result = {"message": "What do you enjoy reading?"}
        else:
            result = {"shared_interests": 80, "lifestyle": 70, "conversation": 90, "goals": 60,
                      "strengths": ["Shared reading interest"], "differences": [], "reason": "The transcript showed curiosity."}
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(result)}]}}]})

    async def exercise():
        provider = GeminiProvider(transport=httpx.MockTransport(handler))
        profile = await provider.analyze("public profile", "")
        turn = await provider.generate_message(sample_profile(), [], None)
        evaluation = await provider.evaluate_compatibility(sample_profile(), sample_profile(), [{"speaker": "Agent A", "message": "Hello"}])
        return provider, profile, turn, evaluation

    provider, profile, turn, evaluation = asyncio.run(exercise())
    assert provider.model == "test-model"
    assert profile.profession == "Designer"
    assert turn.message == "What do you enjoy reading?"
    assert evaluation.shared_interests == 80
    assert all(req.headers["x-goog-api-key"] == "test-only-key" for req, _ in seen)
    assert all(payload["generationConfig"]["responseFormat"]["text"]["mimeType"] == "application/json" for _, payload in seen)
    assert all("schema" in payload["generationConfig"]["responseFormat"]["text"] for _, payload in seen)


def test_gemini_provider_retries_invalid_json_without_mocking():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "not json"}]}}]})

    provider = GeminiProvider(api_key="test-only-key", model="test-model", transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        asyncio.run(provider.analyze("public text", ""))
    assert attempts == 3


def test_mock_provider_keeps_offline_profile_grounding():
    async def exercise():
        provider = MockProvider()
        turn = await provider.generate_message(sample_profile(), [], None)
        analysis = await provider.analyze("ignored", "ignored")
        return provider, turn, analysis

    provider, turn, analysis = asyncio.run(exercise())
    assert provider.simulation_mode == "Demo Simulation"
    assert "books" in turn.message
    assert analysis.interests == []


def test_person_agent_only_passes_its_normalized_profile():
    class SpyProvider(MockProvider):
        received = None

        async def generate_message(self, profile, history, latest_message):
            self.received = profile
            return AgentTurn(message="I can only speak from this profile.")

    provider = SpyProvider()
    own_profile = sample_profile()
    agent = PersonAgent(own_profile, provider)
    result = asyncio.run(agent.respond([], None))
    assert result.message.startswith("I can only speak")
    assert provider.received is own_profile
    assert not hasattr(provider.received, "raw_linkedin_text")


def test_dating_engine_uses_turn_history_and_latest_other_message():
    class ScriptedProvider(MockProvider):
        calls = []

        async def generate_message(self, profile, history, latest_message):
            self.calls.append((profile, list(history), latest_message))
            return AgentTurn(message=f"Reply {len(self.calls)}")

    provider = ScriptedProvider()
    a, b = PersonAgent(sample_profile(), provider), PersonAgent(sample_profile(interests=["hiking"]), provider)
    transcript = asyncio.run(run_date(a, b, turns=6))
    assert len(transcript) == 6
    assert [turn["agent_index"] for turn in transcript] == [0, 1, 0, 1, 0, 1]
    assert provider.calls[1][2] == "Reply 1"
    assert len(provider.calls[5][1]) == 5


def test_compatibility_schema_and_python_weighted_score():
    result = CompatibilityEvaluation(shared_interests=100, lifestyle=80, conversation=60, goals=40,
                                     strengths=["Curiosity"], differences=[], reason="Balanced exchange.")
    assert weighted_score(result) == 73
    with pytest.raises(ValueError):
        CompatibilityEvaluation(shared_interests=101, lifestyle=80, conversation=60, goals=40,
                                 strengths=[], differences=[], reason="Out of range")


def test_fixture_date_api_returns_compatibility_and_simulation_label():
    database = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(database)
    TestSession = sessionmaker(bind=database, expire_on_commit=False)

    def override_db():
        with TestSession() as session:
            yield session

    with TestSession() as session:
        for person_id, interest in (("api-a", "books"), ("api-b", "books")):
            person = Person(id=person_id, name=person_id, source_type="fixture",
                            profile=Profile(person_id=person_id, profession="Designer", interests=[interest],
                                hobbies=["reading"], lifestyle=["city walks"], conversation_topics=[interest],
                                preferences=[], profile_summary="Synthetic fixture."))
            person.agent = Agent(person_id=person_id, system_prompt="Fixture agent")
            session.add(person)
        session.commit()
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        created = client.post("/api/dates", json={"person_a_id": "api-a", "person_b_id": "api-b"})
        assert created.status_code == 200
        refreshed = client.post("/api/dates", json={"person_a_id": "api-a", "person_b_id": "api-b", "force": True})
        assert refreshed.status_code == 200
        assert refreshed.json()["id"] == created.json()["id"]
        date = client.get(f"/api/dates/{created.json()['id']}")
        assert date.status_code == 200
        body = date.json()
        assert len(body["messages"]) == 6
        assert body["compatibility"]["simulation_mode"] == "Fixture Mode · Demo Simulation"
        activity = client.get(f"/api/dates/{created.json()['id']}/activity").json()["activity"]
        assert len(activity) == 8 and activity[-1]["event"] == "compatibility_completed"
        dimensions = body["compatibility"]["dimensions"]
        expected = round(.30 * dimensions["shared_interests"] + .25 * dimensions["lifestyle"] +
                         .25 * dimensions["conversation"] + .20 * dimensions["goals"])
        assert body["compatibility"]["overall_score"] == expected
        with TestSession() as session:
            real = Person(id="api-public", name="Public Profile", source_type="public_profile_simulation",
                profile=Profile(person_id="api-public", interests=["books"], profile_summary="Simulation"))
            real.agent = Agent(person_id="api-public", system_prompt="AI simulation")
            session.add(real)
            session.commit()
        mixed = client.post("/api/dates", json={"person_a_id": "api-a", "person_b_id": "api-public"})
        assert mixed.status_code == 409
        assert "cannot be mixed" in mixed.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)
        database.dispose()


def test_profile_analysis_schema_and_similarity():
    analyzed = ProfileAnalysis.model_validate({"profession": "Designer", "summary": "Works in design."})
    assert analyzed.profession == "Designer"
    assert analyzed.interests == []
    assert analyzed.education is None
    assert sample_profile().interests


def test_csv_public_profiles_receive_simulation_disclaimer():
    person = Person(id="csv-public", name="Public Profile", source_type="public_profile")
    result = person_json(person)
    assert result["simulation_mode"] == "Public-profile simulation"
    assert "not represented as a participant or endorser" in result["simulation_notice"]


def test_apify_source_uses_official_api_and_normalizes_dataset():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.host == "api.apify.com"
            assert request.headers["Authorization"] == "Bearer test-token"
            return httpx.Response(200, json={"data": {"status": "SUCCEEDED", "defaultDatasetId": "dataset-1"}})
        return httpx.Response(200, json=[{"name": "Ada", "headline": "Designer", "about": "Enjoys pottery"}])

    async def exercise():
        source = ApifySource(api_token="test-token", linkedin_actor_id="actor~profile", transport=httpx.MockTransport(handler))
        return await source.fetch_linkedin("https://www.linkedin.com/in/example")

    result = asyncio.run(exercise())
    assert result.status == "success" and "Designer" in result.text and "pottery" in result.text
    assert result.raw_data[0]["name"] == "Ada"


def test_apify_source_missing_configuration_is_recorded():
    result = asyncio.run(ApifySource(api_token="", linkedin_actor_id="").fetch_linkedin("https://www.linkedin.com/in/example"))
    assert result.status == "unavailable" and "APIFY_API_TOKEN" in result.error


def test_fixture_source_does_not_claim_real_profile_data():
    result = asyncio.run(FixtureSource().fetch_instagram(None))
    assert result.status == "fixture" and result.raw_data is None and result.text == ""
