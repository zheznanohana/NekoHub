"""User-authored day entries: the one memory layer the model never writes alone.

Every edit keeps the previous text in history and publishes the new text as a
manual event, so a diary line stays quotable as evidence and an edit never
destroys what it replaced.
"""
import json
import re
import uuid

from .rollup import Rollups, period_key
from .store import digest, now, packed
from .validate import validate

DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_TEXT = 20000


def check_day(day):
    if not DAY.fullmatch(day or ""):
        raise ValueError("diary day must be YYYY-MM-DD")
    return day


class Diary:
    def __init__(self, store):
        self.store = store
        with store.db() as con:
            con.executescript("""
              CREATE TABLE IF NOT EXISTS memory_diary (
                owner_id TEXT NOT NULL, day TEXT NOT NULL, text TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1, event_id TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(owner_id,day));
              CREATE TABLE IF NOT EXISTS memory_diary_history (
                id INTEGER PRIMARY KEY, owner_id TEXT NOT NULL, day TEXT NOT NULL,
                text TEXT NOT NULL, version INTEGER NOT NULL, replaced_at TEXT NOT NULL);
            """)

    def write(self, owner, day, text):
        check_day(day)
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
            raise ValueError(f"diary text must be 1-{MAX_TEXT} characters")
        text = text.strip()
        with self.store.db() as con:
            con.execute("BEGIN IMMEDIATE")
            old = con.execute("SELECT text,version,created_at FROM memory_diary WHERE owner_id=? AND day=?", (owner, day)).fetchone()
            if old and old["text"] == text:
                return {"state": "unchanged", "day": day, "version": old["version"]}
            version = (old["version"] + 1) if old else 1
            if old:
                con.execute("INSERT INTO memory_diary_history(owner_id,day,text,version,replaced_at) VALUES(?,?,?,?,?)",
                            (owner, day, old["text"], old["version"], now()))
        # A distinct external ID per version keeps edits additive instead of a source conflict.
        event = self.store.ingest(owner, {
            "schema_version": "1.0", "kind": "memory.ingest", "request_id": uuid.uuid4().hex,
            "source": {"type": "manual", "instance_id": "diary", "external_id": f"{day}:v{version}"},
            "occurred_at": f"{day}T00:00:00Z", "timezone": "UTC",
            "content": {"title": f"日记 {day}", "text": text, "fields": {"diary_day": day, "diary_version": version}},
            "provenance": "user_authored"})
        with self.store.db() as con:
            con.execute("""INSERT INTO memory_diary(owner_id,day,text,version,event_id,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(owner_id,day) DO UPDATE SET
                text=excluded.text,version=excluded.version,event_id=excluded.event_id,updated_at=excluded.updated_at""",
                (owner, day, text, version, event["event_id"], (old["created_at"] if old else now()), now()))
        return {"state": "saved", "day": day, "version": version, "event_id": event["event_id"]}

    def history(self, owner, day):
        check_day(day)
        with self.store.db() as con:
            return [dict(r) for r in con.execute(
                "SELECT version,text,replaced_at FROM memory_diary_history WHERE owner_id=? AND day=? ORDER BY version DESC", (owner, day))]

    def rows(self, owner, start="", end="", text=""):
        """One row per day that has an entry, records, or both. Never invents days."""
        with self.store.db() as con:
            entries = {r["day"]: dict(r) for r in con.execute("SELECT * FROM memory_diary WHERE owner_id=?", (owner,))}
            events = [dict(r) for r in con.execute(
                "SELECT id,text,occurred_at,received_at,source_type FROM memory_events WHERE owner_id=? AND deleted_at IS NULL", (owner,))]
        by_day = {}
        for event in events:
            by_day.setdefault(period_key(event, "day"), []).append(event)
        summaries = {s["period"]: s for s in Rollups(self.store).search(owner) if s["level"] == "day"}
        rows = []
        for day in sorted(set(entries) | set(by_day), reverse=True):
            if (start and day < start) or (end and day > end):
                continue
            entry = entries.get(day)
            day_events = sorted(by_day.get(day, []), key=lambda e: e["occurred_at"] or e["received_at"])
            summary = summaries.get(day)
            row = {"day": day, "text": entry["text"] if entry else "", "version": entry["version"] if entry else 0,
                   "updated_at": entry["updated_at"] if entry else None,
                   "event_count": len(day_events), "event_ids": [e["id"] for e in day_events][:200],
                   "sources": sorted({e["source_type"] for e in day_events}),
                   "summary": summary["summary"] if summary else "", "summary_id": summary["id"] if summary else ""}
            if text and text.lower() not in (row["text"] + row["summary"]).lower():
                continue
            rows.append(row)
        return rows

    def block(self, owner, start="", end="", text=""):
        return {"type": "memory.diary", "rows": self.rows(owner, start, end, text),
                "scope": "每天一行：你写的日记、当天记录条数与来源、以及该日自动摘要。空白日期表示当天没有记录也没有日记。"}
