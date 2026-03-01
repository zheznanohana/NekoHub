# gotify_ws.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import threading
import time
import urllib.parse
from typing import Callable, Optional, Any

import websocket


def _make_ws_url(base_url: str, token: str) -> str:
    """
    Gotify websocket stream:
      ws(s)://host/stream?token=CLIENT_TOKEN
    base_url examples:
      https://notify.example.com
      https://notify.example.com/
      https://notify.example.com/#/
    """
    base_url = (base_url or "").strip()
    if not base_url:
        raise ValueError("Missing gotify_url")

    # strip fragments
    base_url = base_url.split("#", 1)[0].rstrip("/")

    # scheme -> ws/wss
    if base_url.startswith("https://"):
        ws_base = "wss://" + base_url[len("https://") :]
    elif base_url.startswith("http://"):
        ws_base = "ws://" + base_url[len("http://") :]
    elif base_url.startswith("wss://") or base_url.startswith("ws://"):
        ws_base = base_url
    else:
        # assume https if no scheme
        ws_base = "wss://" + base_url

    qs = urllib.parse.urlencode({"token": token})
    return f"{ws_base}/stream?{qs}"


class GotifyWSReceiver:
    """
    Gotify websocket receiver.

    兼容历史参数（关键！）：
      token=..., recv_token=..., gotify_key=..., api_key=...
      on_state=... (旧名)  -> 等价 on_status=...
      on_status=...
      on_message=...
      on_error=...

    Usage:
      r = GotifyWSReceiver(
            base_url,
            token=recv_token,
            on_message=...,
            on_state=...,
            on_error=...
          )
      r.start()
    """

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        recv_token: Optional[str] = None,
        gotify_key: Optional[str] = None,
        api_key: Optional[str] = None,
        on_message: Optional[Callable[[dict], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_state: Optional[Callable[[str], None]] = None,  # ✅ 兼容旧参数名
        on_error: Optional[Callable[[object], None]] = None,
        reconnect_delay: float = 2.0,
        **_kwargs: Any,  # ✅ 吃掉任何未知参数，永不再报 “unexpected keyword”
    ):
        self.base_url = (base_url or "").strip()

        # accept many token names
        self.token = (recv_token or token or gotify_key or api_key or "").strip()

        # on_state is alias of on_status
        self.on_message = on_message
        self.on_status = on_status or on_state
        self.on_error = on_error

        self.reconnect_delay = max(0.5, float(reconnect_delay))

        self._t: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._ws: Optional[websocket.WebSocketApp] = None

    def start(self):
        if self._t and self._t.is_alive():
            return
        self._stop.clear()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def stop(self):
        self._stop.set()
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass

    # ---------------- internals ----------------
    def _emit_status(self, s: str):
        try:
            if self.on_status:
                self.on_status(s)
        except Exception:
            pass

    def _emit_error(self, e: object):
        try:
            if self.on_error:
                self.on_error(e)
        except Exception:
            pass

    def _run(self):
        if not self.base_url or not self.token:
            self._emit_status("WS: missing gotify_url or recv token")
            return

        ws_url = _make_ws_url(self.base_url, self.token)

        def _on_open(_ws):
            self._emit_status("WS: connected")

        def _on_close(_ws, status_code, msg):
            self._emit_status(f"WS: closed ({status_code}) {msg or ''}".strip())

        def _on_error(_ws, err):
            self._emit_error(err)
            self._emit_status(f"WS: error {err}")

        def _on_message(_ws, message: str):
            try:
                obj = json.loads(message)
            except Exception:
                obj = {"raw": message}
            try:
                if self.on_message:
                    self.on_message(obj)
            except Exception as e:
                self._emit_error(e)

        while not self._stop.is_set():
            try:
                self._emit_status(f"WS: connecting {ws_url}")
                self._ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=_on_open,
                    on_close=_on_close,
                    on_error=_on_error,
                    on_message=_on_message,
                )
                self._ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                self._emit_error(e)
                self._emit_status(f"WS: run error {e}")

            if self._stop.is_set():
                break
            time.sleep(self.reconnect_delay)