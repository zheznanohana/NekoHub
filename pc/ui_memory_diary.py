"""Diary table: one row per day, the user's own text beside that day's records."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QPlainTextEdit, QLineEdit)

from ui_memory_table import label

SOURCE = {'imap': '邮件', 'rss': 'RSS', 'web3': '链上', 'gotify': '通知',
          'github': 'GitHub', 'manual': '手记', 'import': '旧版导入'}


class MemoryDiary(QWidget):
    open_event = Signal(str)
    export_requested = Signal(dict)
    save_requested = Signal(str, str)      # day, text
    expand_summary = Signal(str)

    def __init__(self, block, parent=None):
        super().__init__(parent)
        self.block = block
        self.setObjectName('memoryDiaryPanel')
        self.setMinimumHeight(460)
        root = QVBoxLayout(self); root.setContentsMargins(20, 18, 20, 16); root.setSpacing(14)
        head = QHBoxLayout(); titles = QVBoxLayout()
        titles.addWidget(label('日记表', 'sectionTitle'))
        titles.addWidget(label(f"{len(block['rows'])} 天  ·  左侧选日期，右侧写当天日记", 'muted'))
        head.addLayout(titles); head.addStretch()
        export = QPushButton('导出 JSON'); export.clicked.connect(lambda: self.export_requested.emit(block))
        head.addWidget(export); root.addLayout(head)

        split = QSplitter(Qt.Horizontal); root.addWidget(split, 1)
        self.table = QTableWidget(len(block['rows']), 4)
        self.table.setHorizontalHeaderLabels(['日期', '日记', '记录', '来源'])
        self.table.verticalHeader().hide(); self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setTextElideMode(Qt.ElideRight)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 104); self.table.setColumnWidth(2, 56); self.table.setColumnWidth(3, 120)
        split.addWidget(self.table)

        editor = QWidget(); side = QVBoxLayout(editor); side.setContentsMargins(18, 0, 0, 0)
        self.day = QLineEdit(); self.day.setPlaceholderText('YYYY-MM-DD')
        side.addWidget(label('日期', 'eyebrow')); side.addWidget(self.day)
        self.text = QPlainTextEdit(); self.text.setPlaceholderText('写下这一天。你写的内容优先于自动摘要。')
        side.addWidget(label('我的日记', 'eyebrow')); side.addWidget(self.text, 2)
        self.summary = QPlainTextEdit(); self.summary.setReadOnly(True)
        self.summary.setPlaceholderText('该日自动摘要会在这里显示（由后台整理生成）。')
        side.addWidget(label('当日自动摘要 · 只读', 'eyebrow')); side.addWidget(self.summary, 1)
        buttons = QHBoxLayout()
        save = QPushButton('保存日记'); save.clicked.connect(self._save); buttons.addWidget(save)
        self.open_button = QPushButton('打开当天记录'); self.open_button.clicked.connect(self._open_day)
        buttons.addWidget(self.open_button)
        self.expand_button = QPushButton('展开摘要原文'); self.expand_button.clicked.connect(self._expand)
        buttons.addWidget(self.expand_button)
        side.addLayout(buttons)
        self.hint = label('', 'muted'); side.addWidget(self.hint)
        split.addWidget(editor); split.setSizes([560, 460]); split.setStretchFactor(0, 1); split.setStretchFactor(1, 1)

        for index, row in enumerate(block['rows']):
            values = [row['day'], (row['text'] or '（未写）').replace('\n', ' '), str(row['event_count']),
                      ' / '.join(SOURCE.get(s, s) for s in row['sources'])]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value); item.setToolTip(value)
                self.table.setItem(index, column, item)
            self.table.setRowHeight(index, 40)
        self.table.currentCellChanged.connect(lambda r, c, pr, pc: self.select(r))
        root.addWidget(label(block['scope'], 'muted'))
        if block['rows']:
            self.table.setCurrentCell(0, 0)
        else:
            self.hint.setText('还没有任何一天的记录。先导入数据或直接写今天的日记。')

    def current(self):
        index = self.table.currentRow()
        return self.block['rows'][index] if 0 <= index < len(self.block['rows']) else None

    def select(self, index):
        row = self.current()
        if not row:
            return
        self.day.setText(row['day'])
        self.text.setPlainText(row['text'])
        self.summary.setPlainText(row['summary'])
        self.expand_button.setEnabled(bool(row['summary_id']))
        self.open_button.setEnabled(bool(row['event_ids']))
        version = f"第 {row['version']} 版 · {row['updated_at'][:16]}" if row['version'] else '尚未写过'
        self.hint.setText(f"{version}  ·  当天 {row['event_count']} 条记录")

    def _save(self):
        day, text = self.day.text().strip(), self.text.toPlainText().strip()
        if not day or not text:
            self.hint.setText('日期和正文都要填；保存会保留上一版历史。')
            return
        self.save_requested.emit(day, text)

    def _open_day(self):
        row = self.current()
        if row and row['event_ids']:
            for event_id in row['event_ids'][:3]:
                self.open_event.emit(event_id)

    def _expand(self):
        row = self.current()
        if row and row['summary_id']:
            self.expand_summary.emit(row['summary_id'])
