# ui_tasks.py
import uuid
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (CardWidget, PushButton, LineEdit, TextEdit, TitleLabel, 
                            SubtitleLabel, BodyLabel, ComboBox, SwitchButton, FluentIcon, 
                            SpinBox, InfoBar, InfoBarPosition, StrongBodyLabel, ScrollArea)

class GuideCard(CardWidget):
    def __init__(self, lang, parent=None):
        super().__init__(parent)
        is_en = lang == "English"
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 15, 20, 15)
        lay.addWidget(SubtitleLabel("💡 User Guide" if is_en else "💡 AI 自动化指南"))
        guide = (
            "1. **Count**: Run after N new messages.\n2. **Time**: Run at fixed points (e.g., 08:00).\n3. **Interval**: Run every N minutes." if is_en else
            "1. **累计触发**：每满 N 条通知运行一次。\n2. **定时触发**：每天 08:00, 20:00 准点总结。\n3. **固定频率**：每隔 60 分钟梳理一次。"
        )
        lbl = BodyLabel(guide); lbl.setTextFormat(Qt.MarkdownText); lay.addWidget(lbl)

class TaskCard(CardWidget):
    def __init__(self, task_data, lang, on_delete, on_save, on_run):
        super().__init__()
        self.task_id = task_data.get("id"); self.lang = lang
        self.on_run, self.on_delete, self.on_save = on_run, on_delete, on_save
        is_en = lang == "English"
        lay = QVBoxLayout(self)
        
        head = QHBoxLayout()
        self.ed_name = LineEdit(); self.ed_name.setText(task_data.get("name", "New Task"))
        self.sw_enabled = SwitchButton("Enable" if is_en else "启用")
        self.sw_enabled.setChecked(task_data.get("enabled", True))
        head.addWidget(StrongBodyLabel("Name:" if is_en else "任务名:")); head.addWidget(self.ed_name, 1); head.addWidget(self.sw_enabled)
        lay.addLayout(head)

        lay.addWidget(StrongBodyLabel("AI Prompt (Instruction):" if is_en else "AI 处理指令 (Prompt):"))
        self.ed_prompt = TextEdit(); self.ed_prompt.setText(task_data.get("prompt", "")); self.ed_prompt.setFixedHeight(80)
        lay.addWidget(self.ed_prompt)

        logic = QHBoxLayout()
        self.cb_mode = ComboBox()
        self.cb_mode.addItems(["By Count" if is_en else "累计计数触发", "By Time" if is_en else "定时点执行", "By Interval" if is_en else "固定间隔执行"])
        self.cb_mode.setCurrentIndex({"count": 0, "time": 1, "interval": 2}.get(task_data.get("mode", "count"), 0))
        self.ed_val = LineEdit(); self.ed_val.setText(str(task_data.get("value", "10")))
        self.sp_limit = SpinBox(); self.sp_limit.setRange(1, 1000); self.sp_limit.setValue(int(task_data.get("context_limit", 50)))
        
        logic.addWidget(StrongBodyLabel("Mode:" if is_en else "模式:")); logic.addWidget(self.cb_mode, 1)
        logic.addWidget(StrongBodyLabel("Value:" if is_en else "数值:")); logic.addWidget(self.ed_val, 1)
        logic.addWidget(StrongBodyLabel("Limit:" if is_en else "分析条数:")); logic.addWidget(self.sp_limit, 1)
        lay.addLayout(logic)

        btns = QHBoxLayout(); self.btn_run = PushButton("Test Run" if is_en else "测试执行"); self.btn_run.setIcon(FluentIcon.SEND)
        self.btn_run.clicked.connect(lambda: self.on_run(self._get_data()))
        self.btn_del = PushButton("Delete" if is_en else "删除"); self.btn_del.setIcon(FluentIcon.DELETE)
        self.btn_del.clicked.connect(lambda: self.on_delete(self.task_id))
        btns.addStretch(1); btns.addWidget(self.btn_run); btns.addWidget(self.btn_del); lay.addLayout(btns)

        for w in [self.ed_name, self.ed_val]: w.textChanged.connect(self._sync)
        self.ed_prompt.textChanged.connect(self._sync)
        self.sw_enabled.checkedChanged.connect(self._sync)
        self.cb_mode.currentIndexChanged.connect(self._sync)
        self.sp_limit.valueChanged.connect(self._sync)

    def _get_data(self):
        modes = ["count", "time", "interval"]
        return {"id": self.task_id, "name": self.ed_name.text(), "prompt": self.ed_prompt.toPlainText(), "enabled": self.sw_enabled.isChecked(), "mode": modes[self.cb_mode.currentIndex()], "value": self.ed_val.text().strip(), "context_limit": self.sp_limit.value()}
    def _sync(self): self.on_save(self._get_data())

