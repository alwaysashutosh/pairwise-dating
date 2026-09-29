import argparse
import sys
import logging
from pathlib import Path
from sqlalchemy import select
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from backend.main import Agent, Person, Profile, SessionLocal, ensure_agents, make_agent_prompt
from backend.fixtures import PEOPLE, fixture_profile
from backend.llm import GeminiProvider
import asyncio
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
p = argparse.ArgumentParser(); p.add_argument("--fixture", action="store_true"); p.add_argument("--force", action="store_true"); args = p.parse_args()
with SessionLocal() as db:
    people = [person for person in db.scalars(select(Person)).all()
              if (person.source_type == "fixture") == args.fixture]
    if not args.fixture and people and not __import__("os").getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is required to analyze public profiles; no mock fallback is used.")
    provider = None if args.fixture else GeminiProvider(model=__import__("os").getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    if provider and provider.model != "gemini-2.5-flash":
        raise SystemExit("Public-profile analysis requires GEMINI_MODEL=gemini-2.5-flash.")
    for person in people:
        if person.profile and person.profile.analysis_json and not args.force: continue
        if person.source_type == "fixture":
            index = int(person.id.rsplit("-", 1)[-1]) - 1
            if index < 0 or index >= len(PEOPLE): continue
            data = fixture_profile(index)
            logging.info("PROFILE_ANALYSIS_STARTED source_type=fixture")
            profile = person.profile or Profile(person_id=person.id)
            for key, value in data.items():
                setattr(profile, "profile_summary" if key == "summary" else key, value)
            profile.analysis_json = {**data, "source_type": "fixture", "notice": "Synthetic demo profile; not a real person."}
            logging.info("PROFILE_ANALYSIS_COMPLETED provider=MockProvider")
            profile.raw_linkedin_text = ""; profile.raw_instagram_text = ""
            if person.profile is None: db.add(profile)
        else:
            profile = person.profile or Profile(person_id=person.id)
            if profile.raw_linkedin_text or profile.raw_instagram_text:
                try:
                    logging.info("PROFILE_ANALYSIS_STARTED source_type=public_profile")
                    result = asyncio.run(provider.analyze(profile.raw_linkedin_text, profile.raw_instagram_text))
                    data = result.model_dump()
                    for key, value in data.items(): setattr(profile, "profile_summary" if key == "summary" else key, value)
                    profile.analysis_json = {**data, "source_type": person.source_type,
                                             "simulation_mode": "Public-profile simulation"}
                    profile.raw_linkedin_text = ""
                    profile.raw_instagram_text = ""
                    logging.info("PROFILE_ANALYSIS_COMPLETED provider=%s", provider.__class__.__name__)
                except Exception as exc:
                    profile.profile_summary = "Analysis could not be completed. No profile facts were inferred."
                    profile.analysis_json = {"status": "analysis_failed", "error": str(exc)[:250]}
            else:
                person.ingestion_status = "analysis_unavailable"
                profile.profile_summary = "No permitted public profile content was available. No personal details were inferred."
                profile.analysis_json = {"status": "unavailable"}
            if person.profile is None: db.add(profile)
    db.commit(); ensure_agents(db)
    print(f"Profiles available: {db.query(Profile).count()}; person agents: {db.query(Agent).count()}.")
