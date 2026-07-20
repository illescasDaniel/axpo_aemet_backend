from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Self

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _configure_sqlite(engine: AsyncEngine) -> None:
    def _set_pragmas(dbapi_connection: Any, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    event.listen(engine.sync_engine, "connect", _set_pragmas)


class Database:
    def __init__(self, database_url: str):
        self._database_url = database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def __aenter__(self) -> Self:
        self._engine = create_async_engine(
            self._database_url,
            connect_args={"check_same_thread": False},
        )
        _configure_sqlite(self._engine)
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

        import meteo_service.observations.adapters.database.orm_models  # noqa: F401  # pyright: ignore[reportUnusedImport]

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._engine is not None:
            await self._engine.dispose()
        self._engine = None
        self._session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if self._session_factory is None:
            raise RuntimeError("Database is not initialized")

        async with self._session_factory() as session:
            yield session
