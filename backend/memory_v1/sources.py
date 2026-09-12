"""User-managed connectors: add a source from the UI instead of an env var.

Credentials go in one direction. A connector is written with its secret, the
secret is stored server-side, and every read path returns `has_secret` instead
of the value — so a compromised page, or a model that can call the read tool,
still cannot exfiltrate a token it never sees.

Each kind declares its own fields, so the UI can render a form it does not have
to hard-code, and the server can reject anything not on the list.
"""
import json
import re
import time
import urllib.parse
import uuid

from .connectors import get_json, github_sync, gotify_sync
from .store import now

URL = re.compile(r"^https?://[^\s/$.?#][^\s]*$")

KINDS = {
    "gotify": {
        "label": "Gotify 通知服务器",
        "fields": [{"name": "url", "label": "服务器地址", "type": "url", "placeholder": "http://127.0.0.1:18080"}],
        "secret": {"name": "client_token", "label": "Client Token（读取用，不是发送用）"},
        "note": "拉取历史与新通知。Client Token 在 Gotify 网页端 Clients 页创建。",
    },
    "github": {
        "label": "GitHub Issues",
        "fields": [{"name": "repo", "label": "仓库", "type": "text", "placeholder": "owner/repo"}],
        "secret": {"name": "token", "label": "Personal Access Token（私有库才需要）", "optional": True},
        "note": "只读导入 Issue，不含 Pull Request，不写回仓库。",
    },
    "rss": {
        "label": "RSS / Atom 订阅",
        "fields": [{"name": "url", "label": "订阅地址", "type": "url", "placeholder": "https://example.com/feed.xml"},
                   {"name": "name", "label": "显示名称", "type": "text", "optional": True}],
        "secret": None,
        "note": "公开订阅源，无需凭据。每次最多导入 50 条。",
    },
}


def describe():
    """Form metadata for the UI. Contains no user data and no secrets."""
    return [{"kind": kind, **{k: v for k, v in spec.items()}} for kind, spec in KINDS.items()]


def check(kind, config):
    spec = KINDS.get(kind)
    if not spec:
        raise ValueError("unknown connector kind")
    allowed = {field["name"] for field in spec["fields"]}
    if set(config) - allowed:
        raise ValueError("unexpected connector field")
    for field in spec["fields"]:
        value = (config.get(field["name"]) or "").strip()
        if not value:
            if field.get("optional"):
                continue
            raise ValueError(f"{field['label']} 不能为空")
        if len(value) > 500:
            raise ValueError("connector field too long")
        if field["type"] == "url" and not URL.fullmatch(value):
            raise ValueError("地址必须是 http(s) URL")
        if field["name"] == "repo" and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
            raise ValueError("仓库格式应为 owner/repo")
        config[field["name"]] = value
    return config


