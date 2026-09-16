"""Safe migration bootstrap for the ai_agent-owned schema."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.dsn import get_database_url


LEGACY_VERSION_TABLE = "alembic_version"
VERSION_TABLE = "ai_agent_alembic_version"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _can_adopt_legacy_revisions(
    legacy_revisions: set[str], known_revisions: set[str]
) -> bool:
    """Only adopt a legacy table when every stored revision belongs to ai_agent."""
    return bool(legacy_revisions) and legacy_revisions <= known_revisions


def _known_revisions() -> set[str]:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    return {revision.revision for revision in script.walk_revisions()}


async def adopt_legacy_version_table() -> None:
    """Copy only an unambiguous old ai_agent Alembic state into its own table.

    The old generic table remains untouched deliberately: it may be needed by a
    prior deployment while the service is being upgraded.  An unknown revision
    is a hard stop rather than guessing and potentially overwriting another
    service's migration state.
    """
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            own_exists = await connection.scalar(
                text("SELECT to_regclass(:table_name)"),
                {"table_name": f"public.{VERSION_TABLE}"},
            )
            if own_exists:
                return

            legacy_exists = await connection.scalar(
                text("SELECT to_regclass(:table_name)"),
                {"table_name": f"public.{LEGACY_VERSION_TABLE}"},
            )
            if not legacy_exists:
                return

            rows = await connection.execute(
                text(f'SELECT version_num FROM "{LEGACY_VERSION_TABLE}"')
            )
            legacy_revisions = {row[0] for row in rows}
            if not _can_adopt_legacy_revisions(legacy_revisions, _known_revisions()):
                raise RuntimeError(
                    "Legacy alembic_version does not unambiguously belong to ai_agent; "
                    "stop migration and resolve the database state manually."
                )

            await connection.execute(
                text(
                    f'CREATE TABLE "{VERSION_TABLE}" '
                    "(version_num VARCHAR(32) NOT NULL)"
                )
            )
            for revision in legacy_revisions:
                await connection.execute(
                    text(f'INSERT INTO "{VERSION_TABLE}" (version_num) VALUES (:revision)'),
                    {"revision": revision},
                )
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(adopt_legacy_version_table())


if __name__ == "__main__":
    main()
