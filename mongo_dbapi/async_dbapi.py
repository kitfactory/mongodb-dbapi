from __future__ import annotations

import asyncio
from typing import Any, Mapping, Sequence

from .dbapi import Connection, Cursor, connect


class AsyncCursor:
    """Async wrapper for Cursor / Cursor の非同期ラッパー"""

    def __init__(self, sync_cursor: Cursor):
        self._sync_cursor = sync_cursor

    async def execute(self, sql: str, params: Sequence | Mapping | None = None) -> "AsyncCursor":
        await asyncio.to_thread(self._sync_cursor.execute, sql, params)
        return self

    async def executemany(self, sql: str, seq_of_params: Sequence[Sequence | Mapping]) -> "AsyncCursor":
        await asyncio.to_thread(self._sync_cursor.executemany, sql, seq_of_params)
        return self

    async def fetchone(self) -> tuple | None:
        return await asyncio.to_thread(self._sync_cursor.fetchone)

    async def fetchall(self) -> list[tuple]:
        return await asyncio.to_thread(self._sync_cursor.fetchall)

    @property
    def rowcount(self) -> int:
        return self._sync_cursor.rowcount

    @property
    def lastrowid(self) -> Any:
        return self._sync_cursor.lastrowid

    @property
    def description(self):
        return self._sync_cursor.description

    async def close(self) -> None:
        await asyncio.to_thread(self._sync_cursor.close)


class AsyncConnection:
    """Async wrapper for Connection / Connection の非同期ラッパー"""

    def __init__(self, sync_conn: Connection):
        self._sync_conn = sync_conn

    async def cursor(self) -> AsyncCursor:
        cur = await asyncio.to_thread(self._sync_conn.cursor)
        return AsyncCursor(cur)

    async def begin(self) -> None:
        await asyncio.to_thread(self._sync_conn.begin)

    async def commit(self) -> None:
        await asyncio.to_thread(self._sync_conn.commit)

    async def rollback(self) -> None:
        await asyncio.to_thread(self._sync_conn.rollback)

    async def list_tables(self) -> list[str]:
        return await asyncio.to_thread(self._sync_conn.list_tables)

    async def close(self) -> None:
        await asyncio.to_thread(self._sync_conn.close)


async def connect_async(uri: str, db_name: str) -> AsyncConnection:
    """Async factory for Connection / Connection の非同期ファクトリ"""
    sync_conn = await asyncio.to_thread(connect, uri, db_name)
    return AsyncConnection(sync_conn)
