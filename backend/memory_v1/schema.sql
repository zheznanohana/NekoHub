-- SQLite MVP storage. A relation with provenance is a fact, not a bare edge.
-- Connection factory must execute PRAGMA foreign_keys=ON on EVERY connection.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS memory_events (
  owner_id TEXT NOT NULL, id TEXT NOT NULL,
  source_type TEXT NOT NULL, instance_id TEXT NOT NULL, external_id TEXT NOT NULL,
  text TEXT NOT NULL, raw_json TEXT NOT NULL, content_hash TEXT NOT NULL,
  occurred_at TEXT, received_at TEXT NOT NULL, deleted_at TEXT,
  PRIMARY KEY (owner_id, id), UNIQUE (owner_id, instance_id, external_id)
);
CREATE TABLE IF NOT EXISTS memory_nodes (
  owner_id TEXT NOT NULL, id TEXT NOT NULL, kind TEXT NOT NULL, label TEXT NOT NULL,
  aliases_json TEXT NOT NULL DEFAULT '[]', version INTEGER NOT NULL DEFAULT 1 CHECK(version > 0),
  PRIMARY KEY (owner_id, id)
);
CREATE TABLE IF NOT EXISTS memory_facts (
  owner_id TEXT NOT NULL, id TEXT NOT NULL, subject_id TEXT NOT NULL, predicate TEXT NOT NULL,
  object_node_id TEXT, object_value TEXT, datatype TEXT, unit TEXT,
  status TEXT NOT NULL CHECK(status IN ('candidate','active','superseded','disputed','retracted','archived')),
  epistemic TEXT NOT NULL CHECK(epistemic IN ('observed','reported','inferred')),
  confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
  valid_from TEXT, valid_to TEXT, recorded_at TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1 CHECK(version > 0), supersedes_id TEXT,
  PRIMARY KEY (owner_id, id),
  FOREIGN KEY (owner_id, subject_id) REFERENCES memory_nodes(owner_id, id),
  FOREIGN KEY (owner_id, object_node_id) REFERENCES memory_nodes(owner_id, id),
  FOREIGN KEY (owner_id, supersedes_id) REFERENCES memory_facts(owner_id, id),
  CHECK ((object_node_id IS NOT NULL AND object_value IS NULL AND datatype IS NULL AND unit IS NULL)
      OR (object_node_id IS NULL AND object_value IS NOT NULL AND datatype IS NOT NULL AND datatype IN ('text','datetime','decimal','boolean')))
);
CREATE TABLE IF NOT EXISTS memory_evidence (
  owner_id TEXT NOT NULL, fact_id TEXT NOT NULL, event_id TEXT NOT NULL,
  start_offset INTEGER NOT NULL CHECK(start_offset >= 0),
  end_offset INTEGER NOT NULL CHECK(end_offset > start_offset), quote TEXT NOT NULL,
  PRIMARY KEY(owner_id, fact_id, event_id, start_offset, end_offset),
  FOREIGN KEY(owner_id, fact_id) REFERENCES memory_facts(owner_id, id),
  FOREIGN KEY(owner_id, event_id) REFERENCES memory_events(owner_id, id)
);
CREATE TABLE IF NOT EXISTS memory_changesets (
  owner_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, content_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('pending','applied','rejected')),
  created_at TEXT NOT NULL, applied_at TEXT,
  PRIMARY KEY(owner_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS memory_subject ON memory_facts(owner_id, subject_id, status);
CREATE INDEX IF NOT EXISTS memory_object ON memory_facts(owner_id, object_node_id, status);
CREATE INDEX IF NOT EXISTS memory_time ON memory_facts(owner_id, valid_from, valid_to);
