# storage.py
from __future__ import annotations
import sqlite3
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _base_dir() -> Path:
    # 与 settings 相同的逻辑，确保数据库与 exe 形影不离
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent.resolve()
    else:
        return Path(os.path.abspath(__file__)).parent.resolve()


DB_PATH = _base_dir() / "nekohub.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                appid INTEGER,
                title TEXT,
                message TEXT,
                priority INTEGER,
                date TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                k TEXT PRIMARY KEY,
                v TEXT
            )
            """
        )
        con.commit()


def get_meta(key: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
        return row[0] if row else None


def set_meta(key: str, value: str):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (key, value))
        con.commit()


def upsert_messages(items: List[Dict[str, Any]]):
    with sqlite3.connect(DB_PATH) as con:
        for m in items:
            con.execute(
                """
                INSERT OR IGNORE INTO messages(id, appid, title, message, priority, date)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    int(m.get("id", 0)),
                    int(m.get("appid", 0)),
                    str(m.get("title") or ""),
                    str(m.get("message") or ""),
                    int(m.get("priority", 0)),
                    str(m.get("date") or ""),
                ),
            )
        con.commit()


def latest_messages(limit: int = 200) -> List[Tuple]:
    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            "SELECT id, appid, title, message, priority, date FROM messages ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return rows
