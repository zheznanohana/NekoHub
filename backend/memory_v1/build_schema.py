"""Generate the versioned, strict JSON contracts; no runtime dependencies."""
import json
from pathlib import Path


def obj(properties, required=None):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties) if required is None else required}


def enum(*values):
    return {"enum": list(values)}


def arr(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def ref(name):
    return {"$ref": f"#/$defs/{name}"}


ID = {"type": "string", "minLength": 1, "maxLength": 160}
TEXT = {"type": "string", "minLength": 1, "maxLength": 100000}
TIME = {"type": "string", "format": "date-time"}
NULL_TIME = {"anyOf": [TIME, {"type": "null"}]}
IDS = {**arr(ID, 1), "uniqueItems": True}
DEFS = {
    "evidence": obj({"event_id": ID, "start": {"type": "integer", "minimum": 0},
                     "end": {"type": "integer", "minimum": 1}, "quote": TEXT}),
    "node": obj({"id": ID, "kind": enum("person", "project", "event", "task", "place", "topic", "preference"),
                 "label": {"type": "string", "minLength": 1, "maxLength": 300},
                 "aliases": {**arr(ID), "uniqueItems": True}}),
    "fact": obj({"id": ID, "subject_id": ID,
                 "predicate": enum("participates_in", "belongs_to", "located_at", "scheduled_for", "has_status", "prefers", "related_to"),
                 "object": {"oneOf": [obj({"node_id": ID}), obj({"value": TEXT, "datatype": enum("text", "datetime", "decimal", "boolean"), "unit": {"type": ["string", "null"]}})]},
                 "valid_from": NULL_TIME, "valid_to": NULL_TIME,
                 "epistemic": enum("observed", "reported", "inferred"),
                 "status": enum("candidate", "active", "superseded", "disputed", "retracted", "archived"),
                 "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                 "version": {"type": "integer", "minimum": 1},
                 "evidence": arr(ref("evidence"), 1)}),
}


def envelope(kind, fields):
    return obj({"schema_version": {"const": "1.0"}, "kind": {"const": kind}, "request_id": ID, **fields})


DEFS["ingest"] = envelope("memory.ingest", {
    "source": obj({"type": enum("gotify", "manual", "imap", "rss", "web3", "github", "import"), "instance_id": ID, "external_id": ID}),
    "occurred_at": NULL_TIME, "timezone": ID,
    "content": obj({"title": {"type": "string", "maxLength": 1000}, "text": TEXT,
                    "fields": {"type":"object", "maxProperties":40,
                               "additionalProperties":{"type":["string","number","boolean","null"]}}}, ["title","text"]),
    "provenance": enum("user_authored", "external", "assistant_generated"),
})
DEFS["changeset"] = envelope("memory.changeset", {
    "idempotency_key": ID, "extractor_version": ID, "nodes": arr(ref("node")),
    "operations": arr({"oneOf": [
        obj({"op": {"const": "assert"}, "fact": ref("fact")}),
        obj({"op": {"const": "supersede"}, "target_id": ID,
             "expected_version": {"type": "integer", "minimum": 1}, "reason": TEXT, "fact": ref("fact")}),
        obj({"op": enum("dispute", "retract", "archive"), "target_id": ID,
             "expected_version": {"type": "integer", "minimum": 1}, "reason": TEXT,
             "evidence": arr(ref("evidence"), 1)}),
    ]}, 1),
})
DEFS["query"] = envelope("memory.query", {
    "question": TEXT,
    "filters": obj({"from": NULL_TIME, "to": NULL_TIME, "node_ids": {**arr(ID), "uniqueItems": True},
                    "include_candidates": {"type": "boolean"}}),
    "view": enum("graph", "table", "timeline", "answer"),
    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
    "cursor": {"type": ["string", "null"], "maxLength": 1000},
})
DEFS["result"] = envelope("memory.result", {
    "as_of": TIME, "graph": obj({"nodes": arr(ref("node")), "facts": arr(ref("fact"))}),
    "answer": obj({"status": enum("supported", "partial", "insufficient_evidence"),
                   "claims": arr(obj({"text": TEXT, "fact_ids": IDS})),
                   "unknowns": arr(TEXT)}),
    "next_cursor": {"type": ["string", "null"]},
})
DEFS["error"] = envelope("memory.error", {
    "code": enum("VALIDATION_ERROR", "EVIDENCE_MISMATCH", "VERSION_CONFLICT", "NOT_FOUND", "SOURCE_CONFLICT", "INTERNAL_ERROR"),
    "message": TEXT, "retryable": {"type": "boolean"},
})

SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema",
          "$id": "urn:nekohub:memory:1.0", "$defs": DEFS,
          "oneOf": [ref(k) for k in ("ingest", "changeset", "query", "result", "error")]}

if __name__ == "__main__":
    Path(__file__).with_name("contract.schema.json").write_text(
        json.dumps(SCHEMA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
