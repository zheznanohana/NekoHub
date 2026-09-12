"""The agent's toolset: what it can reach, and how it behaves under pressure."""
import json
import tempfile
import unittest
from pathlib import Path

from backend.memory_v1.agent_tools import execute, specs
from backend.memory_v1.pi_runtime import trim
from backend.memory_v1.sources import Sources
from backend.memory_v1.store import Store

GOTIFY_PAGE = {"messages": [{"id": 1, "title": "t", "message": "m", "date": "2026-03-01T00:00:00Z"}], "paging": {}}


class ToolSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "memory.db")

    def test_the_agent_can_see_and_run_connectors(self):
        names = {spec["name"] for spec in specs()}
        self.assertIn("connectors_list", names)
        self.assertIn("connectors_run", names)

    def test_it_cannot_add_change_or_delete_a_connector(self):
        names = {spec["name"] for spec in specs()}
        for forbidden in ("connectors_add", "connectors_remove", "connectors_delete", "memory_confirm"):
            self.assertNotIn(forbidden, names)
        for forbidden in ("connectors_add", "connectors_remove"):
            with self.assertRaises(ValueError):
                execute(self.store, "admin", forbidden, {})

    def test_listing_connectors_never_exposes_a_secret(self):
        Sources(self.store).add("admin", "gotify", {"url": "http://127.0.0.1:18080"}, "SECRET-TOKEN-VALUE")
        listed = execute(self.store, "admin", "connectors_list", {})
        self.assertNotIn("SECRET-TOKEN-VALUE", json.dumps(listed, ensure_ascii=False))
        self.assertTrue(listed[0]["has_secret"])

    def test_running_a_connector_imports_and_reports(self):
        added = Sources(self.store).add("admin", "gotify", {"url": "http://127.0.0.1:18080"}, "token")
        Sources(self.store).run("admin", added["id"], get=lambda url, headers: GOTIFY_PAGE)
        result = execute(self.store, "admin", "connectors_run", {"connector_id": added["id"]})
        self.assertIn("imported", result)
        self.assertNotIn("secret", json.dumps(result, ensure_ascii=False).lower())

    def test_running_an_unknown_connector_raises_instead_of_lying(self):
        with self.assertRaises(KeyError):
            execute(self.store, "admin", "connectors_run", {"connector_id": "does-not-exist"})


class TrimTests(unittest.TestCase):
    """A broad query must come back smaller, never come back as a refusal."""

    def block(self, count):
        return [{"type": "memory.cards",
                 "items": [{"id": f"e{i}", "text": "x" * 400} for i in range(count)]}]

    def test_small_results_pass_through_untouched(self):
        small = self.block(3)
        self.assertEqual(trim(small), small)

    def test_large_results_are_shortened_and_say_so(self):
        trimmed = trim(self.block(500))
        items = trimmed[0]["items"]
        self.assertLess(len(items), 500)
        self.assertGreaterEqual(len(items), 5)
        self.assertIn("仅显示", trimmed[0]["truncated"])
        self.assertLessEqual(len(json.dumps(trimmed, ensure_ascii=False)), 60000)

    def test_something_usable_survives_even_when_one_item_is_huge(self):
        monstrous = [{"type": "memory.cards", "items": [{"id": "e1", "text": "x" * 200000}]}]
        trimmed = trim(monstrous)
        self.assertIsInstance(trimmed, list)
        self.assertTrue(trimmed)

    def test_a_dict_result_is_reported_as_truncated_not_dropped(self):
        self.assertIn("truncated", trim({"huge": "y" * 90000}))


if __name__ == "__main__":
    unittest.main()
