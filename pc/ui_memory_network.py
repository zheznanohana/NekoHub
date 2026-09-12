"""Memory graph as one linked web: force-directed, pan/zoom, size by connections.

The layered banding this replaced made level look like the only relationship in
the data. A linked web shows what is actually there — what clusters with what —
and the level still reads off colour and size. Positions carry no meaning; the
edge kinds in the block do, which is why the inspector names them in words.
"""
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsScene, QGraphicsView, QGraphicsEllipseItem, QGraphicsSimpleTextItem,
    QSplitter, QPlainTextEdit, QCheckBox)

# The desktop app runs from pc/, so the repository root has to be importable
# for the shared layout module the web UI mirrors.
import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.memory_v1.layout import degrees, layout, radius

LEVEL_COLOR = {"month": "#f0a35a", "week": "#e8c15c", "day": "#6fc4a8",
               "entity": "#a08ae8", "raw": "#6f92b8"}
LEVEL_NAME = {"month": "月记忆", "week": "周记忆", "day": "日记忆",
              "entity": "关联实体", "raw": "原始记录"}
EDGE_COLOR = {"compresses": "#4f7f93", "association": "#7a6bab", "evidence": "#3f5f70"}
EDGE_NAME = {"compresses": "压缩汇总", "association": "实体关联", "evidence": "原文证据"}
BACKGROUND = "#0f1a24"


class Node(QGraphicsEllipseItem):
    def __init__(self, node, size, select):
        super().__init__(-size, -size, size * 2, size * 2)
        self.node = node
        self.select = select
        self.setBrush(QColor(LEVEL_COLOR.get(node["level"], "#6f92b8")))
        self.setPen(QPen(QColor("#0f1a24"), 1.5))
        self.setZValue(3)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsScenePositionChanges, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{LEVEL_NAME.get(node['level'], node['level'])} · {node['label']}\n{node['text'][:300]}")
        self.caption = None
        self.attached = []

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemScenePositionHasChanged:
            self.reflow()
        return super().itemChange(change, value)

    def reflow(self):
        if self.caption is not None:
            self.caption.setPos(self.x() - self.caption.boundingRect().width() / 2,
                                self.y() + self.rect().height() / 2 + 4)
        for line, other, this_is_source in self.attached:
            a = self.pos() if this_is_source else other.pos()
            b = other.pos() if this_is_source else self.pos()
            line.setLine(a.x(), a.y(), b.x(), b.y())

    def mousePressEvent(self, event):
        self.select(self.node["id"])
        super().mousePressEvent(event)


class Canvas(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(BACKGROUND))
        self.setMinimumHeight(500)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        if 0.12 < self.transform().m11() * factor < 4.5:
            self.scale(factor, factor)
        event.accept()


