"""Retrieval for the memory store: BM25 over segmented text, optional vectors.

Why not the obvious choices. FTS5's trigram tokenizer never matches a
two-character Chinese query, and unicode61 treats a whole Han run as one token,
so a query for 群组 misses text containing 在群组. Both fail on exactly the
queries this corpus gets. So CJK is segmented to one token per character at
index *and* query time and matched as a phrase, which restores substring
behaviour while keeping BM25 ranking. Latin words stay whole and are lowercased.

Lexical matching still cannot bridge 电报 to Telegram. That needs vectors, so an
OpenAI-compatible embeddings endpoint can be configured; when it is, results are
fused with reciprocal rank fusion. Without it the index is still far better than
a substring scan, and the caller is told which mode actually ran.
"""
import json
import math
import os
import re
import urllib.error
import urllib.request
from array import array

CJK = (
    (0x3040, 0x30FF),    # kana
    (0x3400, 0x4DBF),    # CJK ext A
    (0x4E00, 0x9FFF),    # CJK unified
    (0xF900, 0xFAFF),    # compatibility ideographs
    (0xAC00, 0xD7AF),    # hangul syllables
    (0x20000, 0x2FA1F),  # CJK ext B and beyond
)
WORD = re.compile(r"[0-9A-Za-z_]+")
PIECE = re.compile(r"[0-9A-Za-z_]+|.", re.S)
RUN = re.compile(r"[0-9A-Za-z_]+|[^0-9A-Za-z_\s]+", re.S)
FTS_OPTIONS = "unicode61 remove_diacritics 2"
RRF_K = 60


def is_cjk(char):
    point = ord(char)
    return any(low <= point <= high for low, high in CJK)


def segment(text):
    """One token per CJK character, Latin/digit runs kept whole and lowercased."""
    out = []
    for match in PIECE.finditer(text or ""):
        piece = match.group()
        if WORD.fullmatch(piece):
            out.append(piece.lower())
        elif is_cjk(piece):
            out.append(piece)
    return " ".join(out)


def quote(token):
    return '"' + token.replace('"', '""') + '"'


def match_expression(text):
    """CJK runs become phrases, Latin words prefix terms. Empty means no query."""
    parts = []
    for match in RUN.finditer(text or ""):
        piece = match.group()
        if WORD.fullmatch(piece):
            parts.append(quote(piece.lower()) + "*")
            continue
        run = [c for c in piece if is_cjk(c)]
        if len(run) == 1:
            parts.append(quote(run[0]))
        elif run:
            parts.append(quote(" ".join(run)))
    return " AND ".join(parts)


def normalise(values):
    vector = array("f", values)
    length = math.sqrt(sum(v * v for v in vector)) or 1.0
    return array("f", (v / length for v in vector))


def unpack(blob):
    return array("f", blob)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b)) if len(a) == len(b) else -1.0


def fuse(*rankings):
    """Reciprocal rank fusion: order-based, so unrelated score scales cannot skew it."""
    scores = {}
    for ranking in rankings:
        for position, event_id in enumerate(ranking):
            scores[event_id] = scores.get(event_id, 0.0) + 1.0 / (RRF_K + position + 1)
    return sorted(scores, key=lambda event_id: -scores[event_id])


class LocalEmbeddings:
    """On-device ONNX embeddings. No key, no network at query time, no data leaves.

    The model is loaded on first use rather than at import, so a service that
    never runs a semantic query never pays the load, and a missing model file
    surfaces as a degraded search instead of a failed startup.
    """

    def __init__(self, model, cache_dir=None):
        self.model = model
        self.cache_dir = cache_dir or os.getenv("MEMORY_EMBED_CACHE") or None
        self._encoder = None

    def encoder(self):
        if self._encoder is None:
            from fastembed import TextEmbedding
            self._encoder = TextEmbedding(model_name=self.model, cache_dir=self.cache_dir)
        return self._encoder

    def embed(self, texts):
        try:
            vectors = list(self.encoder().embed([t[:6000] for t in texts]))
        except Exception as exc:
            raise RuntimeError("local embedding failure: " + type(exc).__name__) from None
        if len(vectors) != len(texts):
            raise RuntimeError("local embedder returned the wrong number of vectors")
        return [normalise(vector.tolist()) for vector in vectors]


