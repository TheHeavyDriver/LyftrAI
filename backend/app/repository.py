"""SQLite persistence for sessions and messages.

The rest of the application never sees SQL. Assistant metadata is stored as a
JSON string exactly as the assignment schema describes, while the API layer
decides its public shape.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert, select, update

from .database import Database, messages_table, sessions_table


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: str
    system_prompt: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class MessageRecord:
    id: int
    role: str
    content: str
    metadata_json: str | None


class SessionRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def ping(self) -> None:
        await self._database.ping()

    async def get_session(self, session_id: str) -> SessionRecord | None:
        async with self._database.engine.connect() as connection:
            row = (
                await connection.execute(
                    select(sessions_table).where(
                        sessions_table.c.session_id == session_id
                    )
                )
            ).mappings().first()

        if row is None:
            return None

        return SessionRecord(
            session_id=row["session_id"],
            system_prompt=row["system_prompt"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_messages(self, session_id: str) -> list[MessageRecord]:
        async with self._database.engine.connect() as connection:
            rows = (
                await connection.execute(
                    select(messages_table)
                    .where(messages_table.c.session_id == session_id)
                    .order_by(messages_table.c.id.asc())
                )
            ).mappings().all()

        return [
            MessageRecord(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                metadata_json=row["metadata"],
            )
            for row in rows
        ]

    async def save_exchange(
        self,
        *,
        session_id: str,
        system_prompt: str,
        user_content: str,
        assistant_content: str,
        assistant_metadata: dict[str, Any],
    ) -> None:
        """Persist a full turn atomically.

        A session row is created only by the first successful exchange. A
        failed request never reaches this method, so storage reflects only
        completed turns.
        """

        now = utc_now_iso()
        metadata_json = json.dumps(
            assistant_metadata, ensure_ascii=False, separators=(",", ":")
        )

        async with self._database.session_factory() as session:
            async with session.begin():
                exists = (
                    await session.execute(
                        select(sessions_table.c.session_id).where(
                            sessions_table.c.session_id == session_id
                        )
                    )
                ).scalar_one_or_none()

                if exists is None:
                    await session.execute(
                        insert(sessions_table).values(
                            session_id=session_id,
                            system_prompt=system_prompt,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                else:
                    await session.execute(
                        update(sessions_table)
                        .where(sessions_table.c.session_id == session_id)
                        .values(system_prompt=system_prompt, updated_at=now)
                    )

                await session.execute(
                    insert(messages_table),
                    [
                        {
                            "session_id": session_id,
                            "role": "user",
                            "content": user_content,
                            "metadata": None,
                            "created_at": now,
                        },
                        {
                            "session_id": session_id,
                            "role": "assistant",
                            "content": assistant_content,
                            "metadata": metadata_json,
                            "created_at": now,
                        },
                    ],
                )
