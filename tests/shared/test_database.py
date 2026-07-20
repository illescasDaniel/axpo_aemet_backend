from pathlib import Path

import pytest
from sqlalchemy import text

from meteo_service.shared.database import Database


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