def embeddings_from_env():
    """Local model, remote endpoint, or nothing at all — in that order of preference."""
    model = os.getenv("MEMORY_EMBED_MODEL")
    if not model:
        return None
    backend = (os.getenv("MEMORY_EMBED_BACKEND") or "").strip().lower()
    if backend == "local" or (not backend and not os.getenv("MEMORY_EMBED_BASE_URL")):
        return LocalEmbeddings(model)
    return Embeddings.from_env()


class Embeddings:
    """OpenAI-compatible /embeddings adapter. Never constructed unless configured."""

    def __init__(self, base_url, api_key, model, timeout=30):
        from .agent import ChatCompletions
        ChatCompletions(base_url, api_key, model)  # reuse URL and credential validation
        self.url = base_url.rstrip("/") + "/embeddings"
        self.key, self.model, self.timeout = api_key, model, timeout

    @classmethod
    def from_env(cls):
        base, model = os.getenv("MEMORY_EMBED_BASE_URL"), os.getenv("MEMORY_EMBED_MODEL")
        if not base or not model:
            return None
        try:
            return cls(base, os.getenv("MEMORY_EMBED_API_KEY", ""), model)
        except ValueError:
            return None

    def embed(self, texts):
        payload = {"model": self.model, "input": [t[:6000] for t in texts]}
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        request = urllib.request.Request(self.url, json.dumps(payload).encode(), headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read(20_000_001))
            items = sorted(data["data"], key=lambda item: item["index"])
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
            raise RuntimeError("embedding provider failure: " + type(exc).__name__) from None
        if len(items) != len(texts):
            raise RuntimeError("embedding provider returned the wrong number of vectors")
        return [normalise(item["embedding"]) for item in items]


