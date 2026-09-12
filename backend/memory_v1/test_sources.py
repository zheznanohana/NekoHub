"""Connectors are user-managed, and their secrets only ever travel inward."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.memory_v1.server import create_app
from backend.memory_v1.sources import Sources, check, describe, rss_sync

GOTIFY_PAGE = {"messages": [{"id": 7, "title": "t", "message": "m", "date": "2026-03-01T00:00:00Z"}], "paging": {}}


class Feed:
    """Minimal stand-in for a parsed feed; no network in tests."""
    bozo = 0

    def __init__(self, entries):
        self.entries = entries
        self.feed = type("F", (), {"title": "示例订阅"})()


class ValidationTests(unittest.TestCase):
    def test_kinds_are_described_without_any_user_data(self):
        described = describe()
        self.assertEqual({k["kind"] for k in described}, {"gotify", "github", "rss"})
        self.assertNotIn("secret_value", json.dumps(described))

    def test_rejects_bad_urls_repos_and_unknown_fields(self):
        for kind, config in [("gotify", {"url": "ftp://x"}), ("gotify", {"url": ""}),
                             ("github", {"repo": "not-a-repo"}), ("rss", {"url": "javascript:alert(1)"}),
                             ("gotify", {"url": "http://a", "extra": "x"}), ("nope", {})]:
            with self.assertRaises(ValueError, msg=f"{kind} {config}"):
                check(kind, dict(config))

    def test_accepts_the_shapes_the_ui_sends(self):
        self.assertEqual(check("gotify", {"url": " http://127.0.0.1:18080 "})["url"], "http://127.0.0.1:18080")
        self.assertEqual(check("github", {"repo": "zheznanohana/NekoHub"})["repo"], "zheznanohana/NekoHub")
        self.assertEqual(check("rss", {"url": "https://example.com/f.xml", "name": ""})["url"], "https://example.com/f.xml")


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.token = "connector-test-token-1234"
        self.app = create_app(path=str(Path(self.folder.name) / "memory.db"), token=self.token)
        self.client = self.app.test_client()
        self.headers = {"Authorization": "Bearer " + self.token}
        self.store = self.app.extensions["memory_store"]
        self.sources = Sources(self.store)

    def api(self, method, path, payload=None):
        call = getattr(self.client, method)
        return call("/api/memory/v1" + path, json=payload, headers=self.headers) if payload is not None \
            else call("/api/memory/v1" + path, headers=self.headers)

    def test_secret_goes_in_and_never_comes_back(self):
        self.sources.add("admin", "gotify", {"url": "http://127.0.0.1:18080"}, "SUPER-SECRET-TOKEN")
        listing = self.api("get", "/connectors").json
        self.assertNotIn("SUPER-SECRET-TOKEN", json.dumps(listing))
        item = listing["items"][0]
        self.assertTrue(item["has_secret"])
        self.assertEqual(item["config"], {"url": "http://127.0.0.1:18080"})
        with self.store.db() as con:
            stored = con.execute("SELECT secret FROM memory_connectors").fetchone()[0]
        self.assertEqual(stored, "SUPER-SECRET-TOKEN")

    def test_a_secret_is_required_when_the_kind_needs_one(self):
        with self.assertRaises(ValueError):
            self.sources.add("admin", "gotify", {"url": "http://127.0.0.1:18080"}, "")
        # GitHub's token is optional: public repositories need no credential.
        self.assertEqual(self.sources.add("admin", "github", {"repo": "a/b"}, "")["state"], "added")

    def test_duplicates_are_refused(self):
        self.sources.add("admin", "rss", {"url": "https://example.com/f.xml"})
        with self.assertRaises(ValueError):
            self.sources.add("admin", "rss", {"url": "https://example.com/f.xml"})

    def test_connectors_are_owner_scoped(self):
        self.sources.add("admin", "rss", {"url": "https://example.com/f.xml"})
        self.assertEqual(self.sources.list("someone-else"), [])
        with self.assertRaises(KeyError):
            self.sources.remove("someone-else", self.sources.list("admin")[0]["id"])

    def test_running_imports_and_records_the_outcome(self):
        added = self.sources.add("admin", "gotify", {"url": "http://127.0.0.1:18080"}, "token")
        result = self.sources.run("admin", added["id"], get=lambda url, headers: GOTIFY_PAGE)
        self.assertEqual(result["imported"], 1)
        self.assertEqual(len(self.store.search("admin", "", limit=10)), 1)
        item = self.sources.list("admin")[0]
        self.assertEqual(item["last_result"], "导入 1 条")
        self.assertTrue(item["last_run"])

    def test_a_broken_connector_is_recorded_not_raised(self):
        added = self.sources.add("admin", "gotify", {"url": "http://127.0.0.1:18080"}, "token")

        def boom(url, headers):
            raise TimeoutError("unreachable")

        result = self.sources.run("admin", added["id"], get=boom)
        self.assertEqual(result["imported"], 0)
        self.assertTrue(self.sources.list("admin")[0]["last_result"].startswith("失败"))

    def test_disabled_connectors_are_skipped_by_the_scheduled_run(self):
        added = self.sources.add("admin", "rss", {"url": "https://example.com/f.xml"})
        self.sources.set_enabled("admin", added["id"], False)
        self.assertEqual(self.sources.run_enabled("admin"), [])

    def test_removing_a_connector_keeps_what_it_imported(self):
        added = self.sources.add("admin", "gotify", {"url": "http://127.0.0.1:18080"}, "token")
        self.sources.run("admin", added["id"], get=lambda url, headers: GOTIFY_PAGE)
        self.sources.remove("admin", added["id"])
        self.assertEqual(self.sources.list("admin"), [])
        self.assertEqual(len(self.store.search("admin", "", limit=10)), 1)

    def test_api_round_trip_add_disable_run_delete(self):
        added = self.api("post", "/connectors", {"kind": "rss", "config": {"url": "https://example.com/f.xml"}})
        self.assertEqual(added.status_code, 200, added.json)
        connector_id = added.json["blocks"][0]["data"]["id"]
        self.assertEqual(self.api("post", f"/connectors/{connector_id}", {"enabled": False}).status_code, 200)
        self.assertFalse(self.api("get", "/connectors").json["items"][0]["enabled"])
        self.assertEqual(self.api("delete", f"/connectors/{connector_id}").status_code, 200)
        self.assertEqual(self.api("get", "/connectors").json["items"], [])

    def test_api_rejects_malformed_requests(self):
        self.assertEqual(self.api("post", "/connectors", {"kind": "rss"}).status_code, 400)
        self.assertEqual(self.api("post", "/connectors", {"kind": "rss", "config": {"url": "x"}}).status_code, 400)
        self.assertEqual(self.api("post", "/connectors", {"kind": "rss", "config": {}, "sneaky": 1}).status_code, 400)
        self.assertEqual(self.client.get("/api/memory/v1/connectors").status_code, 401)

    def test_rss_import_is_idempotent_and_keeps_the_link(self):
        entries = [{"id": "e1", "title": "标题", "summary": "正文", "link": "https://example.com/a"}]
        with patch("feedparser.parse", return_value=Feed(entries)):
            first = rss_sync(self.store, "admin", "https://example.com/f.xml")
            second = rss_sync(self.store, "admin", "https://example.com/f.xml")
        self.assertEqual((first["imported"], second["imported"]), (1, 0))
        record = self.store.event("admin", self.store.search("admin", "标题")[0]["id"])
        self.assertEqual(record["content"]["fields"]["link"], "https://example.com/a")
        self.assertIn("正文", record["content"]["text"])


if __name__ == "__main__":
    unittest.main()
