"""Readable table/card projections of the same canonical memory.table block."""
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QTableWidget,QTableWidgetItem,QHeaderView,QStackedWidget,QScrollArea,QFrame,
    QSplitter,QPlainTextEdit)

SOURCE={'imap':'邮件','rss':'RSS 订阅','web3':'链上交易','gotify':'通知','github':'GitHub','manual':'日常记录','memory_agent':'记忆 Agent'}
LEVEL={'raw':'原始记录','detail':'详细事实','day':'日摘要','week':'周摘要','month':'月摘要'}
STATUS={'recorded':'已收录','active':'有效','candidate':'待审核','archived':'已归档'}
COLORS={'imap':'#3265a8','rss':'#947022','web3':'#7254a5','github':'#435367','manual':'#247968','memory_agent':'#247968','gotify':'#3265a8'}


def label(text, name=None):
    widget=QLabel(str(text));widget.setTextFormat(Qt.PlainText);widget.setWordWrap(True)
    if name:widget.setObjectName(name)
    return widget


class MemoryTable(QWidget):
    open_event=Signal(str)
    export_requested=Signal(dict)

    def __init__(self,block,parent=None):
        super().__init__(parent);self.block=block;self.setObjectName('memoryTablePanel')
        self.setMinimumHeight(460)
        root=QVBoxLayout(self);root.setContentsMargins(20,18,20,16);root.setSpacing(14)
        head=QHBoxLayout();titles=QVBoxLayout()
        titles.addWidget(label('记忆数据表','sectionTitle'))
        titles.addWidget(label(f"当前视图 {len(block['rows'])} 条  ·  原文与摘要共用一份结构化数据",'muted'))
        head.addLayout(titles);head.addStretch()
        self.modes=[]
        for index,text in enumerate(['横向表格','纵向卡片']):
            button=QPushButton(text);button.setCheckable(True);button.setChecked(index==0)
            button.clicked.connect(lambda checked=False,i=index:self.switch(i));self.modes.append(button);head.addWidget(button)
        export=QPushButton('导出 JSON');export.clicked.connect(lambda:self.export_requested.emit(block));head.addWidget(export)
        root.addLayout(head)
        self.stack=QStackedWidget();root.addWidget(self.stack,1)
        split=QSplitter(Qt.Horizontal);self.stack.addWidget(split)
        self.table=QTableWidget(len(block['rows']),5)
        self.table.setHorizontalHeaderLabels(['来源 / 层级','记录摘要','时间','状态','证据'])
        self.table.verticalHeader().hide();self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True);self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection);self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(False);self.table.setTextElideMode(Qt.ElideRight)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        self.table.setColumnWidth(0,120);self.table.setColumnWidth(2,112);self.table.setColumnWidth(3,72);self.table.setColumnWidth(4,52)
        split.addWidget(self.table)
        self.inspector=QWidget();self.detail=QVBoxLayout(self.inspector);self.detail.setContentsMargins(18,0,0,0)
        split.addWidget(self.inspector);split.setSizes([740,270]);split.setStretchFactor(0,3);split.setStretchFactor(1,1)
        for index,row in enumerate(block['rows']):
            values=[SOURCE.get(row['source'],row['source'])+' / '+LEVEL.get(row['level'],row['level']),
                row.get('fields',{}).get('title') or row.get('fields',{}).get('subject') or row['content'].replace('\n',' '),
                (row['period'] or '时间待确认')[:16],STATUS.get(row['status'],row['status']),str(len(row['evidence_ids']))]
            for c,value in enumerate(values):
                item=QTableWidgetItem(str(value));item.setToolTip(str(value));self.table.setItem(index,c,item)
                if c==0:item.setForeground(QColor(COLORS.get(row['source'],'#247968')))
            self.table.setRowHeight(index,58)
        self.table.currentCellChanged.connect(lambda r,c,pr,pc:self.inspect(r))
        self.table.cellDoubleClicked.connect(lambda r,c:self.open_first(r))
        self.vertical=QScrollArea();self.vertical.setWidgetResizable(True);self.stack.addWidget(self.vertical)
        content=QWidget();cards=QVBoxLayout(content);cards.setContentsMargins(0,0,8,0);cards.setSpacing(12)
        for row in block['rows']:
            card=QFrame();card.setObjectName('recordCard');layout=QVBoxLayout(card);layout.setContentsMargins(18,14,18,14)
            top=QHBoxLayout();top.addWidget(label(SOURCE.get(row['source'],row['source'])+'  /  '+LEVEL.get(row['level'],row['level']),'eyebrow'));top.addStretch();top.addWidget(label(row['period'] or '时间待确认','muted'));layout.addLayout(top)
            layout.addWidget(label(row['content'][:700]))
            for key,value in row.get('fields',{}).items():
                layout.addWidget(label(f'{key}  ·  {value}','muted'))
            if row['evidence_ids']:
                button=QPushButton('打开证据原文');button.clicked.connect(lambda checked=False,eid=row['evidence_ids'][0]:self.open_event.emit(eid));layout.addWidget(button,0,Qt.AlignLeft)
            cards.addWidget(card)
        cards.addStretch();self.vertical.setWidget(content)
        root.addWidget(label('范围：最近 100 条原文、最多 200 条有效事实及当前摘要。导出的是当前视图，不是全库备份。','muted'))
        if block['rows']:self.table.setCurrentCell(0,1)
        else:self.detail.addWidget(label('暂无记忆记录\n\n导入插件数据，或在下方聊天框添加第一条记录。','muted'))

    def switch(self,index):
        self.stack.setCurrentIndex(index)
        for i,button in enumerate(self.modes):button.setChecked(i==index)

    def inspect(self,index):
        if not 0<=index<len(self.block['rows']):return
        while self.detail.count():
            item=self.detail.takeAt(0)
            if item.widget():item.widget().deleteLater()
        row=self.block['rows'][index]
        self.detail.addWidget(label('记录详情','sectionTitle'))
        self.detail.addWidget(label(LEVEL.get(row['level'],row['level'])+'  ·  '+STATUS.get(row['status'],row['status']),'eyebrow'))
        body=QPlainTextEdit();body.setReadOnly(True);body.setPlainText(row['content']);self.detail.addWidget(body,1)
        self.detail.addWidget(label(f"{len(row['parent_ids'])} 个上级  /  {len(row['child_ids'])} 个下级  /  {len(row['evidence_ids'])} 条证据",'muted'))
        for eid in row['evidence_ids'][:3]:
            button=QPushButton('查看原文  ↗');button.clicked.connect(lambda checked=False,e=eid:self.open_event.emit(e));self.detail.addWidget(button)
        self.detail.addWidget(label('ID  '+row['id'],'muted'))

    def open_first(self,index):
        refs=self.block['rows'][index]['evidence_ids']
        if refs:self.open_event.emit(refs[0])
