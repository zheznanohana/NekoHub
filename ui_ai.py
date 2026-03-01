# ui_ai.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (CardWidget, PushButton, LineEdit, TextEdit, TitleLabel, 
                            SubtitleLabel, BodyLabel, SpinBox, InfoBar, InfoBarPosition)
from PySide6.QtCore import Qt

class AiPage(QWidget):
    def __init__(self, ai_manager, get_settings, save_settings):
        super().__init__()
        self.setObjectName("ai_chat_page") 
        self.ai_manager, self.get_settings, self.save_settings = ai_manager, get_settings, save_settings
        
        # 获取语言设置
        s = self.get_settings()
        self.lang = getattr(s, "language", "简体中文")
        is_en = self.lang == "English"

        self.ai_manager.chat_response_ready.connect(self._on_reply)

        root = QVBoxLayout(self); root.setContentsMargins(24, 18, 24, 18)
        root.addWidget(TitleLabel("AI Assistant" if is_en else "AI 助手对话"))

        # 1. 接口配置区
        config = CardWidget(); c_lay = QVBoxLayout(config)
        self.ed_url = LineEdit(); self.ed_api = LineEdit(); self.ed_api.setEchoMode(LineEdit.Password)
        self.ed_model = LineEdit()
        
        c_lay.addWidget(SubtitleLabel("API Configuration" if is_en else "模型接口全局配置"))
        self.ed_url.setPlaceholderText("API Base URL")
        self.ed_api.setPlaceholderText("API Key")
        self.ed_model.setPlaceholderText("Model Name (e.g. deepseek-chat)")
        c_lay.addWidget(self.ed_url); c_lay.addWidget(self.ed_api); c_lay.addWidget(self.ed_model)
        
        row_limit = QHBoxLayout()
        row_limit.addWidget(BodyLabel("Context Limit (Messages):" if is_en else "助手对话参考最近通知条数:"))
        self.sp_limit = SpinBox(); self.sp_limit.setRange(1, 1000)
        row_limit.addWidget(self.sp_limit); row_limit.addStretch(1)
        c_lay.addLayout(row_limit)
        
        self.btn_save = PushButton("Save Configuration" if is_en else "保存并应用配置")
        self.btn_save.clicked.connect(self._save_config); c_lay.addWidget(self.btn_save)
        root.addWidget(config)

        # 2. 对话展示区 (使用 TextEdit 获得漂亮滚动条)
        chat = CardWidget(); chat_lay = QVBoxLayout(chat)
        chat_lay.addWidget(SubtitleLabel("Live Chat" if is_en else "上下文实时对话"))
        self.history = TextEdit(); self.history.setReadOnly(True)
        self.history.setStyleSheet("background:transparent; border:none; font-family: 'Segoe UI', 'Microsoft YaHei';")
        chat_lay.addWidget(self.history)
        
        # 3. 输入区
        input_lay = QHBoxLayout()
        self.input = LineEdit()
        self.input.setPlaceholderText("Type your question here..." if is_en else "在这里输入您的问题...")
        self.input.returnPressed.connect(self._send)
        self.btn_send = PushButton("Send" if is_en else "发送")
        self.btn_send.clicked.connect(self._send)
        input_lay.addWidget(self.input, 1); input_lay.addWidget(self.btn_send, 0)
        chat_lay.addLayout(input_lay); root.addWidget(chat, 1)

        self._load_config()

    def _load_config(self):
        s = self.get_settings()
        self.ed_url.setText(s.ai_base_url); self.ed_api.setText(s.ai_api_key); self.ed_model.setText(s.ai_model)
        self.sp_limit.setValue(getattr(s, "ai_chat_context_limit", 50))

    def _save_config(self):
        s = self.get_settings()
        s.ai_base_url, s.ai_api_key, s.ai_model = self.ed_url.text().strip(), self.ed_api.text().strip(), self.ed_model.text().strip()
        s.ai_chat_context_limit = self.sp_limit.value()
        self.save_settings(s); self.ai_manager.update_settings(s)
        is_en = self.lang == "English"
        InfoBar.success("Success" if is_en else "保存成功", "API config updated" if is_en else "API 配置已更新", parent=self)

    def _send(self):
        text = self.input.text().strip()
        if text:
            is_en = self.lang == "English"
            self.history.moveCursor(self.history.textCursor().End)
            self.history.insertHtml(f"<br><b style='color:#0078d4;'>{'User' if is_en else '问'}:</b> {text}<br>")
            self.input.clear(); self.ai_manager.send_chat_async(text)

    def _on_reply(self, text):
        is_en = self.lang == "English"
        self.history.moveCursor(self.history.textCursor().End)
        self.history.insertHtml(f"<b style='color:#107c10;'>{'AI' if is_en else '答'}:</b><br>")
        self.history.insertMarkdown(text)
        self.history.insertHtml("<br>")
        self.history.verticalScrollBar().setValue(self.history.verticalScrollBar().maximum())