"""Read-only connectors; endpoints are server-configured, not LLM supplied."""
import json
import re
import urllib.request
import urllib.parse
from .agent import ChatCompletions


def get_json(url, headers):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
        body = response.read(10_000_001)
    if len(body) > 10_000_000:
        raise ValueError("connector response too large")
    return json.loads(body)


def gotify_sync(store, owner, url, token, *, max_pages=5, start_since=0, get=get_json):
    # Reuse provider URL validation, without constructing a request or using its path.
    ChatCompletions(url, token, "validation-only")
    if not token:
        raise ValueError("Gotify Client Token required")
    since, imported, complete = start_since, 0, False
    for _ in range(max_pages):
        data = get(url.rstrip("/") + "/message?" + urllib.parse.urlencode({"limit": 200, "since": since}), {"X-Gotify-Key": token})
        messages = data["messages"]
        if not messages:
            complete = True
            break
        duplicate_page = True
        for msg in messages:
            document = {"schema_version": "1.0", "kind": "memory.ingest", "request_id": "gotify-"+str(msg["id"]),
                        "source": {"type": "gotify", "instance_id": "gotify:"+url.rstrip("/"), "external_id": str(msg["id"])},
                        "occurred_at": msg.get("date"), "timezone": "UTC",
                        "content": {"title": msg.get("title") or "", "text": msg.get("message") or "(empty notification)"}, "provenance": "external"}
            ack = store.ingest(owner, document)
            imported += not ack["duplicate"]
            duplicate_page = duplicate_page and ack["duplicate"]
        next_since = min(int(msg["id"]) for msg in messages)
        if since and next_since >= since:
            raise ValueError("Gotify pagination stalled")
        since = next_since
        if not data.get("paging", {}).get("next"):
            complete = True
            break
    return {"imported": imported, "history_complete": complete, "next_since": since if not complete else None}


def github_sync(store, owner, repository, token="", *, page=1, get=get_json):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("GitHub repository must be owner/repo")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "NekoHub-Memory"}
    if token:
        headers["Authorization"] = "Bearer " + token
    items = get(f"https://api.github.com/repos/{repository}/issues?state=all&sort=updated&direction=desc&per_page=100&page={page}", headers)
    imported = 0
    for item in items:
        if "pull_request" in item:
            continue
        text = f"GitHub Issue #{item['number']}: {item['title']}\n状态: {item['state']}\n{item.get('body') or ''}\n{item['html_url']}"
        document = {"schema_version": "1.0", "kind": "memory.ingest", "request_id": "github-"+str(item["id"]),
                    "source": {"type": "github", "instance_id": "github:"+repository, "external_id": f"{item['id']}:{item['updated_at']}"},
                    "occurred_at": item["updated_at"], "timezone": "UTC", "content": {"title": item["title"], "text": text}, "provenance": "external"}
        imported += not store.ingest(owner, document)["duplicate"]
    return {"imported": imported, "next_page": page+1 if len(items) == 100 else None}
