import argparse
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main import PipelineRequest, SessionLocal, generate_rankings

parser = argparse.ArgumentParser()
parser.add_argument("--fixture", action="store_true")
parser.add_argument("--force", action="store_true")
args = parser.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main():
    with SessionLocal() as db:
        print(await generate_rankings(PipelineRequest(fixture=args.fixture, force=args.force), db))


asyncio.run(main())
