"""Imported history needs layers above it, or the graph is a pile of dots."""
import json
import tempfile
import unittest
from pathlib import Path

from backend.memory_v1.network import network
from backend.memory_v1.rollup import Rollups
from backend.memory_v1.store import Store


def model(messages):
    """Summarises whatever it is given, echoing every source id back."""
    job = json.loads(messages[1]["content"])
    return json.dumps({"summary": f"{job['level']} {job['period']} 共 {len(job['sources'])} 条",
                       "source_ids": [s["id"] for s in job["sources"]]}, ensure_ascii=False)


def ingest(store, key, day):
    store.ingest("admin", {
        "schema_version": "1.0", "kind": "memory.ingest", "request_id": key,
        "source": {"type": "import", "instance_id": "legacy", "external_id": key},
        "occurred_at": f"{day}T09:00:00Z", "timezone": "UTC",
        "content": {"title": key, "text": f"{day} 的记录 {key}"}, "provenance": "external"})


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "memory.db")
        self.rollups = Rollups(self.store)
        for index, day in enumerate(("2026-03-02", "2026-03-03", "2026-03-04")):
            for n in range(2):
                ingest(self.store, f"e{index}{n}", day)

    def test_periods_are_derived_from_records_only(self):
        self.assertEqual(self.rollups.periods("admin", "day"), ["2026-03-04", "2026-03-03", "2026-03-02"])
        self.assertEqual(self.rollups.periods("admin", "month"), ["2026-03"])
        self.assertEqual(self.rollups.periods("empty", "day"), [])

    def test_missing_lists_every_uncovered_period(self):
        gaps = self.rollups.missing("admin")
        self.assertEqual([g["level"] for g in gaps], ["day", "day", "day", "week", "month"])
        self.rollups.backfill("admin", model, limit=40)
        self.assertEqual(self.rollups.missing("admin"), [])

    def test_a_sunday_belongs_to_the_previous_iso_week(self):
        ingest(self.store, "sunday", "2026-03-01")   # Sunday: ISO week 2026-W09
        weeks = [g["period"] for g in self.rollups.missing("admin") if g["level"] == "week"]
        self.assertEqual(sorted(weeks), ["2026-W09", "2026-W10"])

    def test_backfill_respects_its_limit_and_reports_the_remainder(self):
        first = self.rollups.backfill("admin", model, limit=2)
        self.assertEqual(len(first["periods"]), 2)
        self.assertEqual(first["remaining"], len(self.rollups.missing("admin")))
        self.rollups.backfill("admin", model, limit=40)
        self.assertEqual(self.rollups.backfill("admin", model)["periods"], [])

    def test_days_are_summarised_before_the_weeks_that_reuse_them(self):
        self.rollups.backfill("admin", model, limit=40)
        summaries = {(s["level"], s["period"]): s for s in self.rollups.search("admin")}
        week = next(s for (level, _), s in summaries.items() if level == "week")
        day_ids = {s["id"] for (level, _), s in summaries.items() if level == "day"}
        self.assertTrue(set(week["child_ids"]) <= day_ids)
        self.assertTrue(week["child_ids"], "the week should compress the day summaries, not raw records")

    def test_a_failing_period_does_not_abort_the_rest(self):
        calls = []

        def flaky(messages):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("provider hiccup")
            return model(messages)

        result = self.rollups.backfill("admin", flaky, limit=3)
        self.assertEqual(result["periods"][0]["state"], "failed")
        self.assertEqual([p["state"] for p in result["periods"][1:]], ["summarized", "summarized"])

    def test_backfill_is_what_turns_loose_records_into_a_connected_graph(self):
        before = network(self.store, "admin")
        self.assertEqual(before["edges"], [], "no summaries yet means nothing to connect")
        self.rollups.backfill("admin", model, limit=40)
        after = network(self.store, "admin")
        self.assertTrue(after["edges"])
        self.assertTrue(all(edge["kind"] == "compresses" for edge in after["edges"]))
        linked = {edge["source"] for edge in after["edges"]} | {edge["target"] for edge in after["edges"]}
        self.assertEqual(len(linked), len(after["nodes"]), "every node should hang off the compression tree")


if __name__ == "__main__":
    unittest.main()
