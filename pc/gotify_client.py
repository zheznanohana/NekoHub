# gotify_client.py
from __future__ import annotations

import time
import threading
from typing import Callable, Dict, Any, List, Optional

import requests


def _norm_base(url: str) -> str:
    url = (url or "").strip()
    while url.endswith("/"):
        url = url[:-1]
    return url


# ---------- SEND (App token) ----------
def send_message(base_url: str, app_token: str, title: str, message: str, priority: int = 5, timeout: int = 10):
    """
    POST /message?token=APP_TOKEN
    """
    base = _norm_base(base_url)
    if not base or not app_token:
        raise ValueError("Missing base_url/app_token")

    url = f"{base}/message"
    r = requests.post(
        url,
        params={"token": app_token},
        json={"title": title, "message": message, "priority": int(priority)},
        timeout=timeout,
    )
    r.raise_for_status()
    j = r.json()
    if not isinstance(j, dict) or "id" not in j:
        raise RuntimeError(f"Unexpected response: {j}")
    return j


# ---------- RECEIVE (Client token) ----------
def fetch_latest(base_url: str, client_token: str, limit: int = 80, timeout: int = 10) -> List[dict]:
    """
    GET /message?limit=LIMIT
    Auth: X-Gotify-Key: CLIENT_TOKEN
    Returns newest-first list usually.
    """
    base = _norm_base(base_url)
    if not base or not client_token:
        return []

    url = f"{base}/message"
    r = requests.get(
        url,
        headers={"X-Gotify-Key": client_token},
        params={"limit": int(limit)},
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()

    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        return data["messages"]
    if isinstance(data, list):
        return data
    return []


def filter_newer(msgs: List[dict], last_id: int) -> List[dict]:
    out: List[dict] = []
    for m in msgs:
        try:
            mid = int(m.get("id", 0))
        except Exception:
            mid = 0
        if mid > int(last_id):
            out.append(m)
    out.sort(key=lambda x: int(x.get("id", 0)))
    return out


class GotifyReceiver:
    """
    Stable polling receiver.
    Uses CLIENT token (read).
    """

    def __init__(
        self,
        base_url: str,
        client_token: str,
        on_message: Callable[[Dict[str, Any]], None],
        on_status: Optional[Callable[[str], None]] = None,
        poll_seconds: int = 2,
        limit: int = 80,
    ):
        self.base_url = _norm_base(base_url)
        self.client_token = (client_token or "").strip()
        self.on_message = on_message
        self.on_status = on_status or (lambda _s: None)

        self.poll_seconds = max(2, int(poll_seconds))
        self.limit = max(10, int(limit))

        self._stop = threading.Event()
        self._last_id = 0

    def set_last_id(self, last_id: int):
        try:
            self._last_id = max(self._last_id, int(last_id))
        except Exception:
            pass

    def stop(self):
        self._stop.set()

    def run_forever(self):
        if not self.base_url or not self.client_token:
            self.on_status("Missing Gotify URL / Receive Token (Client).")
            return

        self.on_status("Listening…")

        while not self._stop.is_set():
            try:
                msgs = fetch_latest(self.base_url, self.client_token, limit=self.limit)
                new_msgs = filter_newer(msgs, self._last_id)
                if new_msgs:
                    try:
                        self._last_id = max(self._last_id, max(int(m.get("id", 0)) for m in new_msgs))
                    except Exception:
                        pass
                    for m in new_msgs:
                        self.on_message(m)
            except Exception as e:
                self.on_status(f"Polling error: {e}")

            for _ in range(self.poll_seconds * 10):
                if self._stop.is_set():
                    break
                time.sleep(0.1)