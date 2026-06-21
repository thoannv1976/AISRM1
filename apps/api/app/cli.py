"""Command-line entrypoint: migrations and seeding.

Usage:
    python -m app.cli migrate
    python -m app.cli seed [--demo]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine


def ensure_extensions() -> None:
    with engine.connect() as conn:
        for ext in ("vector", "unaccent", "pg_trgm"):
            conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {ext}"))
        conn.commit()


def _alembic_config():
    from alembic.config import Config

    here = Path(__file__).resolve().parent.parent  # apps/api
    cfg = Config(str(here / "alembic.ini"))
    cfg.set_main_option("script_location", str(here / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def migrate() -> None:
    """Apply migrations (Alembic). Falls back to create_all if no versions exist."""
    ensure_extensions()
    here = Path(__file__).resolve().parent.parent
    versions = list((here / "alembic" / "versions").glob("*.py"))
    if versions:
        from alembic import command

        command.upgrade(_alembic_config(), "head")
        print(f"[migrate] Alembic upgrade head applied ({len(versions)} revision file(s)).")
    else:
        import app.models  # noqa: F401  ensure metadata populated
        from app.models import Base

        Base.metadata.create_all(engine)
        print("[migrate] No Alembic versions found — created schema via metadata.create_all.")


def seed(demo: bool) -> None:
    from app.seed import seed_all

    seed_all(demo=demo)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aisrm1")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate", help="Run DB migrations")
    sp_seed = sub.add_parser("seed", help="Seed data")
    sp_seed.add_argument("--demo", action="store_true", help="Load rich demo dataset")

    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        migrate()
    elif args.cmd == "seed":
        seed(demo=args.demo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
