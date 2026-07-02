from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from db import SQLiteAdapter, ValidationError
from init_db import DB_PATH, create_database


if not Path(DB_PATH).exists():
    create_database(DB_PATH)

adapter = SQLiteAdapter(DB_PATH)
mcp = FastMCP("SQLite Lab MCP Server")


def _run(callable_obj, *args, **kwargs) -> dict[str, Any]:
    try:
        return callable_obj(*args, **kwargs)
    except ValidationError as exc:
        return {"error": str(exc), "error_type": "validation_error"}


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict[str, Any]] | dict[str, Any] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows with optional filters, selected columns, ordering, and pagination."""
    return _run(adapter.search, table, filters, columns, limit, offset, order_by, descending)


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one row into a known table using validated column names."""
    return _run(adapter.insert, table, values)


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | dict[str, Any] | None = None,
    group_by: str | list[str] | None = None,
) -> dict[str, Any]:
    """Run count, avg, sum, min, or max over validated columns."""
    return _run(adapter.aggregate, table, metric, column, filters, group_by)


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return a JSON description of all database tables."""
    return json.dumps(adapter.database_schema(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return a JSON description for a single table."""
    try:
        payload = adapter.get_table_schema(table_name)
    except ValidationError as exc:
        payload = {"error": str(exc), "error_type": "validation_error"}
    return json.dumps(payload, indent=2)


if __name__ == "__main__":
    mcp.run()
