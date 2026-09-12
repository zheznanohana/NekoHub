"""Native PC view for fixed chat.blocks responses from the shared backend."""
import json
import os
import math
import uuid
from PySide6.QtCore import QObject, Signal, Qt, QUrl, QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, QFileDialog,
    QGraphicsScene, QGraphicsView, QComboBox, QLineEdit, QDialog, QPlainTextEdit)


class MemoryPage(QWidget):
    import_requested = Signal()
    def __init__(self):
        super().__init__()
        self.setObjectName("memory_page")
        self.net = QNetworkAccessManager(self)
        self.pending_imports = []
        self.import_busy = False
        self.view_context={'selected_ids':[],'visible_ids':[],'levels':[],'query':''}
        self.root = QVBoxLayout(self)
        self.root.addWidget(QLabel("记忆工作台 · 原文 / 图谱 / 分层摘要"))
        toolbar = QHBoxLayout()
        for label, command in [("记录", '/memory.search {"text":""}'), ("图谱", '/memory.graph {}'),
                               ("结构化表", '/memory.export {}'), ("回忆", '/memory.recall {"text":""}'), ("日报", '/memory.daily {}')]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, c=command: self.send(c))
            toolbar.addWidget(button)
        self.root.addLayout(toolbar)
        tools = QHBoxLayout()
        for label, path, payload in [('连接 / 队列','/status',None),('整理一条','/process',{}),
                                     ('同步 GitHub','/sync/github',{}),('后台日报','/daily/latest',None)]:
            button=QPushButton(label)
            button.clicked.connect(lambda checked=False,p=path,d=payload:self.call(p,d))
            tools.addWidget(button)
        button=QPushButton('导入插件已加载数据');button.clicked.connect(self.import_requested.emit);tools.addWidget(button)
        button=QPushButton('数据类型');button.clicked.connect(self.show_catalog);tools.addWidget(button)
        self.root.addLayout(tools)
        filters=QHBoxLayout()
        self.source_filter=QComboBox();self.source_filter.addItems(['','gotify','rss','imap','web3','github','manual','memory_agent'])
        self.level_filter=QComboBox();self.level_filter.addItems(['','raw','detail','day','week','month'])
        self.query=QLineEdit();self.query.setPlaceholderText('筛选内容；双击表格记录打开原文')
        filters.addWidget(self.source_filter);filters.addWidget(self.level_filter);filters.addWidget(self.query)
        button=QPushButton('查询表');button.clicked.connect(lambda:self.send('/memory.table.read '+json.dumps({'source':self.source_filter.currentText(),'level':self.level_filter.currentText(),'text':self.query.text()})));filters.addWidget(button)
        self.root.addLayout(filters)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); self.scroll=scroll
        content = QWidget(); self.cards = QVBoxLayout(content); self.cards.setAlignment(Qt.AlignTop)
        scroll.setWidget(content); self.root.addWidget(scroll, 1)
        self.status = QLabel("需启动记忆服务；读取 MEMORY_SERVICE_URL / MEMORY_SERVICE_TOKEN")
        self.status.setWordWrap(True); self.root.addWidget(self.status)
        self.input = QTextEdit(); self.input.setMaximumHeight(90)
        self.input.setPlaceholderText('聊天，或 /memory.create {"text":"今天的记录"}')
        self.root.addWidget(self.input)
        send = QPushButton("发送"); send.clicked.connect(lambda: self.send(self.input.toPlainText())); self.root.addWidget(send)

    def text(self, text, layout=None):
        label = QLabel(str(text)); label.setTextFormat(Qt.PlainText); label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        (layout or self.cards).addWidget(label)

    def call(self, path, data, done=None, settled=None):
        base = os.getenv("MEMORY_SERVICE_URL", "http://127.0.0.1:18081").rstrip("/")
        url = QUrl(base)
        if url.scheme() != "https" and not (url.scheme() == "http" and url.host() in ("localhost", "127.0.0.1", "::1")):
            self.status.setText("服务地址需 HTTPS 或本机 HTTP"); return
        request = QNetworkRequest(QUrl(base+"/api/memory/v1"+path))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", ("Bearer "+os.getenv("MEMORY_SERVICE_TOKEN", "")).encode())
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        request.setTransferTimeout(150000)
        reply = self.net.get(request) if data is None else self.net.post(request, json.dumps(data).encode())
        self.status.setText("处理中…")
        def finished():
            try:
                value = json.loads(bytes(reply.readAll()))
                if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) not in (200,202):
                    self.status.setText(value.get('message','请求失败'));return
                if path == '/status':
                    self.text('连接配置：'+json.dumps({k:v for k,v in value.items() if k!='jobs'},ensure_ascii=False))
                    for job in value.get('jobs',[]):
                        self.text(json.dumps(job,ensure_ascii=False))
                        if job.get('state')=='review':
                            button=QPushButton('查看整理提议');button.clicked.connect(lambda checked=False,jid=job['id']:self.call('/jobs/'+jid,None));self.cards.addWidget(button)
                    self.status.setText('状态已刷新');return
                if path.startswith('/events/') or (path.startswith('/jobs/') and not path.endswith('/review')):
                    self.show_json(value)
                    if path.startswith('/jobs/'):
                        for label,approve in [('批准整理',True),('驳回整理',False)]:
                            button=QPushButton(label);button.clicked.connect(lambda checked=False,p=path,a=approve,b=button:self.call(p+'/review',{'approve':a},lambda:b.setDisabled(True)));self.cards.addWidget(button)
                    return
                if value.get('event_id') and value.get('job_id'):
                    self.status.setText('通知已进入记忆队列');return
                if value.get("kind") != "chat.blocks":
                    self.status.setText(value.get("message", "请求失败")); return
                self.render(value["blocks"])
                if done: done()
                self.status.setText("完成")
            except Exception:
                self.status.setText("连接或响应格式异常；检查服务与配置")
            finally:
                reply.deleteLater()
                if settled: settled()
        reply.finished.connect(finished)

    def show_catalog(self):
        from memory_sources import CATALOG
        self.show_json([dict(source=s,type=t,fields=f,scope=sc) for s,t,f,sc in CATALOG])

    def show_json(self, value):
        dialog=QDialog(self);dialog.setWindowTitle('结构化数据 · 只读');dialog.resize(850,600)
        layout=QVBoxLayout(dialog);view=QPlainTextEdit();view.setReadOnly(True)
        view.setPlainText(json.dumps(value,ensure_ascii=False,indent=2));layout.addWidget(view)
        dialog.setAttribute(Qt.WA_DeleteOnClose);dialog.show()

    def enqueue_documents(self, documents):
        if not os.getenv('MEMORY_SERVICE_TOKEN'):
            self.status.setText('先用本地启动器加载记忆服务配置');return
        self.pending_imports.extend(documents)
        if not self.import_busy:self.import_next()

    def import_next(self):
        if not self.pending_imports:
            self.import_busy=False;return
        self.import_busy=True
        document=self.pending_imports.pop(0)
        self.call('/events',document,settled=lambda:QTimer.singleShot(0,self.import_next))

    def send(self, message):
        if not message.strip(): return
        self.text("你："+message); self.input.clear()
        self.call("/chat", {"schema_version": "1.0", "message": message,"view_context":self.view_context})

    def ingest_external(self,title,text,source,external_id=None,occurred_at=None):
        # Opt-in: no service token means no extra data transfer from legacy plugins.
        if not os.getenv('MEMORY_SERVICE_TOKEN'):return
        document={'schema_version':'1.0','kind':'memory.ingest','request_id':uuid.uuid4().hex,
                  'source':{'type':source,'instance_id':'pc:'+source,'external_id':external_id or uuid.uuid4().hex},
                  'occurred_at':occurred_at,'timezone':'Asia/Tokyo','content':{'title':title or '', 'text':text or '(empty notification)'},'provenance':'external'}
        self.call('/events',document)

    def render(self, blocks):
        for block in blocks:
            kind = block["type"]
            if kind == "text": self.text(block["text"])
            elif kind == "memory.cards":
                for item in block["items"]:
                    self.text(item["id"]+"\n"+item["text"])
                    button=QPushButton('打开完整原文 / 字段');button.clicked.connect(lambda checked=False,eid=item['id']:self.call('/events/'+eid,None));self.cards.addWidget(button)
            elif kind == "memory.summaries":
                for item in block["items"]:
                    self.text(f"{item['level']} / {item['period']}\n{item['summary']}")
                    button = QPushButton("展开原文")
                    button.clicked.connect(lambda checked=False, sid=item["id"]: self.send('/memory.expand '+json.dumps({"summary_id":sid})))
                    self.cards.addWidget(button)
            elif kind == "memory.action":
                self.text("待确认（Agent 无删除权限）：\n"+json.dumps(block["command"],ensure_ascii=False)+"\n"+block.get("preview", "")+"\n"+block.get("reason", ""))
                button = QPushButton("确认执行")
                button.clicked.connect(lambda checked=False, aid=block["action_id"], b=button: self.call('/actions/'+aid+'/confirm', {}, lambda: b.setDisabled(True)))
                self.cards.addWidget(button)
            elif kind == "memory.table":
                from ui_memory_table import MemoryTable
                table=MemoryTable(block)
                table.open_event.connect(lambda eid:self.call('/events/'+eid,None))
                table.export_requested.connect(self.export)
                self.cards.addWidget(table)
            elif kind == "memory.network":
                from ui_memory_network import MemoryNetwork
                graph=MemoryNetwork(block)
                self.view_context={'selected_ids':[],'visible_ids':[n['id'] for n in block['nodes']][:500],'levels':sorted(set(n['level'] for n in block['nodes'])),'query':self.query.text()}
                graph.selection_changed.connect(lambda nid:self.view_context.update(selected_ids=[nid]))
                graph.open_event.connect(lambda eid:self.call('/events/'+eid,None))
                graph.expand_summary.connect(lambda sid:self.send('/memory.expand '+json.dumps({'summary_id':sid})))
                graph.export_requested.connect(self.export)
                self.cards.addWidget(graph)
            elif kind == "memory.graph":
                graph=block["data"]; scene=QGraphicsScene(self)
                points={n["id"]:(220+170*math.cos(i*2*math.pi/max(1,len(graph["nodes"]))),150+110*math.sin(i*2*math.pi/max(1,len(graph["nodes"])))) for i,n in enumerate(graph["nodes"])}
                for fact in graph["facts"]:
                    if "node_id" in fact["object"]:
                        a,b=points[fact["subject_id"]],points[fact["object"]["node_id"]]
                        line=scene.addLine(*a,*b); line.setToolTip(fact["predicate"]+"\n"+"\n".join(e["quote"] for e in fact["evidence"]))
                for node in graph["nodes"]:
                    x,y=points[node["id"]]; scene.addEllipse(x-8,y-8,16,16); scene.addText(node["label"]).setPos(x-20,y+10)
                view=QGraphicsView(scene); view.setMinimumHeight(350); self.cards.addWidget(view)
            elif kind == "memory.receipt": self.text(json.dumps(block["data"],ensure_ascii=False))

    def export(self, block):
        path,_=QFileDialog.getSaveFileName(self,"导出结构化记忆","memory.json","JSON (*.json)")
        if path:
            with open(path,"w",encoding="utf-8") as file:
                json.dump({"schema_version":"1.0","kind":block['type']+'.export',**block},file,ensure_ascii=False,indent=2)

    def fill_table(self,table,block,vertical):
        columns,rows=block['columns'],block['rows']
        table.clear();table.setRowCount(len(columns) if vertical else len(rows));table.setColumnCount(len(rows) if vertical else len(columns))
        table.setHorizontalHeaderLabels([r['id'] for r in rows] if vertical else columns)
        if vertical:table.setVerticalHeaderLabels(columns)
        for r,row in enumerate(rows):
            for c,column in enumerate(columns):
                value=row[column];item=QTableWidgetItem(json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else str(value if value is not None else ''))
                item.setData(Qt.UserRole,row['evidence_ids'])
                table.setItem(c if vertical else r,r if vertical else c,item)
        try:table.itemDoubleClicked.disconnect()
        except RuntimeError:pass
        table.itemDoubleClicked.connect(lambda item:[self.call('/events/'+eid,None) for eid in (item.data(Qt.UserRole) or [])[:3]])
