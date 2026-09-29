import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from backend.discovery.pipeline import run_public_simulation, validate_discovery_configuration
from backend.main import SessionLocal


def parser_args():
    parser = argparse.ArgumentParser(description="Discover and run a public-profile AI compatibility simulation.")
    parser.add_argument("--limit", type=int, default=25, help="Validated public profiles to discover (1-25).")
    parser.add_argument("--force", action="store_true", help="Refresh cached public acquisition, analysis, dates and rankings.")
    return parser.parse_args()


async def main(limit: int, force: bool) -> int:
    if not 1 <= limit <= 25:
        print("Discovery limit must be between 1 and 25.")
        return 2
    missing = validate_discovery_configuration()
    if missing:
        print("Public-profile simulation is not configured. Missing/invalid: " + ", ".join(missing))
        print("No Apify or Gemini requests were made.")
        return 2
    try:
        with SessionLocal() as db:
            result = await run_public_simulation(db, limit=limit, force=force)
    except Exception as exc:
        print(f"Public-profile simulation stopped ({type(exc).__name__}). No fallback provider was used.")
        return 1
    for key, value in result.items():
        print(f"{key}: {value}")
    if result["discovered"] < limit:
        print(f"Validated {result['discovered']} of {limit} requested profiles; no records were fabricated.")
    return 0


if __name__ == "__main__":
    args = parser_args()
    raise SystemExit(asyncio.run(main(args.limit, args.force)))
