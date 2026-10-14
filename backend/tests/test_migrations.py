"""Ensure Alembic upgrade/downgrade one step works against Postgres test DB."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND = Path(__file__).resolve().parents[1]


async def _reset_test_schema(database_url: str) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
    await engine.dispose()


@pytest.mark.integration
def test_alembic_upgrade_and_downgrade_one_step() -> None:
    from app.core.settings import get_settings

    settings = get_settings()
    asyncio.run(_reset_test_schema(settings.test_database_url))

    env = {
        **os.environ,
        "DATABASE_URL": settings.test_database_url,
    }
    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if upgrade.returncode != 0 and "Connection refused" in (upgrade.stderr + upgrade.stdout):
        pytest.skip("Postgres not available")
    assert upgrade.returncode == 0, upgrade.stderr + upgrade.stdout

    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "-1"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert downgrade.returncode == 0, downgrade.stderr + downgrade.stdout

    restore = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert restore.returncode == 0, restore.stderr + restore.stdout

    # Re-seed so later tests still find their data
    async def _reseed() -> None:
        from app.seed.runner import seed_all as _seed

        engine = create_async_engine(settings.test_database_url)
        async with engine.begin() as conn:
            from sqlalchemy.ext.asyncio import AsyncSession

            session = AsyncSession(bind=conn)
            await _seed(session)
            await session.flush()
        await engine.dispose()

    asyncio.run(_reseed())
