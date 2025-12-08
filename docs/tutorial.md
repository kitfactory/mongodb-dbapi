# dbapi-mongodb Tutorial (English)

This tutorial shows how to use `dbapi-mongodb` with plain DB-API, SQLAlchemy Core, and async. It reflects the current feature set: JOIN projection/alias support, simple CASE aggregates, HAVING with aggregate aliases, and window functions (`ROW_NUMBER`, `RANK`, `DENSE_RANK` on MongoDB 5+).

## Prerequisites
- Python 3.10+
- MongoDB 4.4+ (transactions) or 5.0+ (window functions). Use the bundled `mongodb-4.4`/`mongodb-7.0` scripts for local tests.
- Install: `pip install dbapi-mongodb`

## DB-API quickstart
```python
from mongo_dbapi import connect

conn = connect("mongodb://127.0.0.1:27019", "mongo_dbapi_test")
cur = conn.cursor()

# INSERT
cur.execute("INSERT INTO projects (id, name) VALUES (%s, %s)", (1, "P1"))

# JOIN with projection and alias
cur.execute("""
SELECT p.id AS project_id, t.id AS task_id
FROM projects p
JOIN tasks t ON p.id = t.project_id
WHERE t.status = %s
""", ("open",))
print(cur.fetchall())

# CASE aggregate + HAVING with aggregate alias
cur.execute("""
SELECT project_id,
       SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done_count
FROM tasks
GROUP BY project_id
HAVING done_count >= 1
ORDER BY project_id
""")
print(cur.fetchall())

# Window functions (MongoDB 5+)
cur.execute("""
SELECT user_id,
       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) AS rn,
       RANK() OVER (ORDER BY created_at) AS rnk
FROM events
""")
print(cur.fetchall())

conn.close()
```

## SQLAlchemy Core
```python
from sqlalchemy import create_engine, text

engine = create_engine("mongodb+dbapi://127.0.0.1:27019/mongo_dbapi_test")

with engine.begin() as conn:
    conn.execute(text("INSERT INTO tasks (id, project_id, status) VALUES (1, 1, 'open')"))
    rows = conn.execute(text("""
        SELECT p.id AS project_id, t.id AS task_id
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        WHERE t.status = :status
    """), {"status": "open"}).all()
    print(rows)
```

## Async (thread-pool backed)
```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

engine = create_async_engine("mongodb+dbapi://127.0.0.1:27019/mongo_dbapi_test")

async def main():
    async with engine.connect() as conn:
        await conn.execute(text("INSERT INTO events (id, user_id, created_at) VALUES (1, 1, '2024-01-01')"))
        res = await conn.execute(text("""
            SELECT user_id, DENSE_RANK() OVER (ORDER BY created_at) AS drk FROM events
        """))
        print(res.all())

asyncio.run(main())
```

## Notes and limits
- CASE aggregates: only simple `CASE WHEN <col> = <literal> THEN <literal> ELSE <literal> END` are supported.
- HAVING: aggregate aliases are resolved; non-aggregate columns in HAVING remain unsupported (`[mdb][E2]`).
- Window functions: `ROW_NUMBER`, `RANK`, `DENSE_RANK` on MongoDB 5+. Older versions return `[mdb][E2]`.
- Transactions: available on MongoDB 4.x+ replica sets; 3.6 is treated as no-op success.
