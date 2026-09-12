"""Persistent single-host memory queue and transactional graph repository."""
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .validate import validate


def now():
    return datetime.now(timezone.utc).isoformat()


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(packed(value).encode()).hexdigest()


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, path):
        self.path = str(Path(path).resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as con:
            con.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
            con.executescript("""
              CREATE TABLE IF NOT EXISTS memory_jobs (
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, event_id TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending', lease_until REAL NOT NULL DEFAULT 0,
                lease_token TEXT, attempts INTEGER NOT NULL DEFAULT 0,
                snapshot TEXT, result TEXT, error TEXT, created_at TEXT NOT NULL,
                UNIQUE(owner_id,event_id),
                FOREIGN KEY(owner_id,event_id) REFERENCES memory_events(owner_id,id));
              CREATE TABLE IF NOT EXISTS memory_audit (
                id INTEGER PRIMARY KEY, owner_id TEXT NOT NULL, job_id TEXT NOT NULL,
                actor TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS memory_actions (
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, command TEXT NOT NULL,
                expected_hash TEXT, expires_at REAL NOT NULL, state TEXT NOT NULL DEFAULT 'pending');
            """)

    @contextmanager
    def db(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            with con:
                yield con
        finally:
            con.close()

    def ingest(self, owner, document):
        validate(document)
        if document["kind"] != "memory.ingest":
            raise ValueError("memory.ingest required")
        source = document["source"]
        canonical = {key: value for key, value in document.items() if key != "request_id"}
        content_hash = digest(canonical)
        with self.db() as con:
            con.execute("BEGIN IMMEDIATE")
            existing = con.execute("SELECT id,content_hash FROM memory_events WHERE owner_id=? AND instance_id=? AND external_id=?",
                                   (owner, source["instance_id"], source["external_id"])).fetchone()
            if existing:
                if existing["content_hash"] != content_hash:
                    raise Conflict("source message ID reused with different content")
                job = con.execute("SELECT id,state FROM memory_jobs WHERE owner_id=? AND event_id=?", (owner, existing["id"])).fetchone()
                return {"event_id": existing["id"], "job_id": job["id"], "state": job["state"], "duplicate": True}
            event_id, job_id = uuid.uuid4().hex, uuid.uuid4().hex
            con.execute("INSERT INTO memory_events(owner_id,id,source_type,instance_id,external_id,text,raw_json,content_hash,occurred_at,received_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (owner, event_id, source["type"], source["instance_id"], source["external_id"], document["content"]["text"], packed(document), content_hash, document["occurred_at"], now()))
            con.execute("INSERT INTO memory_jobs(id,owner_id,event_id,created_at) VALUES(?,?,?,?)", (job_id, owner, event_id, now()))
            return {"event_id": event_id, "job_id": job_id, "state": "pending", "duplicate": False}

    def _graph(self, con, owner, limit=100):
        facts = []
        rows = con.execute("SELECT * FROM memory_facts WHERE owner_id=? AND status='active' ORDER BY recorded_at DESC,id LIMIT ?", (owner, limit)).fetchall()
        ids = set()
        for row in rows:
            ids.add(row["subject_id"])
            if row["object_node_id"]:
                ids.add(row["object_node_id"])
            evidence = [dict(e) for e in con.execute("SELECT event_id,start_offset AS start,end_offset AS end,quote FROM memory_evidence WHERE owner_id=? AND fact_id=?", (owner, row["id"]))]
            if not evidence or any(con.execute("SELECT 1 FROM memory_events WHERE owner_id=? AND id=? AND deleted_at IS NULL", (owner, e["event_id"])).fetchone() is None for e in evidence):
                continue
            fact = {key: row[key] for key in ("id", "subject_id", "predicate", "valid_from", "valid_to", "status", "epistemic", "confidence", "version")}
            fact["object"] = {"node_id": row["object_node_id"]} if row["object_node_id"] else {"value": row["object_value"], "datatype": row["datatype"], "unit": row["unit"]}
            fact["evidence"] = evidence
            facts.append(fact)
        nodes = []
        for node_id in sorted(ids):
            row = con.execute("SELECT * FROM memory_nodes WHERE owner_id=? AND id=?", (owner, node_id)).fetchone()
            nodes.append({"id": row["id"], "kind": row["kind"], "label": row["label"], "aliases": json.loads(row["aliases_json"])})
        return {"nodes": nodes, "facts": facts}

    def graph(self, owner, limit=100):
        with self.db() as con:
            return self._graph(con, owner, min(max(limit, 1), 200))

    def jobs(self, owner):
        with self.db() as con:
            return [dict(row) for row in con.execute("SELECT id,event_id,state,error,attempts,created_at FROM memory_jobs WHERE owner_id=? ORDER BY created_at DESC LIMIT 100", (owner,))]

    def event(self, owner, event_id):
        with self.db() as con:
            row = con.execute("SELECT raw_json FROM memory_events WHERE owner_id=? AND id=? AND deleted_at IS NULL", (owner, event_id)).fetchone()
            if not row:
                raise KeyError(event_id)
            return json.loads(row[0])

    def index(self):
        """Lazily built so a plain contract/store user never pays for FTS setup."""
        if getattr(self, "_index", None) is None:
            from .retrieval import Index, embeddings_from_env
            self._index = Index(self, embeddings_from_env())
        return self._index

    def search(self, owner, text, limit=30):
        """Empty text means 'latest records'. Otherwise ranked; see retrieval.py."""
        limit = min(max(limit, 1), 100)
        columns = "id,text,occurred_at,source_type,content_hash"
        if not (text or "").strip():
            with self.db() as con:
                return [dict(row) for row in con.execute(
                    f"SELECT {columns} FROM memory_events WHERE owner_id=? AND deleted_at IS NULL ORDER BY received_at DESC LIMIT ?",
                    (owner, limit))]
        ranked, _mode = self.index().search(owner, text, limit)
        if not ranked:
            return []
        with self.db() as con:
            found = {row["id"]: dict(row) for row in con.execute(
                f"SELECT {columns} FROM memory_events WHERE owner_id=? AND deleted_at IS NULL AND id IN ({','.join('?' * len(ranked))})",
                (owner, *ranked))}
        return [found[event_id] for event_id in ranked if event_id in found]

    def prepare_action(self, owner, command):
        import time
        action_id = uuid.uuid4().hex
        expected_hash = None
        with self.db() as con:
            if command["command"] in ("memory.update", "memory.delete"):
                row = con.execute("SELECT content_hash FROM memory_events WHERE owner_id=? AND id=? AND deleted_at IS NULL", (owner, command["event_id"])).fetchone()
                if not row:
                    raise KeyError(command["event_id"])
                expected_hash = row[0]
            con.execute("INSERT INTO memory_actions(id,owner_id,command,expected_hash,expires_at) VALUES(?,?,?,?,?)", (action_id, owner, packed(command), expected_hash, time.time()+600))
        return action_id

    def confirm_action(self, owner, action_id):
        import time
        with self.db() as con:
            con.execute("BEGIN IMMEDIATE")
            action = con.execute("SELECT * FROM memory_actions WHERE owner_id=? AND id=?", (owner, action_id)).fetchone()
            if not action:
                raise KeyError(action_id)
            if action["state"] != "pending" or action["expires_at"] < time.time():
                raise Conflict("action used or expired")
            command = json.loads(action["command"])
            if command["command"] in ("memory.update", "memory.delete"):
                row = con.execute("SELECT content_hash FROM memory_events WHERE owner_id=? AND id=? AND deleted_at IS NULL", (owner, command["event_id"])).fetchone()
                if not row or row[0] != action["expected_hash"]:
                    raise Conflict("record changed since preview")
                con.execute("UPDATE memory_events SET deleted_at=? WHERE owner_id=? AND id=?", (now(), owner, command["event_id"]))
                con.execute("UPDATE memory_facts SET status='retracted',version=version+1 WHERE owner_id=? AND id IN (SELECT fact_id FROM memory_evidence WHERE owner_id=? AND event_id=?)", (owner, owner, command["event_id"]))
                con.execute("UPDATE memory_jobs SET state='rejected' WHERE owner_id=? AND event_id=? AND state IN ('pending','review')", (owner, command["event_id"]))
            if command["command"] == "memory.diary.write":
                con.execute("UPDATE memory_actions SET state='applied' WHERE id=?", (action_id,))
                con.execute("INSERT INTO memory_audit(owner_id,job_id,actor,result,created_at) VALUES(?,?,?,?,?)", (owner, action_id, "user:chat", packed({"command": command}), now()))
                return {"state": "applied", "event_id": None, "command": command}
            event_id = None
            if command["command"] in ("memory.create", "memory.update"):
                event_id = uuid.uuid4().hex
                document = {"schema_version": "1.0", "kind": "memory.ingest", "request_id": action_id,
                            "source": {"type": "manual", "instance_id": "chat", "external_id": action_id},
                            "occurred_at": now(), "timezone": "UTC", "content": {"title": "聊天记录", "text": command["text"]}, "provenance": "user_authored"}
                validate(document)
                canonical = {k:v for k,v in document.items() if k != "request_id"}
                con.execute("INSERT INTO memory_events(owner_id,id,source_type,instance_id,external_id,text,raw_json,content_hash,occurred_at,received_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (owner, event_id, "manual", "chat", action_id, command["text"], packed(document), digest(canonical), document["occurred_at"], now()))
                con.execute("INSERT INTO memory_jobs(id,owner_id,event_id,created_at) VALUES(?,?,?,?)", (uuid.uuid4().hex, owner, event_id, now()))
            con.execute("UPDATE memory_actions SET state='applied' WHERE id=?", (action_id,))
            con.execute("INSERT INTO memory_audit(owner_id,job_id,actor,result,created_at) VALUES(?,?,?,?,?)", (owner, action_id, "user:chat", packed({"command": command, "new_event_id": event_id}), now()))
            return {"state": "applied", "event_id": event_id}

    def process_one(self, owner, agent, *, auto_apply=False):
        import time
        token = uuid.uuid4().hex
        with self.db() as con:
            con.execute("BEGIN IMMEDIATE")
            job = con.execute("SELECT * FROM memory_jobs WHERE owner_id=? AND (state='pending' OR (state='running' AND lease_until<?)) ORDER BY created_at LIMIT 1", (owner, time.time())).fetchone()
            if not job:
                return None
            job = dict(job)
            con.execute("UPDATE memory_jobs SET state='running',lease_until=?,lease_token=?,attempts=attempts+1 WHERE id=?", (time.time()+300, token, job["id"]))
            if job["snapshot"]:
                snapshot = json.loads(job["snapshot"])
            else:
                graph = self._graph(con, owner, 60)
                event_ids = {job["event_id"]} | {e["event_id"] for f in graph["facts"] for e in f["evidence"]}
                events = []
                for event_id in sorted(event_ids):
                    row = con.execute("SELECT raw_json FROM memory_events WHERE owner_id=? AND id=? AND deleted_at IS NULL", (owner, event_id)).fetchone()
                    if row:
                        events.append({"event_id": event_id, "ingest": json.loads(row[0])})
                snapshot = {"events": events, "known_nodes": graph["nodes"], "known_facts": graph["facts"]}
                con.execute("UPDATE memory_jobs SET snapshot=? WHERE id=?", (packed(snapshot), job["id"]))
        try:
            proposal = agent.propose(job_id=job["id"], mode="ingest", **snapshot)
            state = "skipped" if proposal["kind"] == "memory.skip" else "review"
            with self.db() as con:
                changed = con.execute("UPDATE memory_jobs SET state=?,result=?,lease_until=0 WHERE id=? AND lease_token=? AND state='running'", (state, packed(proposal), job["id"], token)).rowcount
                if not changed:
                    raise Conflict("job lease changed")
            # Auto policy: explicit manual sources, reported/observed assertions only.
            fresh = self.event(owner, job["event_id"])
            if auto_apply and state == "review" and fresh["source"]["type"] == "manual" and all(op["op"] == "assert" and op["fact"]["epistemic"] != "inferred" for op in proposal["operations"]):
                self.review(owner, job["id"], approve=True, actor="policy:manual-assertions")
                state = "applied"
            return {"job_id": job["id"], "state": state}
        except Exception as exc:
            with self.db() as con:
                con.execute("UPDATE memory_jobs SET state='failed',error=?,lease_until=0 WHERE id=? AND lease_token=? AND state IN ('running','review')", (type(exc).__name__, job["id"], token))
            raise

    def proposal(self, owner, job_id):
        with self.db() as con:
            row = con.execute("SELECT state,result FROM memory_jobs WHERE owner_id=? AND id=?", (owner, job_id)).fetchone()
            if not row:
                raise KeyError(job_id)
            return {"state": row["state"], "proposal": json.loads(row["result"]) if row["result"] else None}

    def review(self, owner, job_id, *, approve, actor="user"):
        with self.db() as con:
            con.execute("BEGIN IMMEDIATE")
            job = con.execute("SELECT * FROM memory_jobs WHERE owner_id=? AND id=?", (owner, job_id)).fetchone()
            if not job:
                raise KeyError(job_id)
            if job["state"] != "review":
                raise Conflict("job not pending review")
            result = json.loads(job["result"])
            if approve:
                texts = {r["id"]: r["text"] for r in con.execute("SELECT id,text FROM memory_events WHERE owner_id=? AND deleted_at IS NULL", (owner,))}
                node_ids = [r[0] for r in con.execute("SELECT id FROM memory_nodes WHERE owner_id=?", (owner,))]
                validate(result, evidence_texts=texts, existing_node_ids=node_ids)
                for node in result["nodes"]:
                    con.execute("INSERT INTO memory_nodes(owner_id,id,kind,label,aliases_json) VALUES(?,?,?,?,?)", (owner, node["id"], node["kind"], node["label"], packed(node["aliases"])))
                for op in result["operations"]:
                    if "target_id" in op:
                        status = {"supersede": "superseded", "dispute": "disputed", "retract": "retracted", "archive": "archived"}[op["op"]]
                        changed = con.execute("UPDATE memory_facts SET status=?,version=version+1 WHERE owner_id=? AND id=? AND version=?", (status, owner, op["target_id"], op["expected_version"])).rowcount
                        if not changed:
                            raise Conflict("target version changed")
                    if "fact" not in op:
                        continue
                    fact = op["fact"]
                    value = fact["object"]
                    con.execute("""INSERT INTO memory_facts(owner_id,id,subject_id,predicate,object_node_id,object_value,datatype,unit,status,epistemic,confidence,valid_from,valid_to,recorded_at,version,supersedes_id)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (owner, fact["id"], fact["subject_id"], fact["predicate"], value.get("node_id"), value.get("value"), value.get("datatype"), value.get("unit"), "active", fact["epistemic"], fact["confidence"], fact["valid_from"], fact["valid_to"], now(), 1, op.get("target_id") if op["op"] == "supersede" else None))
                    for e in fact["evidence"]:
                        con.execute("INSERT INTO memory_evidence VALUES(?,?,?,?,?,?)", (owner, fact["id"], e["event_id"], e["start"], e["end"], e["quote"]))
            state = "applied" if approve else "rejected"
            con.execute("UPDATE memory_jobs SET state=? WHERE id=?", (state, job_id))
            con.execute("INSERT INTO memory_audit(owner_id,job_id,actor,result,created_at) VALUES(?,?,?,?,?)", (owner, job_id, actor, packed(result), now()))
            return {"job_id": job_id, "state": state}
