"""Force-directed placement for the memory network.

Position is presentation, never meaning: the graph contract carries explicit
edge kinds precisely so nothing has to be inferred from where a dot landed.
This module only decides where dots land, so the picture reads the way a linked
web should — densely connected things pull together, isolated things drift out,
and a node's size reflects how connected it is.

Repulsion is limited to a neighbourhood grid rather than every pair, which keeps
a few hundred nodes interactive in pure Python. The seed is fixed so the same
graph always produces the same picture across restarts and across the two UIs.
"""
import math

CELL = 110.0          # repulsion cutoff, in layout units
REPULSION = 9000.0
SPRING = 0.012
REST_LENGTH = 95.0
GRAVITY = 0.006
DAMPING = 0.86
MAX_STEP = 28.0


def degrees(nodes, edges):
    """Connection count per node, the Obsidian sense of 'how important is this'."""
    counts = {node["id"]: 0 for node in nodes}
    for edge in edges:
        for end in (edge["source"], edge["target"]):
            if end in counts:
                counts[end] += 1
    return counts


def radius(degree, level):
    base = {"month": 17.0, "week": 14.0, "day": 12.0, "entity": 11.0}.get(level, 7.0)
    return round(base + 2.6 * math.sqrt(degree), 2)


def seeded(index, total, salt):
    """Deterministic spread: a golden-angle spiral, jittered by a stable hash."""
    angle = index * 2.399963229728653 + (salt % 997) / 997.0
    span = 40.0 + 360.0 * math.sqrt((index + 0.5) / max(total, 1))
    return math.cos(angle) * span, math.sin(angle) * span


def layout(nodes, edges, *, iterations=260, width=1600, height=1040):
    """Returns {node_id: (x, y)} centred on (width/2, height/2)."""
    if not nodes:
        return {}
    ids = [node["id"] for node in nodes]
    index_of = {node_id: i for i, node_id in enumerate(ids)}
    count = len(ids)
    position = [seeded(i, count, sum(map(ord, ids[i][:12]))) for i in range(count)]
    xs = [p[0] for p in position]
    ys = [p[1] for p in position]
    vx = [0.0] * count
    vy = [0.0] * count

    links = []
    for edge in edges:
        a, b = index_of.get(edge["source"]), index_of.get(edge["target"])
        if a is not None and b is not None and a != b:
            links.append((a, b))
    degree = degrees(nodes, edges)
    mass = [1.0 + 0.32 * degree[node_id] for node_id in ids]

    for step in range(iterations):
        cooling = 1.0 - step / (iterations * 1.25)
        fx = [0.0] * count
        fy = [0.0] * count

        buckets = {}
        for i in range(count):
            buckets.setdefault((int(xs[i] // CELL), int(ys[i] // CELL)), []).append(i)
        for (cx, cy), members in buckets.items():
            near = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    near.extend(buckets.get((cx + dx, cy + dy), ()))
            for i in members:
                for j in near:
                    if i == j:
                        continue
                    ox, oy = xs[i] - xs[j], ys[i] - ys[j]
                    squared = ox * ox + oy * oy
                    if squared > CELL * CELL * 4 or squared == 0.0:
                        # Overlapping nodes get a deterministic nudge, not a divide by zero.
                        if squared == 0.0:
                            fx[i] += (i - j) * 0.5
                            fy[i] += 0.5
                        continue
                    distance = math.sqrt(squared)
                    push = REPULSION * mass[j] / squared
                    fx[i] += ox / distance * push
                    fy[i] += oy / distance * push

        for a, b in links:
            ox, oy = xs[b] - xs[a], ys[b] - ys[a]
            distance = math.hypot(ox, oy) or 0.01
            pull = SPRING * (distance - REST_LENGTH)
            ux, uy = ox / distance * pull, oy / distance * pull
            fx[a] += ux / mass[a] * 30
            fy[a] += uy / mass[a] * 30
            fx[b] -= ux / mass[b] * 30
            fy[b] -= uy / mass[b] * 30

        for i in range(count):
            fx[i] -= xs[i] * GRAVITY
            fy[i] -= ys[i] * GRAVITY
            vx[i] = (vx[i] + fx[i]) * DAMPING
            vy[i] = (vy[i] + fy[i]) * DAMPING
            speed = math.hypot(vx[i], vy[i])
            if speed > MAX_STEP:
                vx[i] *= MAX_STEP / speed
                vy[i] *= MAX_STEP / speed
            xs[i] += vx[i] * cooling
            ys[i] += vy[i] * cooling

    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    scale = min((width - 160) / max(right - left, 1.0), (height - 160) / max(bottom - top, 1.0), 1.6)
    ox = width / 2 - (left + right) / 2 * scale
    oy = height / 2 - (top + bottom) / 2 * scale
    return {ids[i]: (xs[i] * scale + ox, ys[i] * scale + oy) for i in range(count)}
