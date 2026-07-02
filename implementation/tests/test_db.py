from pathlib import Path
from uuid import uuid4

import pytest

from db import SQLiteAdapter, ValidationError
from init_db import create_database


@pytest.fixture()
def adapter() -> SQLiteAdapter:
    test_db = Path(__file__).resolve().parents[1] / 'test_dbs' / f'sqlite_lab_{uuid4().hex}.db'
    return SQLiteAdapter(create_database(test_db))


def test_search_filters_ordering_and_pagination(adapter: SQLiteAdapter):
    result = adapter.search(
        "students",
        filters={"cohort": "A1"},
        columns=["name", "score"],
        order_by="score",
        descending=True,
        limit=1,
    )

    assert result["row_count"] == 1
    assert result["rows"][0]["name"] == "Binh Tran"


def test_insert_returns_inserted_row(adapter: SQLiteAdapter):
    result = adapter.insert(
        "students",
        {
            "name": "Lan Vo",
            "cohort": "C3",
            "email": "lan.vo@example.edu",
            "score": 82.0,
            "active": 1,
        },
    )

    assert result["row"]["name"] == "Lan Vo"
    assert result["inserted_id"] > 0


def test_aggregate_average_by_cohort(adapter: SQLiteAdapter):
    result = adapter.aggregate("students", "avg", "score", group_by="cohort")

    rows = {row["cohort"]: row["value"] for row in result["rows"]}
    assert rows["A1"] == 89.75


def test_schema_contains_students(adapter: SQLiteAdapter):
    schema = adapter.get_table_schema("students")

    assert "score" in {column["name"] for column in schema["columns"]}


def test_rejects_unknown_table(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError, match="unknown table"):
        adapter.search("missing")


def test_rejects_unknown_column(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError, match="unknown column"):
        adapter.search("students", filters={"password": "secret"})


def test_rejects_unsupported_operator(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError, match="unsupported filter operator"):
        adapter.search("students", filters=[{"column": "score", "op": "contains", "value": 9}])


def test_rejects_empty_insert(adapter: SQLiteAdapter):
    with pytest.raises(ValidationError, match="cannot be empty"):
        adapter.insert("students", {})


