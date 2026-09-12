"""Synthetic contract fixtures; not user history."""
from copy import deepcopy

TEXT = "我计划明天下午三点整理 NekoHub 的记忆设计。"
INGEST = {
    "schema_version": "1.0", "kind": "memory.ingest", "request_id": "req-demo-1",
    "source": {"type": "manual", "instance_id": "desktop-demo", "external_id": "note-demo-1"},
    "occurred_at": "2026-09-12T15:00:00+09:00", "timezone": "Asia/Tokyo",
    "content": {"title": "速记", "text": TEXT}, "provenance": "user_authored",
}
CHANGESET = {
    "schema_version": "1.0", "kind": "memory.changeset", "request_id": "req-demo-1",
    "idempotency_key": "demo-extraction-v1", "extractor_version": "demo/1",
    "nodes": [{"id": "task-demo", "kind": "task", "label": "整理记忆设计", "aliases": []},
              {"id": "project-demo", "kind": "project", "label": "NekoHub", "aliases": []}],
    "operations": [{"op": "assert", "fact": {
        "id": "fact-demo", "subject_id": "task-demo", "predicate": "belongs_to",
        "object": {"node_id": "project-demo"}, "valid_from": None, "valid_to": None,
        "epistemic": "reported", "status": "candidate", "confidence": 0.9, "version": 1,
        "evidence": [{"event_id": "event-demo", "start": 0, "end": len(TEXT), "quote": TEXT}],
    }}],
}
RESULT = {
    "schema_version": "1.0", "kind": "memory.result", "request_id": "req-demo-2",
    "as_of": "2026-09-12T06:01:00Z",
    "graph": {"nodes": deepcopy(CHANGESET["nodes"]), "facts": [deepcopy(CHANGESET["operations"][0]["fact"])]},
    "answer": {"status": "supported", "claims": [{"text": "你计划整理 NekoHub 的记忆设计。", "fact_ids": ["fact-demo"]}], "unknowns": []},
    "next_cursor": None,
}
RESULT["graph"]["facts"][0]["status"] = "active"
QUERY = {
    "schema_version": "1.0", "kind": "memory.query", "request_id": "req-demo-2",
    "question": "记忆设计属于哪个项目？", "filters": {"from": None, "to": None, "node_ids": [], "include_candidates": False},
    "view": "graph", "limit": 50, "cursor": None,
}
