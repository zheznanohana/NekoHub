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
# Etherscan's multichain endpoint; the chain id is the only thing that varies.
CHAINS = {"ETH": 1, "Polygon": 137, "Arbitrum": 42161, "Base": 8453,
          "Optimism": 10, "BSC": 56, "Linea": 59144, "Scroll": 534352}

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
    "imap": {
        "label": "邮箱（IMAP 只读）",
        "fields": [{"name": "host", "label": "IMAP 服务器", "type": "text", "placeholder": "imap.qq.com"},
                   {"name": "user", "label": "邮箱账号", "type": "text", "placeholder": "you@example.com"},
                   {"name": "port", "label": "端口", "type": "text", "placeholder": "993", "optional": True}],
        "secret": {"name": "password", "label": "密码或授权码"},
        "note": "只读取收件箱最近若干封的发件人、主题与正文摘要。不发信，不删信，不改标记。",
    },
    "web3": {
        "label": "链上地址（Etherscan 兼容）",
        "fields": [{"name": "address", "label": "钱包地址", "type": "text", "placeholder": "0x..."},
                   {"name": "chain", "label": "链", "type": "text", "placeholder": "ETH / Polygon / Arbitrum", "optional": True}],
        "secret": {"name": "api_key", "label": "Etherscan API Key"},
        "note": "只读最近交易记录。永远不发起交易，也不接受私钥。",
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
        if field["name"] == "address" and not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
            raise ValueError("地址格式应为 0x 开头的 40 位十六进制")
        if field["name"] == "host" and not re.fullmatch(r"[A-Za-z0-9.-]{3,253}", value):
            raise ValueError("IMAP 服务器格式不正确")
        if field["name"] == "port" and not (value.isdigit() and 1 <= int(value) <= 65535):
            raise ValueError("端口必须是 1-65535")
        if field["name"] == "chain" and value not in CHAINS:
            raise ValueError("暂不支持这条链：" + ", ".join(CHAINS))
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
            elif row["kind"] == "imap":
                result = imap_sync(self.store, owner, config["host"], config["user"], row["secret"], int(config.get("port") or 993))
            elif row["kind"] == "web3":
                result = web3_sync(self.store, owner, config["address"], row["secret"], config.get("chain") or "ETH", get=get)
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


def imap_sync(store, owner, host, user, password, port=993, *, limit=25):
    """Read-only inbox pull. Never sends, deletes, or changes a message flag."""
    import email
    import imaplib
    from email.header import decode_header, make_header
    mail = imaplib.IMAP4_SSL(host, port)
    imported, uids = 0, []
    try:
        mail.login(user, password)
        mail.select("INBOX", readonly=True)
        ok, data = mail.search(None, "ALL")
        if ok != "OK":
            raise ValueError("IMAP search failed")
        uids = data[0].split()[-limit:]
        for uid in uids:
            ok, raw = mail.fetch(uid, "(RFC822)")
            if ok != "OK" or not raw or not isinstance(raw[0], tuple):
                continue
            message = email.message_from_bytes(raw[0][1])
            subject = str(make_header(decode_header(message.get("Subject", "")))).strip()
            sender = str(make_header(decode_header(message.get("From", "")))).strip()
            body = ""
            for part in message.walk():
                if part.get_content_type() == "text/plain" and not part.get_filename():
                    try:
                        body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
                    except (AttributeError, LookupError):
                        body = ""
                    break
            parts = [p for p in (subject, ("发件人：" + sender) if sender else "", body.strip()) if p]
            text = "\\n".join(parts) or "(empty mail)"
            # Message-ID is stable across re-fetches; the mailbox UID is not.
            external = (message.get("Message-ID") or (user + ":" + uid.decode()))[:160]
            ack = store.ingest(owner, {
                "schema_version": "1.0", "kind": "memory.ingest", "request_id": uuid.uuid4().hex,
                "source": {"type": "imap", "instance_id": "imap:" + user + "@" + host, "external_id": external},
                "occurred_at": None, "timezone": "UTC",
                "content": {"title": subject[:1000], "text": text[:100000],
                            "fields": {"from": sender[:200], "mailbox": user[:200]}},
                "provenance": "external"})
            imported += not ack["duplicate"]
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return {"imported": imported, "entries": len(uids), "feed": user}


def web3_sync(store, owner, address, api_key, chain="ETH", *, limit=25, get=get_json):
    """Read-only transaction history. No key material, no signing, no sending."""
    if chain not in CHAINS:
        raise ValueError("unsupported chain")
    query = urllib.parse.urlencode({"chainid": CHAINS[chain], "module": "account", "action": "txlist",
                                    "address": address, "page": 1, "offset": limit,
                                    "sort": "desc", "apikey": api_key})
    data = get("https://api.etherscan.io/v2/api?" + query, {"User-Agent": "NekoHub-Memory"})
    rows = data.get("result") if isinstance(data.get("result"), list) else []
    if not rows and str(data.get("status")) != "1" and data.get("message") not in ("No transactions found", "OK"):
        raise ValueError("chain query failed: " + str(data.get("message"))[:80])
    imported = 0
    for tx in rows:
        value = int(tx.get("value") or 0) / 1e18
        direction = "转出" if (tx.get("from") or "").lower() == address.lower() else "转入"
        text = "\\n".join([
            chain + " " + direction + " " + format(value, ".6f") + " 原生代币",
            "from " + str(tx.get("from")),
            "to " + str(tx.get("to")),
            "hash " + str(tx.get("hash"))])
        occurred = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(tx.get("timeStamp") or 0))) if tx.get("timeStamp") else None
        ack = store.ingest(owner, {
            "schema_version": "1.0", "kind": "memory.ingest", "request_id": uuid.uuid4().hex,
            "source": {"type": "web3", "instance_id": "web3:" + chain + ":" + address.lower(), "external_id": (tx.get("hash") or "")[:160]},
            "occurred_at": occurred, "timezone": "UTC",
            "content": {"title": chain + " " + direction + " " + format(value, ".6f"), "text": text,
                        "fields": {"chain": chain, "direction": direction, "value": value,
                                   "hash": (tx.get("hash") or "")[:160]}},
            "provenance": "external"})
        imported += not ack["duplicate"]
    return {"imported": imported, "entries": len(rows), "feed": chain + " " + address[:10]}
