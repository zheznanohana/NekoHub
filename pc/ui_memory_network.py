"""Interactive semantic network: distinct shapes, compression levels and evidence."""
import math
from PySide6.QtCore import Qt,QPointF,Signal,QRectF
from PySide6.QtGui import QColor,QPen,QBrush,QPainterPath,QPolygonF,QPainter
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QGraphicsScene,QGraphicsView,QGraphicsPathItem,QSplitter,QPlainTextEdit)

LAYERS=[('month','03  月记忆'),('week','02  周记忆'),('day','01  日记忆'),('raw','00  原始记录'),('entity','关联实体')]
PALETTE={'summary':'#399c89','imap':'#6e9de0','rss':'#dfa95b','github':'#a49ae7','web3':'#c78db6','gotify':'#77afca','manual':'#82bca2','person':'#e6b36f','project':'#a49ae7','topic':'#87b9d0'}


class Node(QGraphicsPathItem):
    def __init__(self,node,x,y,select):
        path=QPainterPath();kind=node['kind']
        if kind=='summary':
            radius={'month':33,'week':27,'day':22}[node['level']]
            path.addEllipse(-radius,-radius,radius*2,radius*2)
        elif kind in ('web3','project'):
            path.addPolygon(QPolygonF([QPointF(0,-22),QPointF(25,0),QPointF(0,22),QPointF(-25,0)]));path.closeSubpath()
        elif kind in ('rss','topic'):
            path.addPolygon(QPolygonF([QPointF(math.cos(i*math.pi/3)*24,math.sin(i*math.pi/3)*24) for i in range(6)]));path.closeSubpath()
        elif kind in ('person','event'):
            path.addEllipse(-17,-17,34,34)
        elif kind=='gotify':
            path.addPolygon(QPolygonF([QPointF(0,-23),QPointF(24,20),QPointF(-24,20)]));path.closeSubpath()
        else:path.addRoundedRect(-26,-18,52,36,5,5)
        super().__init__(path);self.node=node;self.select=select
        self.setPos(x,y);self.setBrush(QColor(PALETTE.get(kind,'#90b5c6')))
        self.setPen(QPen(QColor('#dbe9f4'),1));self.setZValue(3)
        self.setCursor(Qt.PointingHandCursor);self.setToolTip(node['label']+'\n'+node['text'][:300])

    def mousePressEvent(self,event):
        self.select(self.node['id']);event.accept()


class Canvas(QGraphicsView):
    def __init__(self,scene):
        super().__init__(scene);self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag);self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QColor('#101d2a'));self.setMinimumHeight(480)

    def wheelEvent(self,event):
        factor=1.15 if event.angleDelta().y()>0 else 1/1.15
        if .25<self.transform().m11()*factor<3:self.scale(factor,factor)
        event.accept()


