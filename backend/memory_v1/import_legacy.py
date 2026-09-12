"""Import the pre-memory NekoHub desktop database into the memory store.

The legacy app kept a flat `messages` table mirroring Gotify. Rows are copied
verbatim as `import` events; nothing is summarised, rewritten or dropped here,
so a re-run is idempotent and the original wording stays quotable as evidence.
"""
import argparse
import json
import os
import re
import sqlite3
from pathlib import Path

from .store import Store

# The desktop forwarder puts the Android package name on the first line.
PACKAGE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+){1,6}$")
INSTANCE = "legacy:nekohub-desktop"


def default_path():
    value = os.getenv("MEMORY_LEGACY_DB")
    return Path(value) if value else None


def rows(path):
    con = sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "messages" not in names:
            raise ValueError("not a NekoHub desktop database: no messages table")
        return [dict(r) for r in con.execute("SELECT id,appid,title,message,priority,date FROM messages ORDER BY id")]
    finally:
        con.close()


def document(row):
    title = (row["title"] or "").strip()
    body = (row["message"] or "").strip()
    package = ""
    lines = body.split("\n", 1)
    if lines and PACKAGE.fullmatch(lines[0].strip()):
        package = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
    text = "\n".join(part for part in (title, body) if part) or "(empty notification)"
    fields = {"legacy_id": int(row["id"]), "appid": row["appid"], "priority": row["priority"]}
    if package:
        fields["app_package"] = package
    return {"schema_version": "1.0", "kind": "memory.ingest", "request_id": f"legacy-{row['id']}",
            "source": {"type": "import", "instance_id": INSTANCE, "external_id": str(row["id"])},
            "occurred_at": row["date"] or None, "timezone": "UTC",
            "content": {"title": title[:1000], "text": text, "fields": fields},
            "provenance": "external"}


def run(store, owner, path):
    """Returns counts only. Per-row failures are reported, never silently skipped."""
    imported = duplicate = 0
    failures = []
    for row in rows(path):
        try:
            ack = store.ingest(owner, document(row))
        except Exception as exc:
            failures.append({"legacy_id": row["id"], "error": type(exc).__name__})
            continue
        duplicate += ack["duplicate"]
        imported += not ack["duplicate"]
    return {"state": "imported", "imported": imported, "duplicate": duplicate,
            "failed": len(failures), "failures": failures[:20], "source": INSTANCE}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_path())
    parser.add_argument("--owner", default=os.getenv("MEMORY_CONNECTOR_OWNER", "admin"))
    parser.add_argument("--db", type=Path, default=os.getenv("MEMORY_DB_PATH") or Path(__file__).with_name("memory.db"))
    args = parser.parse_args()
    if not args.path:
        parser.error("pass the legacy nekohub.db path or set MEMORY_LEGACY_DB")
    print(json.dumps(run(Store(args.db), args.owner, args.path), ensure_ascii=False))


if __name__ == "__main__":
    main()
