"""Connector manager: add a source from the app instead of an environment file.

Credentials are write-only here too. The dialog sends a secret once and the
listing only ever shows whether one is stored, so nothing on screen and nothing
in a log can leak a token back out.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QComboBox, QDialogButtonBox, QMessageBox)


class AddDialog(QDialog):
    def __init__(self, kinds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加连接器")
        self.resize(520, 340)
        self.kinds = kinds
        self.inputs = {}
        root = QVBoxLayout(self)
        self.picker = QComboBox()
        for spec in kinds:
            self.picker.addItem(spec["label"], spec["kind"])
        self.picker.currentIndexChanged.connect(self.rebuild)
        root.addWidget(QLabel("来源类型"))
        root.addWidget(self.picker)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName("muted")
        root.addWidget(self.note)
        self.form_host = QWidget()
        self.form = QFormLayout(self.form_host)
        root.addWidget(self.form_host)
        root.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.rebuild()

    def spec(self):
        return self.kinds[self.picker.currentIndex()] if self.kinds else None

    def rebuild(self):
        while self.form.rowCount():
            self.form.removeRow(0)
        self.inputs = {}
        spec = self.spec()
        if not spec:
            return
        self.note.setText(spec.get("note", ""))
        for field in spec["fields"]:
            box = QLineEdit()
            box.setPlaceholderText(field.get("placeholder", ""))
            label = field["label"] + ("（可选）" if field.get("optional") else "")
            self.form.addRow(label, box)
            self.inputs[field["name"]] = box
        if spec.get("secret"):
            box = QLineEdit()
            box.setEchoMode(QLineEdit.Password)
            self.form.addRow(spec["secret"]["label"], box)
            self.inputs["__secret__"] = box

    def payload(self):
        spec = self.spec()
        config = {name: box.text().strip() for name, box in self.inputs.items() if name != "__secret__"}
        secret = self.inputs["__secret__"].text() if "__secret__" in self.inputs else ""
        return {"kind": spec["kind"], "config": config, "secret": secret}


class MemoryConnectors(QWidget):
    add_requested = Signal(dict)
    run_requested = Signal(str)
    toggle_requested = Signal(str, bool)
    remove_requested = Signal(str)
    refresh_requested = Signal()

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.kinds = data.get("kinds", [])
        self.items = data.get("items", [])
        labels = {spec["kind"]: spec["label"] for spec in self.kinds}
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)

        head = QHBoxLayout()
        title = QLabel("连接器")
        title.setObjectName("sectionTitle")
        head.addWidget(title)
        head.addWidget(QLabel(f"{len(self.items)} 个来源"))
        head.addStretch()
        button = QPushButton("添加连接器")
        button.clicked.connect(self.add)
        head.addWidget(button)
        button = QPushButton("刷新")
        button.clicked.connect(self.refresh_requested.emit)
        head.addWidget(button)
        root.addLayout(head)

        hint = QLabel("凭据只向本机服务单向写入，列表永远不回显，模型也读不到。移除连接器不会删除已导入的记录。")
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        root.addWidget(hint)

        self.table = QTableWidget(len(self.items), 5)
        self.table.setHorizontalHeaderLabels(["来源", "配置", "状态", "上次结果", "操作"])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 230)
        for row, item in enumerate(self.items):
            config = " · ".join(str(v) for v in item["config"].values())
            if item["has_secret"]:
                config += " · 已存凭据"
            for column, value in enumerate([labels.get(item["kind"], item["kind"]), config,
                                            "启用" if item["enabled"] else "停用",
                                            item["last_result"] or "尚未运行"]):
                cell = QTableWidgetItem(value)
                cell.setToolTip(value)
                self.table.setItem(row, column, cell)
            actions = QWidget()
            layout = QHBoxLayout(actions)
            layout.setContentsMargins(0, 0, 0, 0)
            run = QPushButton("拉取")
            run.clicked.connect(lambda checked=False, i=item["id"]: self.run_requested.emit(i))
            layout.addWidget(run)
            toggle = QPushButton("停用" if item["enabled"] else "启用")
            toggle.clicked.connect(lambda checked=False, i=item["id"], e=item["enabled"]: self.toggle_requested.emit(i, not e))
            layout.addWidget(toggle)
            remove = QPushButton("移除")
            remove.clicked.connect(lambda checked=False, it=item: self.remove(it))
            layout.addWidget(remove)
            self.table.setCellWidget(row, 4, actions)
            self.table.setRowHeight(row, 44)
        root.addWidget(self.table, 1)
        if not self.items:
            empty = QLabel("还没有连接器。点「添加连接器」接入 Gotify、GitHub Issue 或 RSS 订阅。")
            empty.setObjectName("muted")
            root.addWidget(empty)

    def add(self):
        if not self.kinds:
            return
        dialog = AddDialog(self.kinds, self)
        if dialog.exec() == QDialog.Accepted:
            self.add_requested.emit(dialog.payload())

    def remove(self, item):
        answer = QMessageBox.question(self, "移除连接器",
                                      f"移除「{item['name']}」？\n已导入的记录会保留，不会被删除。")
        if answer == QMessageBox.Yes:
            self.remove_requested.emit(item["id"])
