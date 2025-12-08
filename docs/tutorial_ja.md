# dbapi-mongodb チュートリアル（日本語）

このチュートリアルでは `dbapi-mongodb` の使い方を紹介します。JOIN 投影/alias、簡易 CASE 集計、HAVING 集計 alias、ウィンドウ関数（`ROW_NUMBER`/`RANK`/`DENSE_RANK`。MongoDB 5+）に対応しています。

## 前提
- Python 3.10+
- MongoDB 4.4+（トランザクション）、5.0+（ウィンドウ関数）。手元で試す場合は同梱の `mongodb-4.4`/`mongodb-7.0` と起動スクリプトを利用してください。
- インストール: `pip install dbapi-mongodb`

## DB-API クイックスタート
```python
from mongo_dbapi import connect

conn = connect("mongodb://127.0.0.1:27019", "mongo_dbapi_test")
cur = conn.cursor()

# INSERT
cur.execute("INSERT INTO projects (id, name) VALUES (%s, %s)", (1, "P1"))

# JOIN 投影（別名付き）
cur.execute("""
SELECT p.id AS project_id, t.id AS task_id
FROM projects p
JOIN tasks t ON p.id = t.project_id
WHERE t.status = %s
""", ("open",))
print(cur.fetchall())

# CASE 集計 + HAVING 集計 alias
cur.execute("""
SELECT project_id,
       SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done_count
FROM tasks
GROUP BY project_id
HAVING done_count >= 1
ORDER BY project_id
""")
print(cur.fetchall())

# ウィンドウ関数（MongoDB 5+）
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

## Async（スレッドプールラップ）
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

## 注意点
- CASE 集計: 単純な `CASE WHEN <col> = <literal> THEN <literal> ELSE <literal> END` のみ対応。
- HAVING: 集計 alias は解決可能。非集計列のみの HAVING は未対応（`[mdb][E2]`）。
- ウィンドウ関数: `ROW_NUMBER`/`RANK`/`DENSE_RANK` は MongoDB 5+。それ未満は `[mdb][E2]`。
- トランザクション: MongoDB 4.x+ のレプリカセットで有効。3.6 は no-op（成功扱い）。
