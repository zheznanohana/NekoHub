"""Deterministic structured table projection. Never render model-supplied HTML."""
from .rollup import Rollups

COLUMNS = ["id", "level", "source", "subject", "relation", "content", "period", "status", "parent_ids", "child_ids", "evidence_ids", "fields"]


def table(store, owner):
    graph = store.graph(owner, 200)
    names = {n["id"]: n["label"] for n in graph["nodes"]}
    rows = []
    summaries = Rollups(store).search(owner)
    for record in store.search(owner, "", limit=100):
        rows.append({"id": record["id"], "level": "raw", "source": record["source_type"], "subject": record["id"], "relation": "original_record", "content": record["text"], "period": record["occurred_at"], "status": "recorded", "parent_ids": [s["id"] for s in summaries if record["id"] in s["event_ids"]], "child_ids": [], "evidence_ids": [record["id"]]})
    for fact in graph["facts"]:
        value = fact["object"]
        rows.append({"id": fact["id"], "level": "detail", "source": "memory_agent", "parent_ids": [], "subject": names.get(fact["subject_id"], fact["subject_id"]),
                     "relation": fact["predicate"], "content": names.get(value.get("node_id"), value.get("value", "")),
                     "period": fact["valid_from"], "status": fact["status"], "child_ids": [],
                     "evidence_ids": list(dict.fromkeys(e["event_id"] for e in fact["evidence"]))})
    for summary in summaries:
        rows.append({"id": summary["id"], "level": summary["level"], "source": "memory_agent", "parent_ids": [s["id"] for s in summaries if summary["id"] in s["child_ids"]], "subject": summary["period"], "relation": "summarizes",
                     "content": summary["summary"], "period": summary["period"], "status": "active", "child_ids": summary["child_ids"],
                     "evidence_ids": summary["event_ids"]})
    for row in rows:
        row['fields'] = store.event(owner, row['id'])['content'].get('fields', {}) if row['level']=='raw' else {}
    return {"type": "memory.table", "columns": COLUMNS, "rows": rows, "scope": "latest 100 raw records, up to 200 active facts and current summaries; not a full database backup"}
