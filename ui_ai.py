# ui_ai.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit
from qfluentwidgets import (CardWidget, PushButton, LineEdit, 
                            TitleLabel, SubtitleLabel, BodyLabel, ComboBox, SpinBox)

class AiPage(QWidget):
    def __init__(self, ai_manager, get_settings_cb, save_settings_cb):
        super().__init__()
        self.setObjectName("ai_page")
        self.ai_manager = ai_manager
        self.get_settings = get_settings_cb
        self.save_settings = save_settings_cb
        
        self.ai_manager.chat_response_ready.connect(self._on_chat_response)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)
        root.addWidget(TitleLabel("AI 助手与摘要配置"))

        # ---- AI 配置卡片 ----
        config_card = CardWidget()
        config_card.setBorderRadius(12)
        c_lay = QVBoxLayout(config_card)
        c_lay.setContentsMargins(16, 14, 16, 14)
        
        self.ed_api = LineEdit()
        self.ed_api.setPlaceholderText("API Key (支持 OpenAI 格式)")
        self.ed_url = LineEdit()
        self.ed_url.setPlaceholderText("Base URL (如 https://api.openai.com/v1)")
        self.ed_model = LineEdit()
        self.ed_model.setPlaceholderText("模型名称 (如 gpt-3.5-turbo)")
        
        self.cb_mode = ComboBox()
        self.cb_mode.addItems(["按条数触发", "按时间触发"])
        self.sp_count = SpinBox()
        self.sp_count.setRange(1, 1000)
        self.ed_time = LineEdit()
        self.ed_time.setPlaceholderText("每天触发时间 (如 08:00,18:00)")

        c_lay.addWidget(SubtitleLabel("API 接口配置"))
        c_lay.addWidget(self.ed_url)
        c_lay.addWidget(self.ed_api)
        c_lay.addWidget(self.ed_model)
        
        c_lay.addWidget(SubtitleLabel("自动摘要规则"))
        r1 = QHBoxLayout()
        r1.addWidget(BodyLabel("触发模式:"))
        r1.addWidget(self.cb_mode)
        r1.addWidget(BodyLabel("条数阈值:"))
        r1.addWidget(self.sp_count)
        r1.addWidget(BodyLabel("触发时间(逗号分隔):"))
        r1.addWidget(self.ed_time)
        c_lay.addLayout(r1)
        
        # --- 新增了手动按钮并放在同一排 ---
        self.btn_save = PushButton("保存 AI 配置")
        self.btn_save.clicked.connect(self._on_save)
        
        self.btn_manual = PushButton("手动生成并发送摘要")
        self.btn_manual.clicked.connect(self._on_manual)
        
        btn_lay = QHBoxLayout()
        btn_lay.addWidget(self.btn_save)
        btn_lay.addWidget(self.btn_manual)
        btn_lay.addStretch(1)
        
        c_lay.addLayout(btn_lay)
        # --------------------------------
        
        root.addWidget(config_card, 0)

        # ---- 聊天对话区域 ----
        chat_card = CardWidget()
        chat_card.setBorderRadius(12)
        chat_lay = QVBoxLayout(chat_card)
        chat_lay.addWidget(SubtitleLabel("与 AI 讨论通知记录"))
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background-color: transparent; border: none; font-size: 14px;")
        chat_lay.addWidget(self.chat_history, 1)
        
        input_lay = QHBoxLayout()
        self.chat_input = LineEdit()
        self.chat_input.setPlaceholderText("在此输入你想问 AI 的问题...")
        self.chat_input.returnPressed.connect(self._on_send)
        self.btn_send = PushButton("发送")
        self.btn_send.clicked.connect(self._on_send)
        
        input_lay.addWidget(self.chat_input, 1)
        input_lay.addWidget(self.btn_send, 0)
        chat_lay.addLayout(input_lay)
        
        root.addWidget(chat_card, 1)
        self._load_config()

    def _load_config(self):
        s = self.get_settings()
        self.ed_api.setText(s.ai_api_key)
        self.ed_url.setText(s.ai_base_url)
        self.ed_model.setText(s.ai_model)
        self.cb_mode.setCurrentIndex(0 if s.ai_summary_mode == "count" else 1)
        self.sp_count.setValue(s.ai_summary_count)
        self.ed_time.setText(s.ai_summary_times)

    def _on_save(self):
        s = self.get_settings()
        s.ai_api_key = self.ed_api.text().strip()
        s.ai_base_url = self.ed_url.text().strip()
        s.ai_model = self.ed_model.text().strip()
        s.ai_summary_mode = "count" if self.cb_mode.currentIndex() == 0 else "time"
        s.ai_summary_count = self.sp_count.value()
        s.ai_summary_times = self.ed_time.text().strip()
        self.save_settings(s)
        self.ai_manager.update_settings(s)
        self.chat_history.append("<i>[系统] AI 配置已保存。</i><br>")
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())

    # --- 这里是手动触发按钮的事件 ---
    def _on_manual(self):
        self.chat_history.append("<i>[系统] 已触发手动摘要，正在后台生成并发送至 Gotify...</i><br>")
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())
        self.ai_manager.trigger_summary_async("手动触发摘要：")
    # -----------------------------

    def _on_send(self):
        text = self.chat_input.text().strip()
        if not text: return
        self.chat_history.append(f'<span style="color: #0068B5;"><b>You:</b> {text}</span>')
        self.chat_input.clear()
        self.chat_history.append("<i>AI 正在思考中...</i>")
        self.ai_manager.send_chat_async(text)

    def _on_chat_response(self, reply: str):
        self.chat_history.append(f'<span style="color: #2D2D2D;"><b>AI:</b> {reply}</span><br>')
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())
