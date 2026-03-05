# ui_ai.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget
from qfluentwidgets import (CardWidget, PushButton, LineEdit, TextEdit, TitleLabel, 
                            SubtitleLabel, BodyLabel, InfoBar, CheckBox, 
                            StrongBodyLabel, ComboBox, MessageBoxBase, FluentIcon)
from PySide6.QtCore import Qt, QTimer

class AiConfigDialog(MessageBoxBase):
    def __init__(self, parent_window, profiles, lang):
        super().__init__(parent_window)
        self.is_en = lang == "English"
        self.viewLayout.addWidget(SubtitleLabel("Model Management" if self.is_en else "AI 模型配置管理"))
        
        self.list_widget = QListWidget()
        self.list_widget.addItems(profiles)
        self.viewLayout.addWidget(self.list_widget)

        lay = QVBoxLayout()
        self.ed_name = LineEdit()
        self.ed_name.setPlaceholderText("Profile Name" if self.is_en else "备注名 (如: DeepSeek)")
        
        self.ed_url = LineEdit()
        self.ed_url.setPlaceholderText("API URL (如: https://api.deepseek.com/v1)")
        
        self.ed_key = LineEdit()
        self.ed_key.setPlaceholderText("API Key")
        self.ed_key.setEchoMode(LineEdit.Password)
        
        self.ed_model = LineEdit()
        self.ed_model.setPlaceholderText("Model Name" if self.is_en else "模型名 (如: deepseek-chat)")
        
        for w in [self.ed_name, self.ed_url, self.ed_key, self.ed_model]:
            lay.addWidget(w)
            
        btn_lay = QHBoxLayout()
        self.btn_add = PushButton("Add" if self.is_en else "添加")
        self.btn_del = PushButton("Delete" if self.is_en else "删除")
        
        self.btn_add.clicked.connect(lambda: self.list_widget.addItem(f"{self.ed_name.text()}|{self.ed_url.text()}|{self.ed_key.text()}|{self.ed_model.text()}") if self.ed_name.text() and self.ed_url.text() else None)
        self.btn_del.clicked.connect(lambda: [self.list_widget.takeItem(self.list_widget.row(i)) for i in self.list_widget.selectedItems()])
        
        btn_lay.addWidget(self.btn_add)
        btn_lay.addWidget(self.btn_del)
        lay.addLayout(btn_lay)
        self.viewLayout.addLayout(lay)
        self.widget.setMinimumWidth(550)


