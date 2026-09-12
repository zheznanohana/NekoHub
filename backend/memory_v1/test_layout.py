"""The picture must read like a linked web: clusters together, loners apart."""
import math
import time
import unittest

from backend.memory_v1.layout import degrees, layout, radius


def node(node_id, level="raw"):
    return {"id": node_id, "kind": "manual", "level": level, "label": node_id,
            "text": node_id, "period": "", "evidence_ids": []}


def edge(source, target, kind="association"):
    return {"source": source, "target": target, "kind": kind, "label": kind}


def distance(positions, a, b):
    return math.dist(positions[a], positions[b])


class LayoutTests(unittest.TestCase):
    def test_empty_and_single_node_are_safe(self):
        self.assertEqual(layout([], []), {})
        single = layout([node("a")], [])
        self.assertEqual(list(single), ["a"])
        self.assertTrue(all(math.isfinite(v) for v in single["a"]))

    def test_connected_nodes_end_up_closer_than_unconnected_ones(self):
        nodes = [node(n) for n in "abcxyz"]
        links = [edge("a", "b"), edge("b", "c"), edge("a", "c")]
        positions = layout(nodes, links, iterations=200)
        cluster = max(distance(positions, a, b) for a, b in (("a", "b"), ("b", "c"), ("a", "c")))
        apart = min(distance(positions, a, b) for a in "abc" for b in "xyz")
        self.assertLess(cluster, apart)

    def test_two_clusters_separate(self):
        nodes = [node(n) for n in ("a1", "a2", "a3", "b1", "b2", "b3")]
        links = [edge("a1", "a2"), edge("a2", "a3"), edge("a3", "a1"),
                 edge("b1", "b2"), edge("b2", "b3"), edge("b3", "b1")]
        positions = layout(nodes, links, iterations=260)
        within = max(max(distance(positions, x, y) for y in group if y != x) for group in (("a1", "a2", "a3"), ("b1", "b2", "b3")) for x in group)
        between = min(distance(positions, a, b) for a in ("a1", "a2", "a3") for b in ("b1", "b2", "b3"))
        self.assertLess(within, between)

    def test_nodes_do_not_land_on_top_of_each_other(self):
        nodes = [node(f"n{i}") for i in range(40)]
        positions = layout(nodes, [], iterations=200)
        closest = min(distance(positions, a["id"], b["id"]) for a in nodes for b in nodes if a["id"] < b["id"])
        self.assertGreater(closest, 8.0)

    def test_layout_is_deterministic_and_finite(self):
        nodes = [node(f"n{i}") for i in range(30)]
        links = [edge(f"n{i}", f"n{(i * 7) % 30}") for i in range(30)]
        first = layout(nodes, links, iterations=120)
        second = layout(nodes, links, iterations=120)
        self.assertEqual(first, second)
        self.assertTrue(all(math.isfinite(x) and math.isfinite(y) for x, y in first.values()))

    def test_result_fits_the_requested_canvas(self):
        nodes = [node(f"n{i}") for i in range(60)]
        links = [edge(f"n{i}", f"n{i + 1}") for i in range(59)]
        positions = layout(nodes, links, width=1200, height=800)
        self.assertTrue(all(0 <= x <= 1200 and 0 <= y <= 800 for x, y in positions.values()))

    def test_edges_naming_a_missing_node_are_ignored(self):
        positions = layout([node("a"), node("b")], [edge("a", "ghost"), edge("a", "b")])
        self.assertEqual(sorted(positions), ["a", "b"])

    def test_self_loops_do_not_destabilise_the_simulation(self):
        positions = layout([node("a"), node("b")], [edge("a", "a"), edge("a", "b")])
        self.assertTrue(all(math.isfinite(v) for pos in positions.values() for v in pos))

    def test_size_follows_connection_count(self):
        nodes = [node("hub"), node("leaf1"), node("leaf2"), node("lonely")]
        links = [edge("hub", "leaf1"), edge("hub", "leaf2")]
        counts = degrees(nodes, links)
        self.assertEqual(counts, {"hub": 2, "leaf1": 1, "leaf2": 1, "lonely": 0})
        self.assertGreater(radius(counts["hub"], "raw"), radius(counts["lonely"], "raw"))
        self.assertGreater(radius(0, "month"), radius(0, "raw"))

    def test_a_realistic_graph_lays_out_fast_enough_to_feel_instant(self):
        nodes = [node(f"n{i}", "raw" if i % 5 else "day") for i in range(200)]
        links = [edge(f"n{i}", f"n{(i * 3 + 1) % 200}") for i in range(260)]
        start = time.perf_counter()
        positions = layout(nodes, links)
        elapsed = time.perf_counter() - start
        self.assertEqual(len(positions), 200)
        self.assertLess(elapsed, 6.0, f"200-node layout took {elapsed:.1f}s")


if __name__ == "__main__":
    unittest.main()
