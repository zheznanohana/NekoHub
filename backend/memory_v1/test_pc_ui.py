"""The desktop renderer must handle every block the contract can emit."""
import json
import os
import sys
import unittest
from pathlib import Path

from backend.memory_v1.blocks import VALIDATOR
from backend.memory_v1.chat import envelope

BLOCKS = [
    {"type": "text", "text": "hello"},
    {"type": "memory.cards", "items": [{"id": "e1", "text": "原文一"}]},
    {"type": "memory.summaries", "items": [{"id": "s1", "level": "day", "period": "2026-09-12",
                                            "summary": "日摘要", "event_ids": ["e1"], "child_ids": []}]},
    {"type": "memory.action", "action_id": "a1", "command": {"command": "memory.delete", "event_id": "e1"},
     "expires_in": 600, "preview": "原文一", "reason": "重复"},
    {"type": "memory.table",
     "columns": ["id", "level", "source", "subject", "relation", "content", "period", "status",
                 "parent_ids", "child_ids", "evidence_ids", "fields"],
     "rows": [{"id": "e1", "level": "raw", "source": "gotify", "subject": "e1", "relation": "original_record",
               "content": "原文一", "period": "2026-09-12T00:00:00Z", "status": "recorded",
               "parent_ids": [], "child_ids": [], "evidence_ids": ["e1"], "fields": {}}],
     "scope": "test"},
    {"type": "memory.network",
     "nodes": [{"id": "e1", "kind": "gotify", "level": "raw", "label": "原文一", "text": "原文一",
                "period": "2026-09-12", "evidence_ids": ["e1"]},
               {"id": "s1", "kind": "summary", "level": "day", "label": "2026-09-12", "text": "日摘要",
                "period": "2026-09-12", "evidence_ids": ["e1"]}],
     "edges": [{"source": "e1", "target": "s1", "kind": "compresses", "label": "压缩汇总"}],
     "scope": "test"},
    {"type": "memory.diary",
     "rows": [{"day": "2026-03-01", "text": "第一天", "version": 1, "updated_at": "2026-03-01T10:00:00+00:00",
               "event_count": 2, "event_ids": ["e1"], "sources": ["gotify"], "summary": "日摘要", "summary_id": "s1"}],
     "scope": "test"},
    {"type": "memory.graph", "data": {"nodes": [{"id": "n1", "kind": "person", "label": "我", "aliases": []}], "facts": []}},
    {"type": "memory.receipt", "data": {"state": "applied"}},
]

try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
except ImportError:  # desktop extras are optional for the headless backend
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 not installed")
class DesktopRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pc = str(Path(__file__).resolve().parents[2] / "pc")
        if pc not in sys.path:
            sys.path.insert(0, pc)
        cls.app = QApplication.instance() or QApplication([])

    def test_every_contract_block_renders(self):
        VALIDATOR.validate(envelope("test", BLOCKS))
        from ui_memory import MemoryPage
        # Rendered one at a time: a total count would hide a block that draws nothing.
        for block in BLOCKS:
            page = MemoryPage()
            page.render([block])
            self.assertGreater(page.cards.count(), 0, block["type"] + " rendered no widget")
        page = MemoryPage()
        page.render(BLOCKS)
        # The network block is what gives the agent a real selection scope.
        self.assertEqual(page.view_context["visible_ids"], ["e1", "s1"])
        self.assertEqual(page.view_context["levels"], ["day", "raw"])

    def test_renderer_covers_every_declared_block_type(self):
        from backend.memory_v1.blocks import BLOCKS as CONTRACT
        declared = {b["properties"]["type"]["const"] for b in CONTRACT}
        self.assertEqual(declared, {b["type"] for b in BLOCKS})


if __name__ == "__main__":
    unittest.main()