class MemoryNetwork(QWidget):
    selection_changed=Signal(str)
    open_event=Signal(str)
    expand_summary=Signal(str)
    export_requested=Signal(dict)

    def __init__(self,block,parent=None):
        super().__init__(parent);self.block=block;self.nodes={};self.lines=[]
        root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0)
        header=QHBoxLayout();title=QLabel('分层记忆网络');title.setObjectName('sectionTitle');header.addWidget(title);header.addStretch()
        for text,callback in [('适应画布',lambda:self.view.fitInView(self.scene.sceneRect(),Qt.KeepAspectRatio)),('导出网络 JSON',lambda:self.export_requested.emit(block))]:
            button=QPushButton(text);button.clicked.connect(callback);header.addWidget(button)
        root.addLayout(header)
        legend=QLabel('圆形 · 压缩记忆    矩形 · 邮件 / 记录    六边形 · RSS / 主题    菱形 · 项目 / 交易    三角形 · 通知')
        legend.setWordWrap(True);legend.setObjectName('muted');root.addWidget(legend)
        split=QSplitter(Qt.Horizontal);root.addWidget(split,1)
        self.scene=QGraphicsScene(self);self.view=Canvas(self.scene);split.addWidget(self.view)
        inspector=QWidget();self.detail=QVBoxLayout(inspector);self.detail.setContentsMargins(16,8,0,8)
        self.heading=QLabel('点选一个节点');self.heading.setWordWrap(True);self.heading.setObjectName('sectionTitle');self.detail.addWidget(self.heading)
        self.body=QPlainTextEdit();self.body.setReadOnly(True);self.body.setPlainText('向上：从原文压缩到日、周、月。\n\n横向：人物、项目、主题之间的已确认关系。\n\n点击节点高亮直接连接；滚轮缩放，拖动空白平移。\n\n这里仅绘制数据库已有连接，不凭视觉补造关系。');self.detail.addWidget(self.body,1)
        self.actions=QVBoxLayout();self.detail.addLayout(self.actions);split.addWidget(inspector);split.setSizes([950,260])
        positions={};width=max(950,max((sum(n['level']==lev for n in block['nodes']) for lev,_ in LAYERS),default=0)*145+200)
        for level_index,(level,caption) in enumerate(LAYERS):
            y=65+level_index*120
            band=self.scene.addRect(0,y-52,width,104,QPen(Qt.NoPen),QBrush(QColor('#152637' if level_index%2==0 else '#122131')));band.setZValue(-3)
            label=self.scene.addText(caption);label.setDefaultTextColor(QColor('#95adc4'));label.setPos(15,y-14)
            members=[n for n in block['nodes'] if n['level']==level]
            if not members:
                empty=self.scene.addText('尚无该层记忆');empty.setDefaultTextColor(QColor('#617a91'));empty.setPos(175,y-14)
            for i,node in enumerate(members):positions[node['id']]=(180+(i+.5)*(width-210)/max(1,len(members)),y)
        for edge in block['edges']:
            if edge['source'] not in positions or edge['target'] not in positions:continue
            a,b=positions[edge['source']],positions[edge['target']]
            path=QPainterPath(QPointF(*a));path.cubicTo(QPointF(a[0],(a[1]+b[1])/2),QPointF(b[0],(a[1]+b[1])/2),QPointF(*b))
            pen=QPen(QColor('#416878'),1.5)
            if edge['kind']!='compresses':pen.setStyle(Qt.DashLine)
            line=self.scene.addPath(path,pen);line.setToolTip(edge['label']);line.setZValue(-1);self.lines.append((edge,line))
        for node in block['nodes']:
            x,y=positions[node['id']];item=Node(node,x,y,self.select);self.scene.addItem(item);self.nodes[node['id']]=item
            text=self.scene.addText(node['label'][:18]);text.setDefaultTextColor(QColor('#e0eaf3'));text.setPos(x-text.boundingRect().width()/2,y+34)
        self.scene.setSceneRect(0,0,width,625)
        note=QLabel('实线：下层 → 上层压缩汇总  ·  虚线：证据或实体关联  ·  点击可追溯，不自动删除原文')
        note.setWordWrap(True);note.setObjectName('muted');root.addWidget(note)

    def select(self,node_id):
        self.selection_changed.emit(node_id)
        node=self.nodes[node_id].node;neighbors={node_id}
        for edge,line in self.lines:
            active=node_id in (edge['source'],edge['target'])
            if active:neighbors.update([edge['source'],edge['target']])
            pen=line.pen();pen.setColor(QColor('#81e3cb' if active else '#2c424f'));pen.setWidthF(3 if active else 1);line.setPen(pen)
        for key,item in self.nodes.items():item.setOpacity(1 if key in neighbors else .3)
        self.heading.setText(node['label']);self.body.setPlainText(node['text']+'\n\n层级：'+node['level']+'\n类型：'+node['kind']+'\nID：'+node['id'])
        while self.actions.count():
            child=self.actions.takeAt(0)
            if child.widget():child.widget().deleteLater()
        if node['level'] in ('day','week','month'):
            button=QPushButton('下钻：展开原始证据');button.clicked.connect(lambda:self.expand_summary.emit(node_id));self.actions.addWidget(button)
        for eid in node['evidence_ids'][:5]:
            button=QPushButton('打开原文 '+eid[:8]);button.clicked.connect(lambda checked=False,e=eid:self.open_event.emit(e));self.actions.addWidget(button)
