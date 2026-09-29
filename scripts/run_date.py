import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main import Person, SessionLocal, run_date
from backend.llm import get_provider

parser = argparse.ArgumentParser(description="Run or refresh a single saved agent date.")
parser.add_argument("--person-a", required=True)
parser.add_argument("--person-b", required=True)
parser.add_argument("--force", action="store_true", help="Replace a cached date with a new conversation")
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main():
    with SessionLocal() as db:
        person_a, person_b = db.get(Person, args.person_a), db.get(Person, args.person_b)
        if not person_a or not person_b:
            raise SystemExit("Both person IDs must exist in the database.")
        if person_a.source_type not in {"public_profile", "public_profile_simulation"} or person_b.source_type not in {"public_profile", "public_profile_simulation"}:
            raise SystemExit("Real Gemini dates require two public_profile records; fixture records always use MockProvider.")
        if not os.getenv("GEMINI_API_KEY"):
            raise SystemExit("Set GEMINI_API_KEY (and optionally GEMINI_MODEL) before running a real LLM date.")
        date = await run_date(db, person_a, person_b, force=args.force, provider=get_provider())
        print(f"Saved date {date.id}: {person_a.name} / {person_b.name}, score {date.compatibility_score:.0f}, LLM Agent Simulation.")


asyncio.run(main())
