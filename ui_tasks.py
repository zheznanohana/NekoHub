# ui_tasks.py
import uuid
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (CardWidget, PushButton, LineEdit, TextEdit, TitleLabel, 
                            SubtitleLabel, BodyLabel, ComboBox, SwitchButton, FluentIcon, 
                            InfoBar, InfoBarPosition, StrongBodyLabel, ScrollArea, CheckBox)

class GuideCard(CardWidget):
    def __init__(self, lang, parent=None):
        super().__init__(parent)
        is_en = lang == "English"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 15, 20, 15)
        lay.addWidget(SubtitleLabel("💡 User Guide" if is_en else "💡 AI 自动化指南"))
        guide = (
            "1. **Count**: Run after N new messages.\n2. **Time**: Run at fixed points (e.g., 08:00).\n3. **Interval**: Run every N minutes." if is_en else
            "1. **累计触发**：每满 N 条通知运行一次。\n2. **定时触发**：每天 08:00, 20:00 准点总结。\n3. **固定频率**：每隔 60 分钟梳理一次。"
        )
        lbl = BodyLabel(guide)
        lbl.setTextFormat(Qt.MarkdownText)
        lay.addWidget(lbl)

class TaskCard(CardWidget):
    def __init__(self, task_data, lang, on_delete, on_save, on_run):
        super().__init__()
        self.task_id = task_data.get("id")
        self.lang = lang
        self.on_run = on_run
        self.on_delete = on_delete
        self.on_save = on_save
        is_en = lang == "English"
        
        lay = QVBoxLayout(self)
        
        # 1. 标题与开关栏
        head = QHBoxLayout()
        self.ed_name = LineEdit()
        self.ed_name.setText(task_data.get("name", "New Task"))
        self.sw_enabled = SwitchButton("启用")
        self.sw_enabled.setChecked(task_data.get("enabled", True))
        
        head.addWidget(StrongBodyLabel("任务名:"))
        head.addWidget(self.ed_name, 1)
        head.addWidget(self.sw_enabled)
        lay.addLayout(head)

        # 2. [完美极简重构] 普通输入框单行平铺
        source_lay = QHBoxLayout()
        domains = task_data.get("domains", ["gotify", "rss", "imap", "web3"])
        source_lay.addWidget(StrongBodyLabel("数据源(条数):"))

        def make_inline_pair(label_text, domain_key, default_val):
            chk = CheckBox(label_text)
            chk.setChecked(domain_key in domains)
            # 使用普通的 LineEdit
            sp = LineEdit()
            sp.setFixedWidth(40)
            sp.setText(str(task_data.get(f"limit_{domain_key}", default_val)))
            
            chk.stateChanged.connect(self._sync)
            sp.textChanged.connect(self._sync)
            return chk, sp

        self.chk_gotify, self.sp_gotify = make_inline_pair("通知", "gotify", 20)
        self.chk_rss, self.sp_rss = make_inline_pair("订阅", "rss", 10)
        self.chk_imap, self.sp_imap = make_inline_pair("邮件", "imap", 10)
        self.chk_web3, self.sp_web3 = make_inline_pair("链上", "web3", 20)

        # 紧密排列
        for w in [self.chk_gotify, self.sp_gotify, self.chk_rss, self.sp_rss, self.chk_imap, self.sp_imap, self.chk_web3, self.sp_web3]:
            source_lay.addWidget(w)
            if isinstance(w, LineEdit):
                source_lay.addSpacing(15)

        source_lay.addStretch(1)
        lay.addLayout(source_lay)

        # 3. Prompt 指令区
        lay.addWidget(StrongBodyLabel("AI 处理指令 (Prompt):"))
        self.ed_prompt = TextEdit()
        self.ed_prompt.setText(task_data.get("prompt", ""))
        self.ed_prompt.setFixedHeight(80)
        lay.addWidget(self.ed_prompt)

        # 4. 触发逻辑与动态单位提示
        logic = QHBoxLayout()
        
        self.cb_mode = ComboBox()
        self.cb_mode.addItems(["累计计数触发", "定时点执行", "固定间隔执行"])
        self.cb_mode.setCurrentIndex({"count": 0, "time": 1, "interval": 2}.get(task_data.get("mode", "count"), 0))
        
        self.ed_val = LineEdit()
        self.ed_val.setText(str(task_data.get("value", "10")))
        
        self.lbl_unit = BodyLabel()
        self.lbl_unit.setStyleSheet("color: #666;")
        
        logic.addWidget(StrongBodyLabel("模式:"))
        logic.addWidget(self.cb_mode)
        logic.addSpacing(10)
        
        logic.addWidget(StrongBodyLabel("设定值:"))
        logic.addWidget(self.ed_val)
        logic.addWidget(self.lbl_unit)
        logic.addStretch(1)
        
        self.btn_run = PushButton("测试执行")
        self.btn_run.setIcon(FluentIcon.SEND)
        self.btn_run.clicked.connect(lambda: self.on_run(self._get_data()))
        
        self.btn_del = PushButton("删除")
        self.btn_del.setIcon(FluentIcon.DELETE)
        self.btn_del.clicked.connect(lambda: self.on_delete(self.task_id))
        
        logic.addWidget(self.btn_run)
        logic.addWidget(self.btn_del)
        
        lay.addLayout(logic)

        # 动态更新提示标签
        def update_unit_label():
            idx = self.cb_mode.currentIndex()
            if idx == 0:
                self.lbl_unit.setText("条 (收到N条后执行)")
                self.ed_val.setPlaceholderText("如: 10")
            elif idx == 1:
                self.lbl_unit.setText("时间点 (如: 08:00)")
                self.ed_val.setPlaceholderText("如: 08:00, 20:00")
            elif idx == 2:
                self.lbl_unit.setText("分钟 (每隔N分钟执行)")
                self.ed_val.setPlaceholderText("如: 60")
                
        self.cb_mode.currentIndexChanged.connect(update_unit_label)
        update_unit_label()

        self.ed_name.textChanged.connect(self._sync)
        self.ed_val.textChanged.connect(self._sync)
        self.ed_prompt.textChanged.connect(self._sync)
        self.sw_enabled.checkedChanged.connect(self._sync)
        self.cb_mode.currentIndexChanged.connect(self._sync)

    def _get_data(self):
        modes = ["count", "time", "interval"]
        domains = []
        if self.chk_gotify.isChecked(): domains.append("gotify")
        if self.chk_rss.isChecked(): domains.append("rss")
        if self.chk_imap.isChecked(): domains.append("imap")
        if self.chk_web3.isChecked(): domains.append("web3")
        
        # 安全数字转换
        def safe_int(val_str, default_val):
            try:
                v = int(val_str.strip())
                return v if v > 0 else default_val
            except Exception:
                return default_val

        return {
            "id": self.task_id, 
            "name": self.ed_name.text(), 
            "prompt": self.ed_prompt.toPlainText(), 
            "enabled": self.sw_enabled.isChecked(), 
            "mode": modes[self.cb_mode.currentIndex()], 
            "value": self.ed_val.text().strip(), 
            "domains": domains,
            "limit_gotify": safe_int(self.sp_gotify.text(), 20),
            "limit_rss": safe_int(self.sp_rss.text(), 10),
            "limit_imap": safe_int(self.sp_imap.text(), 10),
            "limit_web3": safe_int(self.sp_web3.text(), 20)
        }
        
    def _sync(self): 
        self.on_save(self._get_data())

