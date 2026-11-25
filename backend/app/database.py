"""Async SQLite engine and schema definitions."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    event,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

metadata = MetaData()

sessions_table = Table(
    "sessions",
    metadata,
    Column("session_id", String(128), primary_key=True),
    Column("system_prompt", Text, nullable=True),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
)

messages_table = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "session_id",
        String(128),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("role", String(16), nullable=False),
    Column("content", Text, nullable=False),
    Column("metadata", Text, nullable=True),
    Column("created_at", String(40), nullable=False),
)

Index("ix_messages_session_id_id", messages_table.c.session_id, messages_table.c.id)


def normalize_sqlite_url(url: str) -> str:
    """Return an async-driver SQLite URL while honoring the documented format."""

    if url.startswith("sqlite+aiosqlite://"):
        return url
    if url.startswith("sqlite://"):
        return "sqlite+aiosqlite://" + url[len("sqlite://") :]
    raise ValueError("Only SQLite database URLs are supported")


class Database:
    """Owns the async engine, sessions and connection-level SQLite tuning."""

    def __init__(self, url: str) -> None:
        self.url = normalize_sqlite_url(url)
        self.engine: AsyncEngine = create_async_engine(
            self.url,
            pool_pre_ping=True,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
        )

        @event.listens_for(self.engine.sync_engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
            finally:
                cursor.close()

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(metadata.create_all)

    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        await self.engine.dispose()
