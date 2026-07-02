from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("school.db")

SCHEMA_SQL = """
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    score REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    grade REAL,
    status TEXT NOT NULL DEFAULT 'enrolled',
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
"""

SEED_SQL = """
INSERT INTO students (name, cohort, email, score, active) VALUES
    ('An Nguyen', 'A1', 'an.nguyen@example.edu', 88.5, 1),
    ('Binh Tran', 'A1', 'binh.tran@example.edu', 91.0, 1),
    ('Chi Le', 'B2', 'chi.le@example.edu', 76.5, 1),
    ('Dung Pham', 'B2', 'dung.pham@example.edu', 84.0, 0),
    ('Mai Hoang', 'C3', 'mai.hoang@example.edu', 95.0, 1);

INSERT INTO courses (code, title, credits) VALUES
    ('MCP101', 'Model Context Protocol Basics', 3),
    ('DB201', 'Applied Databases', 4),
    ('AI150', 'AI Tool Integration', 3);

INSERT INTO enrollments (student_id, course_id, grade, status) VALUES
    (1, 1, 87.0, 'completed'),
    (1, 2, 90.0, 'completed'),
    (2, 1, 93.0, 'completed'),
    (2, 3, 89.5, 'enrolled'),
    (3, 2, 78.0, 'completed'),
    (4, 3, 80.0, 'dropped'),
    (5, 1, 96.0, 'completed'),
    (5, 3, 94.0, 'enrolled');
"""


def create_database(db_path: str | Path = DB_PATH) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()
    return path


if __name__ == "__main__":
    print(create_database())