class Sources:
    def __init__(self, store):
        self.store = store
        with store.db() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS memory_connectors (
                owner_id TEXT NOT NULL, id TEXT NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL,
                config TEXT NOT NULL, secret TEXT NOT NULL DEFAULT '', enabled INTEGER NOT NULL DEFAULT 1,
                cursor TEXT NOT NULL DEFAULT '', last_run TEXT, last_result TEXT,
                created_at TEXT NOT NULL, PRIMARY KEY(owner_id,id))""")

    def add(self, owner, kind, config, secret="", name=""):
        config = check(kind, dict(config or {}))
        spec = KINDS[kind]
        secret = (secret or "").strip()
        if spec["secret"] and not secret and not spec["secret"].get("optional"):
            raise ValueError(f"{spec['secret']['label']} 不能为空")
        if not spec["secret"]:
            secret = ""
        if len(secret) > 500:
            raise ValueError("secret too long")
        connector_id = uuid.uuid4().hex
        label = (name or config.get("name") or config.get("repo") or config.get("url") or spec["label"])[:120]
        with self.store.db() as con:
            duplicate = con.execute("SELECT id FROM memory_connectors WHERE owner_id=? AND kind=? AND config=?",
                                    (owner, kind, json.dumps(config, sort_keys=True))).fetchone()
            if duplicate:
                raise ValueError("这个来源已经添加过了")
            con.execute("INSERT INTO memory_connectors(owner_id,id,kind,name,config,secret,created_at) VALUES(?,?,?,?,?,?,?)",
                        (owner, connector_id, kind, label, json.dumps(config, sort_keys=True), secret, now()))
        return {"state": "added", "id": connector_id, "kind": kind, "name": label}

    def list(self, owner):
        """Never returns a secret: only whether one is stored."""
        with self.store.db() as con:
            rows = con.execute("SELECT * FROM memory_connectors WHERE owner_id=? ORDER BY created_at", (owner,)).fetchall()
        return [{"id": r["id"], "kind": r["kind"], "name": r["name"], "config": json.loads(r["config"]),
                 "has_secret": bool(r["secret"]), "enabled": bool(r["enabled"]),
                 "last_run": r["last_run"], "last_result": r["last_result"] or ""} for r in rows]

    def set_enabled(self, owner, connector_id, enabled):
        with self.store.db() as con:
            changed = con.execute("UPDATE memory_connectors SET enabled=? WHERE owner_id=? AND id=?",
                                  (1 if enabled else 0, owner, connector_id)).rowcount
        if not changed:
            raise KeyError(connector_id)
        return {"state": "enabled" if enabled else "disabled", "id": connector_id}

    def remove(self, owner, connector_id):
        """Removes the connector, never the records it already imported."""
        with self.store.db() as con:
            changed = con.execute("DELETE FROM memory_connectors WHERE owner_id=? AND id=?", (owner, connector_id)).rowcount
        if not changed:
            raise KeyError(connector_id)
        return {"state": "removed", "id": connector_id, "reason": "已导入的记录保留，未删除"}

    def run(self, owner, connector_id, *, get=get_json):
        with self.store.db() as con:
            row = con.execute("SELECT * FROM memory_connectors WHERE owner_id=? AND id=?", (owner, connector_id)).fetchone()
        if not row:
            raise KeyError(connector_id)
        config = json.loads(row["config"])
        try:
            if row["kind"] == "gotify":
                result = gotify_sync(self.store, owner, config["url"], row["secret"], get=get)
            elif row["kind"] == "github":
                result = github_sync(self.store, owner, config["repo"], row["secret"], get=get)
            elif row["kind"] == "rss":
                result = rss_sync(self.store, owner, config["url"], config.get("name", ""))
            else:
                raise ValueError("unknown connector kind")
            summary = f"导入 {result.get('imported', 0)} 条"
        except Exception as exc:
            summary = "失败：" + type(exc).__name__
            result = {"imported": 0, "error": type(exc).__name__}
        with self.store.db() as con:
            con.execute("UPDATE memory_connectors SET last_run=?,last_result=? WHERE owner_id=? AND id=?",
                        (now(), summary, owner, connector_id))
        return {"id": connector_id, "kind": row["kind"], "name": row["name"], **result}

    def run_enabled(self, owner):
        return [self.run(owner, item["id"]) for item in self.list(owner) if item["enabled"]]


def rss_sync(store, owner, url, name="", *, limit=50):
    """Read-only feed import. Entry id or link is the dedup key, so re-runs are free."""
    import feedparser
    if not URL.fullmatch(url):
        raise ValueError("RSS 地址必须是 http(s) URL")
    parsed = feedparser.parse(url)
    if getattr(parsed, "bozo", 0) and not parsed.entries:
        raise ValueError("feed could not be parsed")
    source = name or (getattr(parsed.feed, "title", "") or urllib.parse.urlsplit(url).netloc)
    imported = 0
    for entry in parsed.entries[:limit]:
        external = (entry.get("id") or entry.get("link") or entry.get("title") or "")[:160]
        if not external:
            continue
        title = (entry.get("title") or "")[:1000]
        body = entry.get("summary") or entry.get("description") or ""
        text = "\n".join(part for part in (title, body, entry.get("link", "")) if part) or "(empty entry)"
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        occurred = time.strftime("%Y-%m-%dT%H:%M:%SZ", published) if published else None
        ack = store.ingest(owner, {
            "schema_version": "1.0", "kind": "memory.ingest", "request_id": uuid.uuid4().hex,
            "source": {"type": "rss", "instance_id": "rss:" + url, "external_id": external},
            "occurred_at": occurred, "timezone": "UTC",
            "content": {"title": title, "text": text[:100000], "fields": {"feed": source[:200], "link": entry.get("link", "")[:500]}},
            "provenance": "external"})
        imported += not ack["duplicate"]
    return {"imported": imported, "entries": len(parsed.entries[:limit]), "feed": source}
