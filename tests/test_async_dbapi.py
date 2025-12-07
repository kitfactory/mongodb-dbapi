import asyncio
import os

import pytest

from mongo_dbapi import MongoDbApiError
from mongo_dbapi.async_dbapi import connect_async


MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27018")
MONGODB_DB = os.environ.get("MONGODB_DB", "mongo_dbapi_test")


def test_async_crud_roundtrip():
    async def _run():
        conn = await connect_async(MONGODB_URI, MONGODB_DB)
        cur = await conn.cursor()
        await cur.execute("INSERT INTO users (id, name) VALUES (%s, %s)", (999, "Async"))
        await cur.execute("SELECT id, name FROM users WHERE id = %s", (999,))
        rows = await cur.fetchall()
        assert rows == [(999, "Async")]
        await cur.execute("DELETE FROM users WHERE id = %s", (999,))
        await conn.commit()
        await conn.close()

    asyncio.run(_run())


def test_async_invalid_uri_raises():
    async def _run():
        with pytest.raises(MongoDbApiError) as exc:
            await connect_async("", MONGODB_DB)
        assert "[mdb][E1]" in str(exc.value)

    asyncio.run(_run())


def test_async_unsupported_sql_raises():
    async def _run():
        conn = await connect_async(MONGODB_URI, MONGODB_DB)
        cur = await conn.cursor()
        with pytest.raises(MongoDbApiError) as exc:
            await cur.execute("SELECT * FROM users u FULL OUTER JOIN orders o ON u.id = o.user_id")
        assert "[mdb][E2]" in str(exc.value)
        await conn.close()

    asyncio.run(_run())


def test_async_param_mismatch_raises():
    async def _run():
        conn = await connect_async(MONGODB_URI, MONGODB_DB)
        cur = await conn.cursor()
        with pytest.raises(MongoDbApiError) as exc:
            await cur.execute("SELECT * FROM users WHERE id = %s", (1, 2))
        assert "[mdb][E4]" in str(exc.value)
        await conn.close()

    asyncio.run(_run())


def test_async_connection_failed_e7():
    async def _run():
        uri = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=500&connectTimeoutMS=500"
        with pytest.raises(Exception) as exc:
            conn = await connect_async(uri, MONGODB_DB)
            cur = await conn.cursor()
            await cur.execute("SELECT id FROM users")
        msg = str(exc.value)
        assert "[mdb][E7]" in msg or "ServerSelectionTimeoutError" in msg or "Connection refused" in msg

    asyncio.run(_run())