class Index:
    def __init__(self, store, embeddings=None):
        self.store = store
        self.embeddings = embeddings
        with store.db() as con:
            con.executescript(f"""
              CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
                USING fts5(body, tokenize='{FTS_OPTIONS}');
              CREATE TABLE IF NOT EXISTS memory_fts_map (
                rowid INTEGER PRIMARY KEY, owner_id TEXT NOT NULL, event_id TEXT NOT NULL,
                content_hash TEXT NOT NULL, UNIQUE(owner_id,event_id));
              CREATE TABLE IF NOT EXISTS memory_vectors (
                owner_id TEXT NOT NULL, event_id TEXT NOT NULL, model TEXT NOT NULL,
                content_hash TEXT NOT NULL, vector BLOB NOT NULL,
                PRIMARY KEY(owner_id,event_id));
            """)

    # ---------- indexing ----------

    def sync(self, owner, limit=5000):
        """Index new or changed events, drop rows for deleted ones. Idempotent."""
        added = removed = 0
        with self.store.db() as con:
            live = {r["id"]: r["content_hash"] for r in con.execute(
                "SELECT id,content_hash FROM memory_events WHERE owner_id=? AND deleted_at IS NULL", (owner,))}
            indexed = {r["event_id"]: r for r in con.execute(
                "SELECT rowid,event_id,content_hash FROM memory_fts_map WHERE owner_id=?", (owner,))}
            for event_id, row in indexed.items():
                if live.get(event_id) != row["content_hash"]:
                    con.execute("DELETE FROM memory_fts WHERE rowid=?", (row["rowid"],))
                    con.execute("DELETE FROM memory_fts_map WHERE rowid=?", (row["rowid"],))
                    removed += 1
            current = {e for e, r in indexed.items() if live.get(e) == r["content_hash"]}
            missing = [e for e in live if e not in current]
            for event_id in missing[:limit]:
                text = con.execute("SELECT text FROM memory_events WHERE owner_id=? AND id=?", (owner, event_id)).fetchone()[0]
                cursor = con.execute("INSERT INTO memory_fts(body) VALUES(?)", (segment(text),))
                con.execute("INSERT INTO memory_fts_map(rowid,owner_id,event_id,content_hash) VALUES(?,?,?,?)",
                            (cursor.lastrowid, owner, event_id, live[event_id]))
                added += 1
            con.execute("""DELETE FROM memory_vectors WHERE owner_id=? AND event_id NOT IN
                           (SELECT event_id FROM memory_fts_map WHERE owner_id=?)""", (owner, owner))
        return {"indexed": added, "dropped": removed, "pending": max(0, len(missing) - added)}

    def embed_pending(self, owner, batch=64):
        """Vectorise events with no current vector. A no-op without a provider."""
        if not self.embeddings:
            return {"state": "disabled", "embedded": 0, "pending": 0}
        with self.store.db() as con:
            rows = [dict(r) for r in con.execute("""
                SELECT e.id, e.text, e.content_hash FROM memory_events e
                LEFT JOIN memory_vectors v ON v.owner_id=e.owner_id AND v.event_id=e.id
                  AND v.content_hash=e.content_hash AND v.model=?
                WHERE e.owner_id=? AND e.deleted_at IS NULL AND v.event_id IS NULL
                ORDER BY e.received_at DESC LIMIT ?""", (self.embeddings.model, owner, batch))]
            remaining = con.execute("""
                SELECT count(*) FROM memory_events e
                LEFT JOIN memory_vectors v ON v.owner_id=e.owner_id AND v.event_id=e.id
                  AND v.content_hash=e.content_hash AND v.model=?
                WHERE e.owner_id=? AND e.deleted_at IS NULL AND v.event_id IS NULL""",
                (self.embeddings.model, owner)).fetchone()[0]
        if not rows:
            return {"state": "current", "embedded": 0, "pending": 0}
        vectors = self.embeddings.embed([r["text"] for r in rows])
        with self.store.db() as con:
            for row, vector in zip(rows, vectors):
                con.execute("INSERT OR REPLACE INTO memory_vectors VALUES(?,?,?,?,?)",
                            (owner, row["id"], self.embeddings.model, row["content_hash"], vector.tobytes()))
        return {"state": "embedded", "embedded": len(rows), "pending": max(0, remaining - len(rows))}

    # ---------- querying ----------

    def lexical(self, owner, text, limit):
        expression = match_expression(text)
        if not expression:
            return []
        with self.store.db() as con:
            try:
                rows = con.execute("""
                    SELECT m.event_id FROM memory_fts f JOIN memory_fts_map m ON m.rowid=f.rowid
                    WHERE memory_fts MATCH ? AND m.owner_id=? ORDER BY bm25(memory_fts) LIMIT ?""",
                    (expression, owner, limit)).fetchall()
            except Exception:
                return []  # a malformed MATCH must degrade, never take down the query
        return [r[0] for r in rows]

    def semantic(self, owner, text, limit):
        if not self.embeddings:
            return []
        try:
            query = self.embeddings.embed([text])[0]
        except (RuntimeError, IndexError):
            return []
        with self.store.db() as con:
            rows = con.execute("SELECT event_id,vector FROM memory_vectors WHERE owner_id=? AND model=?",
                               (owner, self.embeddings.model)).fetchall()
        scored = sorted(((dot(query, unpack(blob)), event_id) for event_id, blob in rows), reverse=True)
        return [event_id for _, event_id in scored[:limit]]

    def neighbours(self, owner, ids, top_k=3, threshold=0.62):
        """Nearest vector neighbours among `ids`, for drawing similarity links.

        Scoped to the ids already on screen so the cost stays quadratic in the
        visible graph, not in the whole store. Returns (a, b, score) with a < b
        so each undirected pair appears once.
        """
        if not self.embeddings or len(ids) < 2:
            return []
        wanted = set(ids)
        with self.store.db() as con:
            rows = [(r[0], unpack(r[1])) for r in con.execute(
                "SELECT event_id,vector FROM memory_vectors WHERE owner_id=? AND model=?",
                (owner, self.embeddings.model)) if r[0] in wanted]
        pairs = {}
        for i, (a, va) in enumerate(rows):
            scored = []
            for j, (b, vb) in enumerate(rows):
                if i == j:
                    continue
                score = dot(va, vb)
                if score >= threshold:
                    scored.append((score, b))
            for score, b in sorted(scored, reverse=True)[:top_k]:
                key = (a, b) if a < b else (b, a)
                pairs[key] = max(pairs.get(key, 0.0), score)
        return [(a, b, score) for (a, b), score in sorted(pairs.items(), key=lambda kv: -kv[1])]

    def search(self, owner, text, limit=30):
        """Returns (event_ids in rank order, mode). An empty query is the caller's job."""
        self.sync(owner)
        lexical = self.lexical(owner, text, limit * 3)
        semantic = self.semantic(owner, text, limit * 3)
        if semantic:
            return fuse(lexical, semantic)[:limit], "hybrid"
        return lexical[:limit], "lexical"
