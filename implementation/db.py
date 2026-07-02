from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


SUPPORTED_OPERATORS = {
    "eq": "=",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "like": "LIKE",
}

SUPPORTED_METRICS = {"count", "avg", "sum", "min", "max"}


class SQLiteAdapter:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> dict[str, Any]:
        table = self._validate_table(table)
        with self.connect() as conn:
            columns = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
            foreign_keys = conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
        return {
            "table": table,
            "columns": [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "primary_key": bool(row["pk"]),
                }
                for row in columns
            ],
            "foreign_keys": [
                {
                    "column": row["from"],
                    "references_table": row["table"],
                    "references_column": row["to"],
                }
                for row in foreign_keys
            ],
        }

    def database_schema(self) -> dict[str, Any]:
        return {
            "database": str(self.db_path),
            "tables": [self.get_table_schema(table) for table in self.list_tables()],
        }

    def search(
        self,
        table: str,
        filters: list[dict[str, Any]] | dict[str, Any] | None = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        table = self._validate_table(table)
        valid_columns = self._column_names(table)
        selected = self._validate_columns(columns, valid_columns) if columns else ["*"]
        limit = self._validate_non_negative_int(limit, "limit", max_value=100)
        offset = self._validate_non_negative_int(offset, "offset")

        where_sql, params = self._build_where(table, filters)
        select_sql = ", ".join(f'"{column}"' for column in selected) if selected != ["*"] else "*"
        sql = f'SELECT {select_sql} FROM "{table}"'
        if where_sql:
            sql += f" WHERE {where_sql}"
        if order_by:
            self._validate_column(order_by, valid_columns)
            direction = "DESC" if descending else "ASC"
            sql += f' ORDER BY "{order_by}" {direction}'
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return {
            "table": table,
            "columns": selected,
            "limit": limit,
            "offset": offset,
            "rows": [dict(row) for row in rows],
            "row_count": len(rows),
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        table = self._validate_table(table)
        if not values:
            raise ValidationError("insert values cannot be empty")

        valid_columns = self._column_names(table)
        for column in values:
            self._validate_column(column, valid_columns)

        columns = list(values.keys())
        column_sql = ", ".join(f'"{column}"' for column in columns)
        placeholder_sql = ", ".join("?" for _ in columns)
        sql = f'INSERT INTO "{table}" ({column_sql}) VALUES ({placeholder_sql})'

        with self.connect() as conn:
            cursor = conn.execute(sql, [values[column] for column in columns])
            conn.commit()
            inserted_id = cursor.lastrowid
            row = conn.execute(
                f'SELECT * FROM "{table}" WHERE rowid = ?',
                [inserted_id],
            ).fetchone()

        return {
            "table": table,
            "inserted_id": inserted_id,
            "row": dict(row) if row else dict(values),
        }

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | dict[str, Any] | None = None,
        group_by: str | list[str] | None = None,
    ) -> dict[str, Any]:
        table = self._validate_table(table)
        metric = metric.lower()
        if metric not in SUPPORTED_METRICS:
            raise ValidationError(f"unsupported aggregate metric: {metric}")

        valid_columns = self._column_names(table)
        if metric == "count" and column is None:
            aggregate_expr = "COUNT(*)"
        else:
            if column is None:
                raise ValidationError(f"{metric} requires a column")
            self._validate_column(column, valid_columns)
            aggregate_expr = f'{metric.upper()}("{column}")'

        group_columns = self._normalize_group_by(group_by, valid_columns)
        select_parts = [f'"{column}"' for column in group_columns]
        select_parts.append(f"{aggregate_expr} AS value")

        where_sql, params = self._build_where(table, filters)
        sql = f'SELECT {", ".join(select_parts)} FROM "{table}"'
        if where_sql:
            sql += f" WHERE {where_sql}"
        if group_columns:
            sql += " GROUP BY " + ", ".join(f'"{column}"' for column in group_columns)
            sql += " ORDER BY " + ", ".join(f'"{column}"' for column in group_columns)

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return {
            "table": table,
            "metric": metric,
            "column": column,
            "group_by": group_columns,
            "rows": [dict(row) for row in rows],
        }

    def _validate_table(self, table: str) -> str:
        if not isinstance(table, str) or not table:
            raise ValidationError("table name is required")
        if table not in self.list_tables():
            raise ValidationError(f"unknown table: {table}")
        return table

    def _column_names(self, table: str) -> set[str]:
        schema = self.get_table_schema(table)
        return {column["name"] for column in schema["columns"]}

    def _validate_column(self, column: str, valid_columns: set[str]) -> str:
        if column not in valid_columns:
            raise ValidationError(f"unknown column: {column}")
        return column

    def _validate_columns(self, columns: list[str], valid_columns: set[str]) -> list[str]:
        if not isinstance(columns, list) or not columns:
            raise ValidationError("columns must be a non-empty list")
        return [self._validate_column(column, valid_columns) for column in columns]

    def _build_where(
        self,
        table: str,
        filters: list[dict[str, Any]] | dict[str, Any] | None,
    ) -> tuple[str, list[Any]]:
        if filters is None:
            return "", []
        if isinstance(filters, dict):
            filters = [
                {"column": column, "op": "eq", "value": value}
                for column, value in filters.items()
            ]
        if not isinstance(filters, list):
            raise ValidationError("filters must be a list or object")

        valid_columns = self._column_names(table)
        clauses: list[str] = []
        params: list[Any] = []

        for item in filters:
            if not isinstance(item, dict):
                raise ValidationError("each filter must be an object")
            column = item.get("column")
            op = item.get("op", "eq")
            value = item.get("value")
            self._validate_column(column, valid_columns)

            if op == "in":
                if not isinstance(value, list) or not value:
                    raise ValidationError("in filters require a non-empty list value")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f'"{column}" IN ({placeholders})')
                params.extend(value)
            elif op == "is_null":
                clauses.append(f'"{column}" IS {"NOT " if value is False else ""}NULL')
            elif op in SUPPORTED_OPERATORS:
                clauses.append(f'"{column}" {SUPPORTED_OPERATORS[op]} ?')
                params.append(value)
            else:
                raise ValidationError(f"unsupported filter operator: {op}")

        return " AND ".join(clauses), params

    def _normalize_group_by(
        self,
        group_by: str | list[str] | None,
        valid_columns: set[str],
    ) -> list[str]:
        if group_by is None:
            return []
        if isinstance(group_by, str):
            group_columns = [group_by]
        elif isinstance(group_by, list) and group_by:
            group_columns = group_by
        else:
            raise ValidationError("group_by must be a column name or a non-empty list")
        return [self._validate_column(column, valid_columns) for column in group_columns]

    def _validate_non_negative_int(
        self,
        value: int,
        name: str,
        max_value: int | None = None,
    ) -> int:
        if not isinstance(value, int) or value < 0:
            raise ValidationError(f"{name} must be a non-negative integer")
        if max_value is not None and value > max_value:
            raise ValidationError(f"{name} cannot be greater than {max_value}")
        return value
