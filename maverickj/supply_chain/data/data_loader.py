from __future__ import annotations

import sqlite3
from pathlib import Path


def init_db(db_path: str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    seed_path = Path(__file__).with_name("seed.sql")
    seed_sql = seed_path.read_text(encoding="utf-8")
    with sqlite3.connect(path) as conn:
        conn.executescript(seed_sql)
        conn.commit()

