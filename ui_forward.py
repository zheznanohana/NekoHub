# ui_forward.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (CardWidget, PushButton, LineEdit, TitleLabel, 
                            SubtitleLabel, BodyLabel, SwitchButton, ComboBox, 
                            InfoBar, InfoBarPosition, StrongBodyLabel, ScrollArea)
from PySide6.QtCore import Qt

class ForwardPage(QWidget):
    def __init__(self, get_settings, save_settings):
        super().__init__()
        self.setObjectName("forward_page")
        self._get, self._save = get_settings, save_settings
        
        self.lang = getattr(self._get(), "language", "简体中文")
        is_en = self.lang == "English"

        root = QVBoxLayout(self); root.setContentsMargins(24, 18, 24, 18)
        header = QHBoxLayout(); header.addWidget(TitleLabel("Forwarding Center" if is_en else "通知转发中心")); header.addStretch(1)
        self.btn_save = PushButton("Apply Config" if is_en else "保存并应用配置"); self.btn_save.clicked.connect(self._on_save)
        header.addWidget(self.btn_save); root.addLayout(header)

        self.scroll = ScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setStyleSheet("background:transparent; border:none;")
        container = QWidget(); lay = QVBoxLayout(container); lay.setSpacing(15); lay.setAlignment(Qt.AlignTop)

        # 1. Mode
        c1 = CardWidget(); l1 = QVBoxLayout(c1)
        self.sw_enable = SwitchButton("Enable Forwarding" if is_en else "开启全局外转")
        l1.addWidget(self.sw_enable)
        self.cb_mode = ComboBox(); 
        self.cb_mode.addItems(["All (Raw+AI)" if is_en else "全部外转 (原始+AI)", "Raw Only" if is_en else "仅转发原始通知", "AI Only" if is_en else "仅转发 AI 分析结果"])
        l1.addWidget(StrongBodyLabel("Filter Mode:" if is_en else "转发内容筛选:")); l1.addWidget(self.cb_mode); lay.addWidget(c1)

        # 2. DingTalk
        c2 = CardWidget(); l2 = QVBoxLayout(c2); l2.addWidget(SubtitleLabel("DingTalk Bot"))
        self.ed_ding_url = LineEdit(); self.ed_ding_url.setPlaceholderText("Webhook URL")
        self.ed_ding_sec = LineEdit(); self.ed_ding_sec.setPlaceholderText("Secret (Leave empty if not set)")
        self.ed_ding_sec.setEchoMode(LineEdit.Password)
        l2.addWidget(StrongBodyLabel("Webhook:")); l2.addWidget(self.ed_ding_url)
        l2.addWidget(StrongBodyLabel("Secret:")); l2.addWidget(self.ed_ding_sec); lay.addWidget(c2)

        # 3. Telegram
        c3 = CardWidget(); l3 = QVBoxLayout(c3); l3.addWidget(SubtitleLabel("Telegram Bot"))
        self.ed_tg_tk = LineEdit(); self.ed_tg_tk.setPlaceholderText("Bot Token")
        self.ed_tg_id = LineEdit(); self.ed_tg_id.setPlaceholderText("Chat ID (Numeric for user, -100 for groups)")
        l3.addWidget(StrongBodyLabel("Token:")); l3.addWidget(self.ed_tg_tk)
        l3.addWidget(StrongBodyLabel("Chat ID:")); l3.addWidget(self.ed_tg_id); lay.addWidget(c3)

        # 4. Email
        c4 = CardWidget(); l4 = QVBoxLayout(c4); l4.addWidget(SubtitleLabel("Email (SMTP)"))
        self.ed_m_host = LineEdit(); self.ed_m_user = LineEdit(); self.ed_m_pass = LineEdit(); self.ed_m_to = LineEdit()
        self.ed_m_pass.setEchoMode(LineEdit.Password)
        for e, t in [(self.ed_m_host, "Host"), (self.ed_m_user, "User"), (self.ed_m_pass, "Pass"), (self.ed_m_to, "Recipient")] if is_en else [(self.ed_m_host, "SMTP服务器"), (self.ed_m_user, "发件邮箱"), (self.ed_m_pass, "授权码"), (self.ed_m_to, "收件邮箱")]:
            l4.addWidget(StrongBodyLabel(t)); l4.addWidget(e)
        lay.addWidget(c4)

        self.scroll.setWidget(container); root.addWidget(self.scroll); self._load()

    def _load(self):
        s = self._get()
        self.sw_enable.setChecked(s.forward_enabled); self.cb_mode.setCurrentIndex(s.forward_mode)
        self.ed_ding_url.setText(s.dingtalk_webhook); self.ed_ding_sec.setText(s.dingtalk_secret)
        self.ed_tg_tk.setText(s.tg_bot_token); self.ed_tg_id.setText(s.tg_chat_id)
        self.ed_m_host.setText(s.email_smtp); self.ed_m_user.setText(s.email_user)
        self.ed_m_pass.setText(s.email_pass); self.ed_m_to.setText(s.email_to)

    def _on_save(self):
        s = self._get()
        s.forward_enabled = self.sw_enable.isChecked(); s.forward_mode = self.cb_mode.currentIndex()
        s.dingtalk_webhook, s.dingtalk_secret = self.ed_ding_url.text().strip(), self.ed_ding_sec.text().strip()
        s.tg_bot_token, s.tg_chat_id = self.ed_tg_tk.text().strip(), self.ed_tg_id.text().strip()
        s.email_smtp, s.email_user = self.ed_m_host.text().strip(), self.ed_m_user.text().strip()
        s.email_pass, s.email_to = self.ed_m_pass.text().strip(), self.ed_m_to.text().strip()
        self._save(s)
        is_en = self.lang == "English"
        InfoBar.success("Success" if is_en else "成功", "Config applied" if is_en else "转发设置已生效", parent=self)