class AiTasksPage(QWidget):
    def __init__(self, ai_manager, get_settings, save_settings):
        super().__init__()
        self.setObjectName("ai_tasks_page")
        self.ai_manager, self.get_settings, self.save_settings = ai_manager, get_settings, save_settings
        self.lang = getattr(self.get_settings(), "language", "简体中文")
        is_en = self.lang == "English"

        self.ai_manager.task_status_signal.connect(self._show_status)
        root = QVBoxLayout(self); root.setContentsMargins(24, 18, 24, 18)
        
        header = QHBoxLayout(); header.addWidget(TitleLabel("Task Center" if is_en else "AI 自动化中心")); header.addStretch(1)
        self.btn_save = PushButton("Save All" if is_en else "保存并固化"); self.btn_save.setIcon(FluentIcon.SAVE); self.btn_save.clicked.connect(self._on_save_all)
        self.btn_add = PushButton("New Task" if is_en else "新建任务"); self.btn_add.setIcon(FluentIcon.ADD); self.btn_add.clicked.connect(self._add_task)
        header.addWidget(self.btn_save); header.addWidget(self.btn_add); root.addLayout(header)

        self.scroll = ScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setStyleSheet("background:transparent; border:none;")
        self.container = QWidget(); self.layout = QVBoxLayout(self.container); self.layout.setAlignment(Qt.AlignTop); self.layout.setSpacing(15)
        self.layout.addWidget(GuideCard(self.lang)) 
        self.scroll.setWidget(self.container); root.addWidget(self.scroll)
        self._refresh()

    def _show_status(self, n, m, e):
        if e: InfoBar.error(n, m, position=InfoBarPosition.TOP, parent=self)
        else: InfoBar.info(n, m, position=InfoBarPosition.TOP, parent=self)

    def _refresh(self):
        for i in reversed(range(1, self.layout.count())):
            w = self.layout.itemAt(i).widget()
            if w: w.deleteLater()
        for t in self.get_settings().ai_tasks:
            self.layout.addWidget(TaskCard(t, self.lang, self._delete, self._update_mem, self.ai_manager.run_task_async))

    def _update_mem(self, data):
        s = self.get_settings()
        for i, t in enumerate(s.ai_tasks):
            if t["id"] == data["id"]: s.ai_tasks[i] = data; break
        self.ai_manager.update_settings(s)

    def _on_save_all(self):
        self.save_settings(self.get_settings())
        is_en = self.lang == "English"
        InfoBar.success("Success" if is_en else "成功", "Tasks updated" if is_en else "所有任务已同步", parent=self)

    def _add_task(self):
        is_en = self.lang == "English"
        new_t = {"id": str(uuid.uuid4()), "name": "New Task" if is_en else "通知总结", "prompt": "Summary this..." if is_en else "请总结这些内容", "mode": "count", "value": "10", "enabled": True, "context_limit": 50}
        s = self.get_settings(); s.ai_tasks.append(new_t); self._on_save_all(); self._refresh()

    def _delete(self, tid):
        s = self.get_settings(); s.ai_tasks = [t for t in s.ai_tasks if t["id"] != tid]; self._on_save_all(); self._refresh()