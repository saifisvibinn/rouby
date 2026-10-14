import argparse
import asyncio

from app.core.db import AsyncSessionLocal
from app.seed.runner import seed_all


async def _seed() -> None:
    async with AsyncSessionLocal() as session:
        await seed_all(session)
    print("Seed complete.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="rouby")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="Load demo branch, roles, users, settings")
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(_seed())


if __name__ == "__main__":
    main()
