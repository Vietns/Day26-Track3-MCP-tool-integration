from __future__ import annotations

from db import SQLiteAdapter
from init_db import create_database


def main() -> None:
    db_path = create_database()
    adapter = SQLiteAdapter(db_path)

    print(f"database: {db_path}")
    print(f"tables: {', '.join(adapter.list_tables())}")

    print("\nsearch students in cohort A1")
    print(adapter.search("students", filters={"cohort": "A1"}, order_by="score", descending=True))

    print("\ninsert a new student")
    print(
        adapter.insert(
            "students",
            {
                "name": "Lan Vo",
                "cohort": "A1",
                "email": "lan.vo@example.edu",
                "score": 82.0,
                "active": 1,
            },
        )
    )

    print("\naverage score by cohort")
    print(adapter.aggregate("students", "avg", "score", group_by="cohort"))

    print("\nfull schema tables")
    print([table["table"] for table in adapter.database_schema()["tables"]])

    print("\nexpected invalid request")
    try:
        adapter.search("missing_table")
    except Exception as exc:
        print(type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()
