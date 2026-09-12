"""Retrieval must beat substring matching on the queries this corpus gets."""
import tempfile
import unittest
from pathlib import Path

from backend.memory_v1.retrieval import Index, fuse, match_expression, normalise, segment
from backend.memory_v1.store import Store

CORPUS = {
    "chat": "无界 KING 在群组 无界云居民福利群 已置顶一张图片",
    "telegram": "Bpqyx 在 Telegram 发来一张图片",
    "download": "已下载 13.32 MB，共 26.64 MB EhViewer-2.0.1.5.apk",
    "meeting": "会议改到周四下午三点，地点换到二楼",
    "quiet": "天气很好",
}


def ingest(store, key, text):
    return store.ingest("admin", {
        "schema_version": "1.0", "kind": "memory.ingest", "request_id": key,
        "source": {"type": "manual", "instance_id": "test", "external_id": key},
        "occurred_at": "2026-03-01T00:00:00Z", "timezone": "UTC",
        "content": {"title": key, "text": text}, "provenance": "user_authored"})["event_id"]


class SegmentationTests(unittest.TestCase):
    def test_cjk_splits_per_character_and_latin_stays_whole(self):
        self.assertEqual(segment("在群组 Telegram 图片"), "在 群 组 telegram 图 片")
        self.assertEqual(segment("已下载 13.32 MB"), "已 下 载 13 32 mb")

    def test_query_builds_phrases_for_cjk_and_prefixes_for_latin(self):
        self.assertEqual(match_expression("群组"), '"群 组"')
        self.assertEqual(match_expression("会"), '"会"')
        self.assertEqual(match_expression("apk"), '"apk"*')
        self.assertEqual(match_expression("Telegram 图片"), '"telegram"* AND "图 片"')
        self.assertEqual(match_expression("   "), "")

    def test_quotes_in_a_query_cannot_break_the_match_expression(self):
        self.assertEqual(match_expression('a"b'), '"a"* AND "b"*')


class LexicalTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "memory.db")
        self.ids = {key: ingest(self.store, key, text) for key, text in CORPUS.items()}

    def find(self, query):
        return {row["id"] for row in self.store.search("admin", query, limit=50)}

    def test_two_character_chinese_query_matches_mid_string(self):
        # The exact case FTS5 trigram cannot do and unicode61 tokenising cannot do.
        self.assertEqual(self.find("群组"), {self.ids["chat"]})
        self.assertEqual(self.find("福利"), {self.ids["chat"]})
        self.assertEqual(self.find("下载"), {self.ids["download"]})

    def test_latin_is_case_insensitive_and_prefix_matched(self):
        self.assertEqual(self.find("telegram"), {self.ids["telegram"]})
        self.assertEqual(self.find("TELEGRAM"), {self.ids["telegram"]})
        self.assertEqual(self.find("ehviewer"), {self.ids["download"]})

    def test_multiple_terms_require_all_of_them(self):
        self.assertEqual(self.find("会议 周四"), {self.ids["meeting"]})
        self.assertEqual(self.find("会议 火星"), set())

    def test_empty_query_returns_latest_records_not_nothing(self):
        self.assertEqual(len(self.store.search("admin", "", limit=50)), len(CORPUS))
        self.assertEqual(len(self.store.search("admin", "   ", limit=50)), len(CORPUS))

    def test_results_are_ranked_best_first(self):
        ingest(self.store, "weak", "会议纪要一句话")
        rows = self.store.search("admin", "会议 周四 二楼", limit=5)
        self.assertEqual(rows[0]["id"], self.ids["meeting"])

    def test_index_follows_deletes_and_is_idempotent(self):
        self.assertEqual(self.store.index().sync("admin")["indexed"], len(CORPUS))
        self.assertEqual(self.store.index().sync("admin")["indexed"], 0)  # nothing new to do
        action = self.store.prepare_action("admin", {"command": "memory.delete", "event_id": self.ids["chat"]})
        self.store.confirm_action("admin", action)
        self.assertEqual(self.find("群组"), set())
        self.assertEqual(self.store.index().sync("admin")["indexed"], 0)

    def test_lexical_alone_cannot_bridge_a_synonym(self):
        # Documents the honest limit that makes the vector layer worth having.
        self.assertEqual(self.find("电报"), set())


class Stub:
    """Deterministic stand-in for an embeddings provider; no network in tests."""
    model = "stub"

    def __init__(self, table):
        self.table = table
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return [normalise(self.table.get(text.strip(), [0.0, 0.0, 1.0])) for text in texts]


class HybridTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "memory.db")
        self.ids = {key: ingest(self.store, key, text) for key, text in CORPUS.items()}
        # 电报 sits next to the Telegram record and far from everything else.
        self.stub = Stub({CORPUS["telegram"]: [1.0, 0.0, 0.0], "电报": [0.99, 0.1, 0.0],
                          CORPUS["chat"]: [0.0, 1.0, 0.0], CORPUS["download"]: [0.0, 0.0, 1.0]})
        self.index = Index(self.store, self.stub)

    def test_vectors_bridge_the_synonym_lexical_search_misses(self):
        self.index.sync("admin")
        self.assertEqual(self.index.embed_pending("admin")["state"], "embedded")
        ranked, mode = self.index.search("admin", "电报", limit=5)
        self.assertEqual(mode, "hybrid")
        self.assertEqual(ranked[0], self.ids["telegram"])

    def test_embedding_is_incremental_and_stops_when_current(self):
        self.index.sync("admin")
        first = self.index.embed_pending("admin")
        self.assertEqual(first["embedded"], len(CORPUS))
        self.assertEqual(self.index.embed_pending("admin"), {"state": "current", "embedded": 0, "pending": 0})
        ingest(self.store, "extra", "新的一条记录")
        self.index.sync("admin")
        self.assertEqual(self.index.embed_pending("admin")["embedded"], 1)

    def test_a_failing_provider_degrades_to_lexical_instead_of_erroring(self):
        self.index.sync("admin")
        self.index.embed_pending("admin")

        class Broken(Stub):
            def embed(self, texts):
                raise RuntimeError("provider down")

        self.index.embeddings = Broken({})
        ranked, mode = self.index.search("admin", "群组", limit=5)
        self.assertEqual(mode, "lexical")
        self.assertEqual(ranked, [self.ids["chat"]])

    def test_disabled_provider_is_never_called(self):
        plain = Index(self.store)
        self.assertEqual(plain.embed_pending("admin")["state"], "disabled")
        self.assertEqual(plain.search("admin", "群组", limit=5)[1], "lexical")

    def test_fusion_prefers_a_result_both_rankings_return(self):
        # b is second lexically but first semantically, and beats a top-of-one-list hit.
        self.assertEqual(fuse(["a", "b"], ["b"]), ["b", "a"])
        self.assertEqual(fuse(["a"], []), ["a"])
        self.assertEqual(fuse([], []), [])


if __name__ == "__main__":
    unittest.main()
