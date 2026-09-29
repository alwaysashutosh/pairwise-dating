import argparse, asyncio, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from sqlalchemy import select
from backend.main import Person, SessionLocal
from backend.ingestion.apify_source import ApifySource
from backend.ingestion.fixture_source import FixtureSource
from backend.ingestion.normalizer import normalize_sources
from backend.ingestion.playwright_source import PlaywrightSource
parser=argparse.ArgumentParser(); parser.add_argument("--fixture",action="store_true"); parser.add_argument("--force",action="store_true"); args=parser.parse_args()
async def run():
    import os
    source = PlaywrightSource() if os.getenv("PROFILE_SOURCE", "apify").lower() == "playwright" else ApifySource()
    with SessionLocal() as db:
        for person in db.scalars(select(Person)).all():
            from backend.main import Profile
            if person.source_type == "fixture":
                FixtureSource()
                person.ingestion_status="fixture"
                continue
            if person.profile and person.profile.source_data_json and not args.force: continue
            linkedin, instagram = await source.fetch_linkedin(person.linkedin_url), await source.fetch_instagram(person.instagram_url)
            results = normalize_sources(linkedin, instagram)
            good = [item for item in (linkedin, instagram) if item.status == "success"]
            errors = [item.error for item in (linkedin, instagram) if item.error]
            person.ingestion_status = "success" if len(good) == 2 else "partial" if good else "failed"
            profile=person.profile or Profile(person_id=person.id)
            profile.raw_linkedin_text=results["linkedin_text"]; profile.raw_instagram_text=results["instagram_text"]
            keep_fields = ("source_url", "source_type", "platform", "status", "metadata", "error")
            profile.source_data_json = {
                platform: {key: results[platform][key] for key in keep_fields}
                for platform in ("linkedin", "instagram")
            }
            if person.profile is None: db.add(profile)
            if errors: print(f"{person.id}: {'; '.join(errors)}")
        db.commit(); print(f"Ingestion status updated for {db.query(Person).count()} people.")
asyncio.run(run())