class AiTasksPage(QWidget):
    def __init__(self, ai_manager, get_settings, save_settings):
        super().__init__()
        self.setObjectName("ai_tasks_page")
        self.ai_manager = ai_manager
        self.get_settings = get_settings
        self.save_settings = save_settings
        self.lang = getattr(self.get_settings(), "language", "简体中文")

        self.ai_manager.task_status_signal.connect(self._show_status)
        
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        
        header = QHBoxLayout()
        header.addWidget(TitleLabel("AI 自动化中心"))
        header.addStretch(1)
        
        self.btn_save = PushButton("保存并固化")
        self.btn_save.setIcon(FluentIcon.SAVE)
        self.btn_save.clicked.connect(self._on_save_all)
        
        self.btn_add = PushButton("新建任务")
        self.btn_add.setIcon(FluentIcon.ADD)
        self.btn_add.clicked.connect(self._add_task)
        
        header.addWidget(self.btn_save)
        header.addWidget(self.btn_add)
        root.addLayout(header)

        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(15)
        self.layout.addWidget(GuideCard(self.lang)) 
        
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)
        self._refresh()

    def _show_status(self, n, m, e):
        if e: 
            InfoBar.error(n, m, position=InfoBarPosition.TOP, parent=self)
        else: 
            InfoBar.info(n, m, position=InfoBarPosition.TOP, parent=self)

    def _refresh(self):
        for i in reversed(range(1, self.layout.count())):
            w = self.layout.itemAt(i).widget()
            if w: 
                w.deleteLater()
                
        for t in self.get_settings().ai_tasks:
            self.layout.addWidget(TaskCard(t, self.lang, self._delete, self._update_mem, self.ai_manager.run_task_async))

    def _update_mem(self, data):
        s = self.get_settings()
        for i, t in enumerate(s.ai_tasks):
            if t["id"] == data["id"]: 
                s.ai_tasks[i] = data
                break
        self.ai_manager.update_settings(s)

    def _on_save_all(self):
        self.save_settings(self.get_settings())
        InfoBar.success("成功", "所有任务已同步", parent=self)

    def _add_task(self):
        new_t = {
            "id": str(uuid.uuid4()), 
            "name": "信息汇总", 
            "prompt": "请总结以下跨领域信息：", 
            "mode": "count", 
            "value": "10", 
            "enabled": True, 
            "domains": ["gotify", "rss", "imap", "web3"],
            "limit_gotify": 20,
            "limit_rss": 10,
            "limit_imap": 10,
            "limit_web3": 20
        }
        s = self.get_settings()
        s.ai_tasks.append(new_t)
        self._on_save_all()
        self._refresh()

    def _delete(self, tid):
        s = self.get_settings()
        s.ai_tasks = [t for t in s.ai_tasks if t["id"] != tid]
        self._on_save_all()
        self._refresh()