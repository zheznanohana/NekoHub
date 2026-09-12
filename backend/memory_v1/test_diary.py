"""Diary is user-authored ground truth: edits keep history, the model only proposes."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.memory_v1.blocks import VALIDATOR
from backend.memory_v1.chat import COMMAND_VALIDATOR, envelope, render_command
from backend.memory_v1.diary import Diary
from backend.memory_v1.import_legacy import document, run
from backend.memory_v1.store import Conflict, Store

LEGACY = [
    (545, 3, "下载完成 • 26.64 MB", "com.android.chrome\nEhViewer.apk", 5, "2026-03-01T16:45:37.97335463Z"),
    (546, 4, "会议改到周四", "", 8, "2026-03-01T18:00:00.000000000Z"),
    (547, 3, "", None, 5, "2026-03-02T09:00:00.000000000Z"),
]


def legacy_db(folder):
    path = Path(folder) / "nekohub.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, appid INTEGER, title TEXT, message TEXT, priority INTEGER, date TEXT)")
    con.executemany("INSERT INTO messages VALUES (?,?,?,?,?,?)", LEGACY)
    con.commit(); con.close()
    return path


class DiaryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "memory.db")
        self.diary = Diary(self.store)

    def test_edit_keeps_history_and_publishes_each_version(self):
        first = self.diary.write("admin", "2026-03-01", "开始整理项目")
        self.assertEqual((first["state"], first["version"]), ("saved", 1))
        self.assertEqual(self.diary.write("admin", "2026-03-01", "开始整理项目")["state"], "unchanged")
        second = self.diary.write("admin", "2026-03-01", "改主意了，先修后端")
        self.assertEqual(second["version"], 2)
        self.assertNotEqual(second["event_id"], first["event_id"])
        history = self.diary.history("admin", "2026-03-01")
        self.assertEqual([h["version"] for h in history], [1])
        self.assertEqual(history[0]["text"], "开始整理项目")
        # Both versions stay quotable; an edit never erases what it replaced.
        self.assertEqual(self.store.event("admin", first["event_id"])["content"]["text"], "开始整理项目")
        self.assertEqual(self.store.event("admin", second["event_id"])["content"]["text"], "改主意了，先修后端")

    def test_rejects_bad_day_and_empty_text(self):
        for day in ("2026-3-1", "2026/03/01", "", "今天"):
            with self.assertRaises(ValueError):
                self.diary.write("admin", day, "x")
        for text in ("", "   ", "x" * 20001):
            with self.assertRaises(ValueError):
                self.diary.write("admin", "2026-03-01", text)

    def test_rows_join_records_and_never_invent_days(self):
        self.diary.write("admin", "2026-03-01", "第一天")
        run(self.store, "admin", legacy_db(self.folder.name))
        rows = {row["day"]: row for row in self.diary.rows("admin")}
        self.assertEqual(sorted(rows), ["2026-03-01", "2026-03-02"])
        self.assertEqual(rows["2026-03-01"]["text"], "第一天")
        self.assertEqual(rows["2026-03-02"]["text"], "")
        self.assertEqual(rows["2026-03-02"]["version"], 0)
        self.assertIn("import", rows["2026-03-01"]["sources"])
        self.assertEqual(self.diary.rows("admin", start="2026-03-02")[0]["day"], "2026-03-02")
        self.assertEqual([r["day"] for r in self.diary.rows("admin", text="第一天")], ["2026-03-01"])
        VALIDATOR.validate(envelope("t", [self.diary.block("admin")]))

    def test_agent_diary_write_applies_at_once(self):
        command = {"command": "memory.diary.write", "day": "2026-03-01", "text": "模型写的"}
        COMMAND_VALIDATOR.validate(command)
        blocks = render_command(self.store, "admin", command)
        self.assertEqual([b["type"] for b in blocks], ["text", "memory.receipt"])
        self.assertEqual(blocks[1]["data"]["state"], "saved")
        self.assertEqual(self.diary.rows("admin")[0]["text"], "模型写的")

    def test_agent_deletion_still_waits_for_a_click(self):
        event_id = self.diary.write("admin", "2026-03-02", "先写一条")["event_id"]
        blocks = render_command(self.store, "admin", {"command": "memory.delete", "event_id": event_id})
        self.assertEqual(blocks[0]["type"], "memory.action")
        self.assertEqual(len(self.store.search("admin", "先写一条")), 1)
        self.store.confirm_action("admin", blocks[0]["action_id"])
        self.assertEqual(self.store.search("admin", "先写一条"), [])
        with self.assertRaises(Conflict):
            self.store.confirm_action("admin", blocks[0]["action_id"])


class DiaryServiceTests(unittest.TestCase):
    """The confirm endpoint is the only place an agent proposal becomes a diary entry."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.token = "diary-service-token-123456"
        from backend.memory_v1.server import create_app
        self.app = create_app(path=str(Path(self.folder.name) / "memory.db"), token=self.token)
        self.client = self.app.test_client()
        self.headers = {"Authorization": "Bearer " + self.token}
        self.store = self.app.extensions["memory_store"]

    def post(self, path, payload):
        return self.client.post("/api/memory/v1" + path, json=payload, headers=self.headers)

    def test_direct_write_then_read_round_trip(self):
        response = self.post("/diary", {"day": "2026-03-01", "text": "今天接通了记忆后端"})
        self.assertEqual(response.status_code, 200, response.json)
        VALIDATOR.validate(response.json)
        rows = response.json["blocks"][1]["rows"]
        self.assertEqual((rows[0]["day"], rows[0]["text"]), ("2026-03-01", "今天接通了记忆后端"))
        listing = self.client.get("/api/memory/v1/diary?from=2026-03-01&to=2026-03-01", headers=self.headers)
        self.assertEqual(listing.json["blocks"][0]["rows"][0]["version"], 1)
        history = self.client.get("/api/memory/v1/diary/2026-03-01/history", headers=self.headers)
        self.assertEqual(history.json["versions"], [])

    def test_agent_diary_write_through_chat_takes_effect(self):
        response = self.post("/chat", {"schema_version": "1.0",
            "message": '/memory.diary.write {"day":"2026-03-02","text":"模型写的一行"}'})
        self.assertEqual(response.status_code, 200, response.json)
        VALIDATOR.validate(response.json)
        self.assertEqual(response.json["blocks"][1]["data"]["state"], "saved")
        self.assertEqual(Diary(self.store).rows("admin")[0]["text"], "模型写的一行")

    def test_a_deletion_through_chat_still_needs_the_confirm_endpoint(self):
        event_id = Diary(self.store).write("admin", "2026-03-03", "要删掉的一行")["event_id"]
        response = self.post("/chat", {"schema_version": "1.0",
            "message": '/memory.delete {"event_id":"' + event_id + '"}'})
        block = response.json["blocks"][0]
        self.assertEqual(block["type"], "memory.action")
        self.assertEqual(len(self.store.search("admin", "要删掉的一行")), 1)
        self.assertEqual(self.post("/actions/" + block["action_id"] + "/confirm", {}).status_code, 200)
        self.assertEqual(self.store.search("admin", "要删掉的一行"), [])

    def test_rejects_unknown_fields_and_bad_days(self):
        self.assertEqual(self.post("/diary", {"day": "2026-03-01", "text": "x", "owner": "someone"}).status_code, 400)
        self.assertEqual(self.post("/diary", {"day": "3月1日", "text": "x"}).status_code, 400)
        self.assertEqual(self.client.get("/api/memory/v1/diary").status_code, 401)

    def test_legacy_import_needs_server_configuration(self):
        self.assertEqual(self.post("/import/legacy", {}).status_code, 404)


class LegacyImportTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "memory.db")

    def test_import_is_idempotent_and_keeps_original_wording(self):
        path = legacy_db(self.folder.name)
        first = run(self.store, "admin", path)
        self.assertEqual((first["imported"], first["duplicate"], first["failed"]), (3, 0, 0))
        second = run(self.store, "admin", path)
        self.assertEqual((second["imported"], second["duplicate"], second["failed"]), (0, 3, 0))
        texts = {row["text"] for row in self.store.search("admin", "", limit=10)}
        self.assertIn("下载完成 • 26.64 MB\nEhViewer.apk", texts)
        self.assertIn("(empty notification)", texts)

    def test_package_becomes_a_field_not_body_noise(self):
        content = document(dict(zip(("id", "appid", "title", "message", "priority", "date"), LEGACY[0])))["content"]
        self.assertEqual(content["fields"]["app_package"], "com.android.chrome")
        self.assertNotIn("com.android.chrome", content["text"])
        self.assertEqual(content["fields"]["legacy_id"], 545)
        plain = document(dict(zip(("id", "appid", "title", "message", "priority", "date"), LEGACY[1])))["content"]
        self.assertNotIn("app_package", plain["fields"])

    def test_rejects_a_database_that_is_not_the_desktop_app(self):
        other = Path(self.folder.name) / "other.db"
        con = sqlite3.connect(other)
        con.execute("CREATE TABLE x (a)"); con.commit(); con.close()
        with self.assertRaises(ValueError):
            run(self.store, "admin", other)


class WorkerBatchTests(unittest.TestCase):
    """A bulk import must be drainable without changing the queue's semantics."""

    def test_batch_stops_at_the_configured_size_and_when_empty(self):
        from unittest.mock import patch
        from backend.memory_v1 import worker
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "memory.db")
            run(store, "admin", legacy_db(folder))
            calls = []

            def process_one(owner, agent, *, auto_apply=False):
                calls.append(owner)
                return None if len(calls) > 3 else {"job_id": str(len(calls)), "state": "skipped"}

            with patch.object(store, "process_one", process_one),                  patch.dict("os.environ", {"MEMORY_WORKER_BATCH": "10"}),                  patch.object(worker, "Rollups", lambda s: type("R", (), {"summarize": lambda *a: None, "backfill": lambda *a: {"periods": []}})()),                  patch.object(worker, "report", lambda *a: [{"type": "text", "text": "x"}]):
                worker.tick(store, "admin", lambda messages: "{}")
            self.assertEqual(len(calls), 4, "should stop on the first empty queue, not retry")

            calls.clear()
            with patch.object(store, "process_one", lambda *a, **k: (calls.append(1), {"state": "review"})[1]),                  patch.dict("os.environ", {"MEMORY_WORKER_BATCH": "5"}),                  patch.object(worker, "Rollups", lambda s: type("R", (), {"summarize": lambda *a: None, "backfill": lambda *a: {"periods": []}})()),                  patch.object(worker, "report", lambda *a: [{"type": "text", "text": "x"}]):
                worker.tick(store, "admin", lambda messages: "{}")
            self.assertEqual(len(calls), 5)


if __name__ == "__main__":
    unittest.main()