class MemoryNetwork(QWidget):
    selection_changed = Signal(str)
    open_event = Signal(str)
    expand_summary = Signal(str)
    export_requested = Signal(dict)

    def __init__(self, block, parent=None):
        super().__init__(parent)
        self.block = block
        self.nodes = {}
        self.lines = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        title = QLabel("记忆网络")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addWidget(QLabel(f"{len(block['nodes'])} 个节点 · {len(block['edges'])} 条连接"))
        header.addStretch()
        self.labels = QCheckBox("显示标签")
        self.labels.setChecked(True)
        self.labels.toggled.connect(self.toggle_labels)
        header.addWidget(self.labels)
        for text, callback in [("适应画布", self.fit), ("导出网络 JSON", lambda: self.export_requested.emit(block))]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            header.addWidget(button)
        root.addLayout(header)

        legend = QLabel("  ".join(f"● {LEVEL_NAME[level]}" for level in ("raw", "day", "week", "month", "entity"))
                        + "    圆点越大连接越多")
        legend.setWordWrap(True)
        legend.setObjectName("muted")
        root.addWidget(legend)

        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)
        self.scene = QGraphicsScene(self)
        self.view = Canvas(self.scene)
        split.addWidget(self.view)

        inspector = QWidget()
        self.detail = QVBoxLayout(inspector)
        self.detail.setContentsMargins(16, 8, 0, 8)
        self.heading = QLabel("点选一个节点")
        self.heading.setWordWrap(True)
        self.heading.setObjectName("sectionTitle")
        self.detail.addWidget(self.heading)
        self.body = QPlainTextEdit()
        self.body.setReadOnly(True)
        self.body.setPlainText(
            "连接紧密的记忆会聚在一起，孤立的记忆会被推开。\n\n"
            "实线：下层压缩成上层摘要。\n虚线：人物、项目、主题之间的已确认关系。\n点线：事实指向它的原文证据。\n\n"
            "点击节点高亮它的直接连接，可拖动节点，滚轮缩放，拖空白平移。\n\n"
            "位置只是画法，不代表含义；这里只画数据库里已有的连接，不凭距离补造关系。")
        self.detail.addWidget(self.body, 1)
        self.actions = QVBoxLayout()
        self.detail.addLayout(self.actions)
        split.addWidget(inspector)
        split.setSizes([980, 280])

        positions = layout(block["nodes"], block["edges"])
        degree = degrees(block["nodes"], block["edges"])
        for edge in block["edges"]:
            if edge["source"] not in positions or edge["target"] not in positions:
                continue
            a, b = positions[edge["source"]], positions[edge["target"]]
            pen = QPen(QColor(EDGE_COLOR.get(edge["kind"], "#3f5f70")), 1.4)
            if edge["kind"] == "association":
                pen.setStyle(Qt.DashLine)
            elif edge["kind"] == "evidence":
                pen.setStyle(Qt.DotLine)
            line = self.scene.addLine(a[0], a[1], b[0], b[1], pen)
            line.setToolTip(f"{EDGE_NAME.get(edge['kind'], edge['kind'])}：{edge['label']}")
            line.setZValue(-1)
            self.lines.append((edge, line))

        for node in block["nodes"]:
            x, y = positions[node["id"]]
            item = Node(node, radius(degree[node["id"]], node["level"]), self.select)
            item.setPos(x, y)
            self.scene.addItem(item)
            caption = QGraphicsSimpleTextItem(node["label"][:16])
            caption.setBrush(QColor("#c7d7e6"))
            caption.setZValue(2)
            self.scene.addItem(caption)
            item.caption = caption
            self.nodes[node["id"]] = item

        for edge, line in self.lines:
            source, target = self.nodes.get(edge["source"]), self.nodes.get(edge["target"])
            if source and target:
                source.attached.append((line, target, True))
                target.attached.append((line, source, False))
        for item in self.nodes.values():
            item.reflow()

        if self.nodes:
            self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-120, -120, 120, 120))
        note = QLabel(block.get("scope", ""))
        note.setWordWrap(True)
        note.setObjectName("muted")
        root.addWidget(note)

    def showEvent(self, event):
        super().showEvent(event)
        self.fit()

    def fit(self):
        if self.nodes:
            self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-60, -60, 60, 60), Qt.KeepAspectRatio)

    def toggle_labels(self, shown):
        for item in self.nodes.values():
            if item.caption is not None:
                item.caption.setVisible(shown)

    def select(self, node_id):
        self.selection_changed.emit(node_id)
        node = self.nodes[node_id].node
        neighbours = {node_id}
        for edge, line in self.lines:
            active = node_id in (edge["source"], edge["target"])
            if active:
                neighbours.update((edge["source"], edge["target"]))
            pen = line.pen()
            pen.setColor(QColor("#8fe6cc") if active else QColor("#263a48"))
            pen.setWidthF(2.6 if active else 1.1)
            line.setPen(pen)
        for key, item in self.nodes.items():
            visible = key in neighbours
            item.setOpacity(1.0 if visible else 0.22)
            if item.caption is not None:
                item.caption.setOpacity(1.0 if visible else 0.15)
        self.heading.setText(node["label"])
        self.body.setPlainText(
            f"{node['text']}\n\n层级：{LEVEL_NAME.get(node['level'], node['level'])}"
            f"\n类型：{node['kind']}\n连接：{len(neighbours) - 1} 个\nID：{node['id']}")
        while self.actions.count():
            child = self.actions.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        button = QPushButton("只看它的邻居")
        button.clicked.connect(lambda: self.focus(neighbours))
        self.actions.addWidget(button)
        if node["level"] in ("day", "week", "month"):
            button = QPushButton("下钻：展开原始证据")
            button.clicked.connect(lambda: self.expand_summary.emit(node["id"]))
            self.actions.addWidget(button)
        for event_id in node["evidence_ids"][:5]:
            button = QPushButton("打开原文 " + event_id[:8])
            button.clicked.connect(lambda checked=False, e=event_id: self.open_event.emit(e))
            self.actions.addWidget(button)

    def focus(self, ids):
        rect = QRectF()
        for key in ids:
            item = self.nodes.get(key)
            if item:
                rect = rect.united(item.sceneBoundingRect()) if not rect.isNull() else item.sceneBoundingRect()
        if not rect.isNull():
            self.view.fitInView(rect.adjusted(-90, -90, 90, 90), Qt.KeepAspectRatio)
