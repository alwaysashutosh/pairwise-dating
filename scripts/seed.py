import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main import Person, SessionLocal
from backend.fixtures import PEOPLE

parser = argparse.ArgumentParser()
parser.add_argument("--fixture", action="store_true", help="Load 25 clearly synthetic demo profiles")
args = parser.parse_args()
csv_path = ROOT / "data" / "people.csv"
if not args.fixture and not csv_path.exists():
    raise SystemExit("No data/people.csv found. It is optional: run public discovery with python scripts/discover_people.py --limit 2, or load the fixture cohort with python scripts/seed.py --fixture.")
rows = [{"id": f"demo-{i+1:02}", "name": person[0], "linkedin_url": "", "instagram_url": "", "source_type": "fixture"} for i, person in enumerate(PEOPLE)] if args.fixture else list(csv.DictReader(csv_path.open(encoding="utf-8-sig", newline="")))
if not args.fixture and len(rows) < 2:
    raise SystemExit(f"data/people.csv has {len(rows)} rows; provide two public-profile records to run a pair simulation.")
with SessionLocal() as db:
    inserted = 0
    for row in rows:
        pid = (row.get("id") or "").strip()
        name = (row.get("name") or "").strip()
        if not pid or not name:
            continue
        person = db.get(Person, pid)
        if person is None:
            db.add(Person(id=pid, name=name, linkedin_url=row.get("linkedin_url") or None,
                          instagram_url=row.get("instagram_url") or None,
                          source_type="fixture" if args.fixture else "public_profile"))
            inserted += 1
    db.commit()
print(f"Loaded {len(rows)} {'synthetic fixture' if args.fixture else 'CSV'} rows; inserted {inserted} new people.")
