import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main import Date, Person, SessionLocal, candidate_score, ensure_agents, run_date

parser = argparse.ArgumentParser()
parser.add_argument("--fixture", action="store_true")
parser.add_argument("--force", action="store_true")
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main():
    with SessionLocal() as db:
        people = [person for person in db.scalars(select(Person)).all()
                  if person.profile and ((person.source_type == "fixture") == args.fixture)]
        ensure_agents(db)
        processed = 0
        for person in people:
            candidates = sorted((other for other in people if other.id != person.id),
                                key=lambda other: (-candidate_score(person, other), other.id))[:4]
            for candidate in candidates:
                await run_date(db, person, candidate, force=args.force, fixture=args.fixture)
                processed += 1
        print(f"Date candidates processed: {processed}; unique conversations: {db.query(Date).count()}.")


asyncio.run(main())
