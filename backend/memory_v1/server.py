"""Standalone local runner; the same blueprint is mounted in NekoHub web."""
import os
import hmac
from functools import wraps
from pathlib import Path
from flask import Flask, request, abort
from .api import make_blueprint
from .store import Store


def create_app(*, path=None, token=None, complete=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    token = token or os.environ["MEMORY_SERVICE_TOKEN"]
    if len(token) < 16:
        raise ValueError("service token must contain at least 16 characters")
    store = Store(path or os.getenv("MEMORY_DB_PATH", str(Path(__file__).with_name("memory.db"))))
    def authenticate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not hmac.compare_digest(request.headers.get("Authorization", ""), "Bearer "+token):
                abort(401)
            return fn(*args, **kwargs)
        return wrapped
    app.register_blueprint(make_blueprint(store, authenticate, lambda: "admin", complete), url_prefix="/api/memory/v1")
    app.extensions["memory_store"] = store
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.getenv("MEMORY_PORT", "18081")), debug=False)