class AiPage(QWidget):
    def __init__(self, ai_manager, get_settings, save_settings):
        super().__init__()
        self.setObjectName("ai_chat_page") 
        self.ai_manager = ai_manager
        self.get_settings = get_settings
        self.save_settings = save_settings
        
        s = self.get_settings()
        self.lang = getattr(s, "language", "简体中文")
        self.is_en = self.lang == "English"

        self.chat_log = "" 
        self.thinking_mark = "" 
        self._is_loading = True

        self.ai_manager.chat_response_ready.connect(self._on_reply)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)

        # 1. 顶部 Header
        header_lay = QHBoxLayout()
        header_lay.addWidget(TitleLabel("AI Assistant" if self.is_en else "AI 助手对话"))
        header_lay.addStretch(1)
        
        header_lay.addWidget(StrongBodyLabel("Current Model:" if self.is_en else "当前模型:"))
        self.cb_models = ComboBox()
        self.cb_models.setMinimumWidth(150)
        self.cb_models.currentIndexChanged.connect(self._on_model_changed)
        header_lay.addWidget(self.cb_models)
        
        self.btn_config = PushButton("Manage" if self.is_en else "管理配置")
        self.btn_config.setIcon(FluentIcon.SETTING)
        self.btn_config.clicked.connect(self._open_config)
        header_lay.addWidget(self.btn_config)
        
        root.addLayout(header_lay)

        # 2. 对话历史区
        self.history = TextEdit()
        self.history.setReadOnly(True)
        root.addWidget(self.history, 1)

        # 3. [完美极简重构]：用纯文本输入框替代 SpinBox
        source_card = CardWidget()
        s_lay = QHBoxLayout(source_card)
        s_lay.setContentsMargins(15, 10, 15, 10)
        s_lay.addWidget(StrongBodyLabel("带入背景数据(条数):"))
        
        def make_inline_pair(label_text, default_val, setting_key):
            chk = CheckBox(label_text)
            chk.setChecked(True)
            # 使用普通的 LineEdit，拒绝箭头
            sp = LineEdit()
            sp.setFixedWidth(50) 
            sp.setText(str(getattr(s, setting_key, default_val)))
            sp.textChanged.connect(self._save_fine_limits)
            return chk, sp

        self.chk_gotify, self.sp_gotify = make_inline_pair("通知", 20, "ai_limit_gotify")
        self.chk_rss, self.sp_rss = make_inline_pair("订阅", 10, "ai_limit_rss")
        self.chk_imap, self.sp_imap = make_inline_pair("邮件", 10, "ai_limit_imap")
        self.chk_web3, self.sp_web3 = make_inline_pair("链上", 20, "ai_limit_web3")

        # 按顺序排列到同一行
        for w in [self.chk_gotify, self.sp_gotify, self.chk_rss, self.sp_rss, self.chk_imap, self.sp_imap, self.chk_web3, self.sp_web3]:
            s_lay.addWidget(w)
            if isinstance(w, LineEdit):
                s_lay.addSpacing(15)
                
        s_lay.addStretch(1)
        root.addWidget(source_card)

        # 4. 输入区
        inp_lay = QHBoxLayout()
        self.input = TextEdit()
        self.input.setFixedHeight(80)
        self.input.setPlaceholderText("Ask anything..." if self.is_en else "在此输入你想问的问题，AI 将结合上方勾选的数据源为您解答...")
        
        self.btn_send = PushButton("Send" if self.is_en else "发送")
        self.btn_send.setFixedHeight(80)
        self.btn_send.clicked.connect(self._on_send)
        
        inp_lay.addWidget(self.input, 1)
        inp_lay.addWidget(self.btn_send)
        root.addLayout(inp_lay)

        self._load_profiles()

    def _save_fine_limits(self):
        if self._is_loading: 
            return
        s = self.get_settings()
        
        # 安全转换：防止输入框为空或填入字母时报错
        def safe_int(widget, default_val):
            try:
                val = int(widget.text().strip())
                return val if val > 0 else default_val
            except Exception:
                return default_val

        s.ai_limit_gotify = safe_int(self.sp_gotify, 20)
        s.ai_limit_rss = safe_int(self.sp_rss, 10)
        s.ai_limit_imap = safe_int(self.sp_imap, 10)
        s.ai_limit_web3 = safe_int(self.sp_web3, 20)
        
        self.save_settings(s)
        self.ai_manager.update_settings(s)

    def _load_profiles(self):
        self._is_loading = True
        s = self.get_settings()
        self.profiles = getattr(s, "ai_profiles", [])
        
        if not self.profiles:
            old_url = getattr(s, "ai_base_url", "https://api.deepseek.com/v1")
            old_key = getattr(s, "ai_api_key", "")
            old_model = getattr(s, "ai_model", "deepseek-chat")
            self.profiles = [f"默认配置|{old_url}|{old_key}|{old_model}"]
            s.ai_profiles = self.profiles
            QTimer.singleShot(0, lambda: self.save_settings(s))
            
        self.cb_models.clear()
        for p in self.profiles:
            self.cb_models.addItem(p.split('|')[0] if '|' in p else p)
            
        active_idx = getattr(s, "ai_active_profile_idx", 0)
        if 0 <= active_idx < len(self.profiles):
            self.cb_models.setCurrentIndex(active_idx)
        else:
            self.cb_models.setCurrentIndex(0)
            
        self._is_loading = False

    def _open_config(self):
        w = AiConfigDialog(self.window(), self.profiles, self.lang)
        if w.exec():
            s = self.get_settings()
            s.ai_profiles = [w.list_widget.item(i).text() for i in range(w.list_widget.count())]
            self.save_settings(s)
            self._load_profiles()
            
    def _on_model_changed(self, idx):
        if self._is_loading or idx < 0 or idx >= len(self.profiles): 
            return
            
        parts = self.profiles[idx].split('|')
        s = self.get_settings()
        s.ai_active_profile_idx = idx
        
        s.ai_base_url = parts[1] if len(parts) > 1 else ""
        s.ai_api_key = parts[2] if len(parts) > 2 else ""
        s.ai_model = parts[3] if len(parts) > 3 else ""
        
        self.save_settings(s)
        self.ai_manager.update_settings(s)

    def _on_send(self):
        text = self.input.toPlainText().strip()
        if not text: 
            return
        
        user_label = "You" if self.is_en else "我"
        self.chat_log += f"**{user_label}**：{text}\n\n"
        self.thinking_mark = f"*{'AI is thinking...' if self.is_en else 'AI 正在思考中...'}*\n\n"
        self.chat_log += self.thinking_mark
        
        self.history.setMarkdown(self.chat_log)
        self.history.verticalScrollBar().setValue(self.history.verticalScrollBar().maximum())
        
        self.input.clear()
        self.input.setEnabled(False)
        self.btn_send.setEnabled(False)
        self.btn_send.setText("Wait..." if self.is_en else "稍等...")
        
        domains = []
        if self.chk_gotify.isChecked(): domains.append("gotify")
        if self.chk_rss.isChecked(): domains.append("rss")
        if self.chk_imap.isChecked(): domains.append("imap")
        if self.chk_web3.isChecked(): domains.append("web3")
        
        self.ai_manager.send_chat_async(text, domains)

    def _on_reply(self, text):
        ai_label = "AI" if self.is_en else "答"
        
        if self.thinking_mark and self.chat_log.endswith(self.thinking_mark):
            self.chat_log = self.chat_log[:-len(self.thinking_mark)]
            
        self.chat_log += f"**{ai_label}**：\n{text}\n\n---\n\n"
        self.history.setMarkdown(self.chat_log)
        self.history.verticalScrollBar().setValue(self.history.verticalScrollBar().maximum())
        
        self.input.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.btn_send.setText("Send" if self.is_en else "发送")
        self.input.setFocus()