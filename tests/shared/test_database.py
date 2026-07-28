from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text

from meteo_service.shared.database import Base, Database


pytestmark = pytest.mark.unit


async def test_given_file_sqlite_when_database_opens_then_wal_and_busy_timeout_enabled(tmp_path: Path):
    # given
    db_path = tmp_path / "meteo.sqlite"
    database_url = f"sqlite+aiosqlite:///{db_path}"

    # when
    async with Database(database_url) as db:
        async with db.session() as session:
            journal_mode = (await session.execute(text("PRAGMA journal_mode"))).scalar_one()
            busy_timeout = (await session.execute(text("PRAGMA busy_timeout"))).scalar_one()

    # then
    assert journal_mode == "wal"
    assert busy_timeout == 5000


async def test_given_create_all_fails_when_database_opens_then_engine_is_cleaned_up(tmp_path: Path):
    # given
    db_path = tmp_path / "meteo.sqlite"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    db = Database(database_url)

    # when/then
    with patch.object(Base.metadata, "create_all", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="boom"):
            await db.__aenter__()

    assert db._engine is None  # pyright: ignore[reportPrivateUsage]
    assert db._session_factory is None  # pyright: ignore[reportPrivateUsage]
