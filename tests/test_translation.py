import pytest

from mongo_dbapi.errors import MongoDbApiError
from mongo_dbapi.translation import parse_sql


def _raises(code: str, sql: str) -> None:
    with pytest.raises(MongoDbApiError) as exc:
        parse_sql(sql)
    assert code in str(exc.value)


def test_non_equi_join_rejected():
    _raises("[mdb][E2]", "SELECT * FROM users u JOIN orders o ON u.id > o.user_id")


def test_full_outer_join_rejected():
    _raises("[mdb][E2]", "SELECT * FROM users u FULL OUTER JOIN orders o ON u.id = o.user_id")


def test_union_distinct_rejected():
    _raises("[mdb][E2]", "SELECT id FROM users UNION SELECT id FROM users")


def test_window_rank_rejected():
    _raises("[mdb][E2]", "SELECT id, RANK() OVER (ORDER BY id) FROM users")


def test_correlated_subquery_rejected():
    _raises("[mdb][E2]", "SELECT id FROM users u WHERE EXISTS (SELECT 1 FROM users x WHERE x.id = u.id)")


def test_named_param_shortage_rejected():
    with pytest.raises(MongoDbApiError) as exc:
        parse_sql("SELECT * FROM users WHERE id = %(id)s", params={"other": 1})
    assert "[mdb][E4]" in str(exc.value)


def test_named_param_surplus_rejected():
    with pytest.raises(MongoDbApiError) as exc:
        parse_sql("SELECT * FROM users WHERE id = %(id)s", params={"id": 1, "extra": 2})
    assert "[mdb][E4]" in str(exc.value)


def test_unknown_statement_rejected():
    _raises("[mdb][E2]", "MERGE INTO users USING dual ON (1=1) WHEN MATCHED THEN UPDATE SET name = 'x'")


def test_window_row_number_without_partition_parses():
    parts = parse_sql("SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn FROM users")
    assert parts.uses_window is True

def test_param_shortage_rejected():
    with pytest.raises(MongoDbApiError) as exc:
        parse_sql("SELECT * FROM users WHERE id = %s", params=None)
    assert "[mdb][E4]" in str(exc.value)


def test_param_surplus_rejected():
    with pytest.raises(MongoDbApiError) as exc:
        parse_sql("SELECT * FROM users WHERE id = %s", params=(1, 2))
    assert "[mdb][E4]" in str(exc.value)
