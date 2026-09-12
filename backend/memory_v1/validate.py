"""Contract boundary validation. Does not authorize or apply changesets."""
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = json.loads(Path(__file__).with_name("contract.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def check(condition, message):
    if not condition:
        raise ValueError(message)


def dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check_range(start, end):
    if start is not None and end is not None:
        check(dt(start) < dt(end), "time range must be increasing")


def validate(document, *, evidence_texts=None, existing_node_ids=()):
    """Evidence maps and existing IDs must come from an owner-scoped trusted store.

    Evidence offsets are Python Unicode code-point offsets into content.text,
    using [start, end). No whitespace or Unicode normalization is performed.
    """
    VALIDATOR.validate(document)
    kind = document["kind"]
    if kind == "memory.ingest":
        try:
            ZoneInfo(document["timezone"])
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("unknown IANA timezone (install tzdata on Windows)") from exc
        return
    if kind == "memory.query":
        check_range(document["filters"]["from"], document["filters"]["to"])
        return
    if kind == "memory.error":
        return

    graph = document if kind == "memory.changeset" else document["graph"]
    node_ids = [n["id"] for n in graph["nodes"]]
    check(len(node_ids) == len(set(node_ids)), "duplicate node ID")
    if kind == "memory.changeset":
        check(not set(node_ids).intersection(existing_node_ids), "new node ID already exists")
    available = set(node_ids) | (set(existing_node_ids) if kind == "memory.changeset" else set())
    operations = document.get("operations", [])
    facts = [op["fact"] for op in operations if "fact" in op] if operations else graph["facts"]
    fact_ids = [fact["id"] for fact in facts]
    check(len(fact_ids) == len(set(fact_ids)), "duplicate fact ID")
    evidence = [e for fact in facts for e in fact["evidence"]]

    for fact in facts:
        check(fact["subject_id"] in available, "dangling subject")
        value = fact["object"]
        if "node_id" in value:
            check(value["node_id"] in available, "dangling object")
        else:
            if value["datatype"] == "datetime":
                FormatChecker().check(value["value"], "date-time")
            elif value["datatype"] == "decimal":
                try:
                    check(Decimal(value["value"]).is_finite(), "decimal must be finite")
                except InvalidOperation as exc:
                    raise ValueError("invalid decimal") from exc
            elif value["datatype"] == "boolean":
                check(value["value"] in ("true", "false"), "boolean literal must be true/false")
        check_range(fact["valid_from"], fact["valid_to"])
        if kind == "memory.changeset":
            check(fact["status"] == "candidate" and fact["version"] == 1,
                  "extractor may only propose version-1 candidates")

    targets = [op["target_id"] for op in operations if "target_id" in op]
    check(len(targets) == len(set(targets)), "one operation per existing target per changeset")
    check(not set(targets).intersection(fact_ids), "new fact must have a fresh ID")
    for op in operations:
        evidence.extend(op.get("evidence", []))

    if evidence:
        check(evidence_texts is not None, "trusted evidence text required")
    for item in evidence:
        check(item["event_id"] in evidence_texts, "evidence missing from owner-scoped store")
        text = evidence_texts[item["event_id"]]
        check(0 <= item["start"] < item["end"] <= len(text), "invalid evidence span")
        check(text[item["start"]:item["end"]] == item["quote"], "evidence quote mismatch")

    if kind == "memory.result":
        answer = document["answer"]
        fact_map = {fact["id"]: fact for fact in facts}
        for claim in answer["claims"]:
            check(set(claim["fact_ids"]).issubset(fact_map), "answer cites missing fact")
            check(all(fact_map[fid]["status"] in ("active", "superseded", "archived")
                      for fid in claim["fact_ids"]), "answer cites unconfirmed or retracted fact")
        if answer["status"] == "supported":
            check(bool(answer["claims"]) and not answer["unknowns"], "supported answer must have claims and no unknowns")
        if answer["status"] == "partial":
            check(bool(answer["claims"]) and bool(answer["unknowns"]), "partial answer needs claims and unknowns")
        if answer["status"] == "insufficient_evidence":
            check(not answer["claims"] and bool(answer["unknowns"]), "insufficient answer must state unknowns only")
