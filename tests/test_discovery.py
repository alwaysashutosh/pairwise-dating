import asyncio
import json

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.discovery.apify_google_search import ApifyGoogleSearchSource
from backend.discovery.candidates import CandidateValidator, IdentityMatcher
from backend.discovery.pipeline import run_public_simulation, validate_discovery_configuration
from backend.main import Base, Date, Person, Profile, Ranking
from backend.ingestion.base import ProfileSourceResult
from backend.llm import GeminiProvider


def test_candidate_url_validator_accepts_only_public_profile_routes():
    assert CandidateValidator.canonical_profile_url("https://www.linkedin.com/in/name/?trk=abc", "linkedin") == "https://linkedin.com/in/name"
    assert CandidateValidator.canonical_profile_url("https://linkedin.com/company/acme", "linkedin") is None
    assert CandidateValidator.canonical_profile_url("https://instagram.com/p/abc", "instagram") is None
    assert CandidateValidator.canonical_profile_url("https://instagram.com/person/", "instagram") == "https://instagram.com/person"


def test_identity_match_requires_full_name_and_professional_corroboration():
    name = "Alex Rivera"
    linkedin = "Alex Rivera - Product designer at Acme Labs"
    assert len(IdentityMatcher.match(name, linkedin, "Alex Rivera | Product designer at Acme Labs")) >= 2
    assert not IdentityMatcher.match(name, linkedin, "Alex Rivera | Travel, food, and everyday life")
    assert not IdentityMatcher.match(name, linkedin, "Alex R. | Product designer at Acme Labs")


def test_google_search_adapter_uses_actor_configured_input_template():
    captured = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"data": {"id": "run-1", "status": "SUCCEEDED", "defaultDatasetId": "dataset-1"}})
        return httpx.Response(200, json=[{"url": "https://linkedin.com/in/name", "title": "Name"}])

    async def exercise():
        source = ApifyGoogleSearchSource(actor_id="configured~search", api_token="test-only",
            input_template={"customQueryProperty": "{{query}}", "maximumResults": "{{limit}}"},
            transport=httpx.MockTransport(handler))
        return await source.search('site:linkedin.com/in "designer"', limit=7)

    items = asyncio.run(exercise())
    assert captured == [{"customQueryProperty": 'site:linkedin.com/in "designer"', "maximumResults": 7}]
    assert len(items) == 1


def test_discovery_preflight_names_missing_fields_without_values(monkeypatch):
    for key in ("APIFY_API_TOKEN", "APIFY_GOOGLE_SEARCH_ACTOR_ID", "APIFY_GOOGLE_SEARCH_INPUT_TEMPLATE",
                "APIFY_LINKEDIN_ACTOR_ID", "APIFY_INSTAGRAM_ACTOR_ID", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    missing = validate_discovery_configuration()
    assert "APIFY_GOOGLE_SEARCH_ACTOR_ID" in missing
    assert "GEMINI_API_KEY" in missing


def test_public_discovery_runs_mocked_analysis_agents_and_rankings_without_raw_storage():
    class SearchStub:
        async def search(self, query: str, limit: int = 10):
            if "site:linkedin.com/in" in query:
                return [
                    {"url": "https://www.linkedin.com/in/alex-rivera", "title": "Alex Rivera - Product designer at Acme Labs | LinkedIn", "snippet": "Product designer at Acme Labs"},
                    {"url": "https://www.linkedin.com/in/sam-lee", "title": "Sam Lee - Data scientist at Northwind Studio | LinkedIn", "snippet": "Data scientist at Northwind Studio"},
                ]
            if "Alex Rivera" in query:
                return [{"url": "https://www.instagram.com/alexrivera", "title": "Alex Rivera | Instagram", "snippet": "Product designer at Acme Labs"}]
            return [{"url": "https://www.instagram.com/samlee", "title": "Sam Lee | Instagram", "snippet": "Data scientist at Northwind Studio"}]

    class SourceStub:
        async def fetch_linkedin(self, url):
            return ProfileSourceResult(source_url=url, source_type="apify", platform="linkedin", status="success",
                raw_data=[{"headline": "Product designer"}], text="Product designer at Acme Labs. Interests include books and design.")

        async def fetch_instagram(self, url):
            return ProfileSourceResult(source_url=url, source_type="apify", platform="instagram", status="success",
                raw_data=[{"bio": "Public profile"}], text="Public profile mentions design and reading.")

    def gemini_handler(request: httpx.Request) -> httpx.Response:
        prompt = json.loads(request.content)["contents"][0]["parts"][0]["text"]
        if prompt.startswith("Extract"):
            result = {"profession": "Designer", "education": None, "interests": ["books", "design"],
                "hobbies": ["reading"], "lifestyle": [], "conversation_topics": ["design"],
                "preferences": [], "summary": "Public profile lists design and books."}
        elif prompt.startswith("You are an AI compatibility simulation"):
            result = {"message": "As an AI profile simulation, what interests you about design?"}
        else:
            result = {"shared_interests": 75, "lifestyle": 70, "conversation": 80, "goals": 60,
                "strengths": ["The simulated exchange discussed design."], "differences": [],
                "reason": "Based only on this generated exchange."}
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(result)}]}}]})

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    provider = GeminiProvider(api_key="test-only-key", model="gemini-2.5-flash", transport=httpx.MockTransport(gemini_handler))
    with Session() as db:
        outcome = asyncio.run(run_public_simulation(db, limit=2, search_source=SearchStub(), source=SourceStub(), provider=provider))
        assert outcome["discovered"] == 2 and outcome["analyzed"] == 2
        assert db.query(Person).filter_by(source_type="public_profile_simulation").count() == 2
        assert db.query(Date).count() == 1 and db.query(Ranking).count() == 2
        assert db.query(Profile).filter(Profile.raw_linkedin_text != "").count() == 0
        profile = db.query(Profile).first()
        assert "raw_data" not in json.dumps(profile.source_data_json)
        assert profile.analysis_json["simulation_mode"] == "Public-profile simulation"
    engine.dispose()
