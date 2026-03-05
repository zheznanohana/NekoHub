# ui_app.py
from __future__ import annotations

import sys
import os
import threading
import json
import time
import urllib.parse
import hmac
import hashlib
import base64
import requests
import smtplib
from email.mime.text import MIMEText
from dataclasses import asdict
from typing import List, Tuple, Optional

from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
    QLineEdit, QSpinBox, QStyle, QSystemTrayIcon, QMenu,
)

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon, TitleLabel, SubtitleLabel,
    BodyLabel, CardWidget, PushButton, LineEdit, setTheme, Theme, SwitchButton,
    ComboBox, InfoBar, InfoBarPosition, StrongBodyLabel, ScrollArea
)

# 导入业务模块
from settings import Settings, load_settings, save_settings
from notify_fx import SoundPlayer, ToastQueue
from ai_core import AiManager
from ui_ai import AiPage
from ui_tasks import AiTasksPage
from ui_forward import ForwardPage
from plugin_rss import RssPage
from plugin_imap import ImapPage
from plugin_web3 import Web3Page

# ---------------------------
# 多语言翻译字典
# ---------------------------
LANG_MAP = {
    "简体中文": {
        "inbox": "收件箱",
        "ai_chat": "AI 助手",
        "tasks": "自动化任务", 
        "forward": "消息转发",
        "settings": "系统设置",
        "rss": "RSS 订阅", 
        "imap": "邮件中心",
        "web3": "Web3 雷达",
        "ws_status": "WebSocket: ", 
        "ws_ready": "准备就绪",
        "ws_waiting": "等待参数",
        "clear_unread": "清除未读", 
        "new_msg": " ● 新消息",
        "wait_msg": "等待接收实时通知...",
        "save_success": "保存成功", 
        "save_hint": "配置已同步到本地",
        "test_push": "发送测试推送",
        "test_ok": "测试成功，请检查设备", 
        "toast_time": "通知驻留时长:",
        "poll_time": "同步间隔:",
        "lang_choice": "界面语言 (需重启):", 
        "sound_enable": "开启提示音",
        "save_all": "保存并应用所有设置", 
        "filter_title": "免打扰与过滤 (黑/白名单)",
        "filter_mode": "过滤模式:", 
        "filter_none": "不过滤 (接收所有)",
        "filter_black": "黑名单 (包含关键字不提醒)", 
        "filter_white": "白名单 (仅包含关键字才提醒)",
        "filter_kw": "关键字 (多个用逗号分隔):",
        "fwd_plugins": "外挂监控配置 (转发与频率)",
        "fwd_rss": "将 RSS 订阅更新转发至 Gotify",
        "fwd_imap": "将 新邮件提醒转发至 Gotify",
        "fwd_web3": "将 链上异动提醒转发至 Gotify"
    },
    "English": {
        "inbox": "Inbox",
        "ai_chat": "AI Chat",
        "tasks": "Tasks", 
        "forward": "Forwarding",
        "settings": "Settings",
        "rss": "RSS Feeds", 
        "imap": "Email Center",
        "web3": "Web3 Radar",
        "ws_status": "WS: ", 
        "ws_ready": "Ready",
        "ws_waiting": "Waiting config",
        "clear_unread": "Mark Read", 
        "new_msg": " ● New",
        "wait_msg": "Waiting for notifications...",
        "save_success": "Saved", 
        "save_hint": "Config updated locally",
        "test_push": "Test Push",
        "test_ok": "Test sent, check your device", 
        "toast_time": "Toast Duration:",
        "poll_time": "Sync Interval:",
        "lang_choice": "UI Language (Requires Restart):", 
        "sound_enable": "Enable Sound",
        "save_all": "Save All Changes", 
        "filter_title": "Notification Filter (Black/Whitelist)",
        "filter_mode": "Filter Mode:", 
        "filter_none": "No Filter (Allow All)",
        "filter_black": "Blacklist (Mute if contains keyword)", 
        "filter_white": "Whitelist (Mute unless contains keyword)",
        "filter_kw": "Keywords (comma separated):",
        "fwd_plugins": "Plugin Configurations",
        "fwd_rss": "Forward RSS Updates to Gotify",
        "fwd_imap": "Forward New Emails to Gotify",
        "fwd_web3": "Forward Web3 Radar to Gotify"
    }
}

def get_text(lang: str, key: str) -> str:
    data = LANG_MAP.get(lang, LANG_MAP["简体中文"])
    return data.get(key, key)

try:
    from storage import init_db, upsert_messages, latest_messages, get_meta, set_meta
except Exception:
    init_db = lambda: None
    def upsert_messages(m): pass
    def latest_messages(l): return []
    def get_meta(k): return None
    def set_meta(k, v): pass

try:
    from gotify_client import fetch_latest, send_message
    from gotify_ws import GotifyWSReceiver
except Exception:
    fetch_latest = send_message = GotifyWSReceiver = None

class UiRefreshCoalescer:
    def __init__(self, fn, interval_ms=200):
        self._fn = fn
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fn)
        self._int = interval_ms

    def request(self):
        if not self._timer.isActive():
            self._timer.start(self._int)

class TrayController:
    def __init__(self, window: QWidget, title="NekoHub", icon=None):
        self.window = window
        self.tray = QSystemTrayIcon(window)
        self.tray.setToolTip(title)
        
        if icon and not icon.isNull():
            self.tray.setIcon(icon)
        else:
            self.tray.setIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon))
            
        menu = QMenu()
        menu.addAction("Show").triggered.connect(self.restore)
        menu.addAction("Exit").triggered.connect(QApplication.quit)
        self.tray.setContextMenu(menu)
        
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.restore()

    def restore(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

class InboxPage(QWidget):
    def __init__(self, lang):
        super().__init__()
        self.setObjectName("inbox_page")
        self.lang = lang
        self._limit = 100
        self._unread = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        
        top = QHBoxLayout()
        top.addWidget(TitleLabel(get_text(lang, "inbox")), 0)
        
        self.lbl_unread = BodyLabel("")
        self.lbl_unread.setStyleSheet("color:#ff3b30; font-weight:700; padding-left:6px;")
        self.lbl_unread.hide()
        top.addWidget(self.lbl_unread, 0)
        
        top.addStretch(1)
        
        self.btn_mark = PushButton(get_text(lang, "clear_unread"))
        self.btn_mark.clicked.connect(self.clear_unread)
        top.addWidget(self.btn_mark, 0)
        
        root.addLayout(top)

        self.lbl_status = BodyLabel(get_text(lang, "ws_status") + get_text(lang, "ws_ready"))
        root.addWidget(self.lbl_status)

        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        
        self.container = QWidget()
        self.v = QVBoxLayout(self.container)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)
        
        self._cards = []

    def set_status(self, s: str):
        self.lbl_status.setText(get_text(self.lang, "ws_status") + s)

    def limit(self) -> int:
        return self._limit

    def add_unread(self, n=1):
        self._unread += n
        self._sync_unread()

    def clear_unread(self):
        self._unread = 0
        self._sync_unread()

    def _sync_unread(self):
        if self._unread <= 0:
            self.lbl_unread.hide()
        else:
            self.lbl_unread.setText(f"● {self._unread}")
            self.lbl_unread.show()

    def _make_card(self, row):
        card = CardWidget()
        lay = QVBoxLayout(card)
        
        head = QHBoxLayout()
        head.addWidget(SubtitleLabel(str(row[2]) if row[2] else "Gotify"), 0)
        head.addStretch(1)
        
        meta = BodyLabel(f"#{row[0]}")
        meta.setStyleSheet("opacity:0.4; font-size:10px;")
        head.addWidget(meta)
        lay.addLayout(head)
        
        body = BodyLabel(str(row[3]) or "")
        body.setWordWrap(True)
        lay.addWidget(body)
        
        return card

    def refresh_full(self, rows):
        while self.v.count():
            w = self.v.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._cards.clear()
        
        for r in rows:
            card = self._make_card(r)
            self.v.addWidget(card)
            self._cards.append(card)

    def insert_top(self, row):
        card = self._make_card(row)
        self.v.insertWidget(0, card)
        self._cards.insert(0, card)
        if len(self._cards) > self._limit:
            self._cards.pop().deleteLater()

class SettingsPage(QWidget):
    def __init__(self, get_cb, save_cb, test_send_cb, reconnect_cb):
        super().__init__()
        self.setObjectName("settings_page")
        self._get = get_cb
        self._save = save_cb
        self._test_send = test_send_cb
        self._reconnect = reconnect_cb
        
        s = self._get()
        self.lang = getattr(s, "language", "简体中文")
        
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.addWidget(TitleLabel(get_text(self.lang, "settings")))
        
        self.scroll = ScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        
        self.container = QWidget()
        lay = QVBoxLayout(self.container)
        
        def make_row(label, w):
            r = QHBoxLayout()
            r.addWidget(BodyLabel(label), 0)
            r.addWidget(w, 1)
            return r
        
        # 1. 语言设置
        card_l = CardWidget()
        l_l = QVBoxLayout(card_l)
        self.cb_lang = ComboBox()
        self.cb_lang.addItems(["简体中文", "English"])
        l_l.addLayout(make_row(get_text(self.lang, "lang_choice"), self.cb_lang))
        lay.addWidget(card_l)

        # 2. Gotify 配置
        card_g = CardWidget()
        l_g = QVBoxLayout(card_g)
        l_g.addWidget(SubtitleLabel("Gotify Config"))
        self.ed_url = LineEdit()
        self.ed_recv = LineEdit()
        self.ed_recv.setEchoMode(QLineEdit.Password)
        self.ed_send = LineEdit()
        self.ed_send.setEchoMode(QLineEdit.Password)
        l_g.addLayout(make_row("Server URL:", self.ed_url))
        l_g.addLayout(make_row("Receive Token:", self.ed_recv))
        l_g.addLayout(make_row("Send Token:", self.ed_send))
        lay.addWidget(card_g)

        # 3. 插件转发与同步频率
        card_p = CardWidget()
        l_p = QVBoxLayout(card_p)
        l_p.addWidget(SubtitleLabel(get_text(self.lang, "fwd_plugins")))
        
        self.sw_fwd_rss = SwitchButton(get_text(self.lang, "fwd_rss"))
        self.sw_fwd_imap = SwitchButton(get_text(self.lang, "fwd_imap"))
        self.sw_fwd_web3 = SwitchButton(get_text(self.lang, "fwd_web3"))
        l_p.addWidget(self.sw_fwd_rss)
        l_p.addWidget(self.sw_fwd_imap)
        l_p.addWidget(self.sw_fwd_web3)
        
        self.sp_poll_rss = QSpinBox()
        self.sp_poll_rss.setRange(1, 1440)
        self.sp_poll_rss.setSuffix(" min")
        
        self.sp_poll_imap = QSpinBox()
        self.sp_poll_imap.setRange(1, 1440)
        self.sp_poll_imap.setSuffix(" min")
        
        self.sp_poll_web3 = QSpinBox()
        self.sp_poll_web3.setRange(1, 1440)
        self.sp_poll_web3.setSuffix(" min")
        
        l_p.addLayout(make_row(get_text(self.lang, "poll_time") + " RSS", self.sp_poll_rss))
        l_p.addLayout(make_row(get_text(self.lang, "poll_time") + " IMAP", self.sp_poll_imap))
        l_p.addLayout(make_row(get_text(self.lang, "poll_time") + " Web3", self.sp_poll_web3))
        lay.addWidget(card_p)

        # 4. 过滤设置
        card_f = CardWidget()
        l_f = QVBoxLayout(card_f)
        l_f.addWidget(SubtitleLabel(get_text(self.lang, "filter_title")))
        self.cb_filter = ComboBox()
        self.cb_filter.addItems([
            get_text(self.lang, "filter_none"), 
            get_text(self.lang, "filter_black"), 
            get_text(self.lang, "filter_white")
        ])
        self.ed_keywords = LineEdit()
        l_f.addLayout(make_row(get_text(self.lang, "filter_mode"), self.cb_filter))
        l_f.addLayout(make_row(get_text(self.lang, "filter_kw"), self.ed_keywords))
        lay.addWidget(card_f)

        # 5. 底部按钮
        btns = QHBoxLayout()
        self.btn_save = PushButton(get_text(self.lang, "save_all"))
        self.btn_save.clicked.connect(self._on_save)
        self.btn_test = PushButton(get_text(self.lang, "test_push"))
        self.btn_test.clicked.connect(self._on_test)
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_test)
        btns.addStretch(1)
        lay.addLayout(btns)
        
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)
        self.load_to_ui()

    def load_to_ui(self):
        s = self._get()
        l_list = ["简体中文", "English"]
        
        if s.language in l_list:
            self.cb_lang.setCurrentIndex(l_list.index(s.language))
        else:
            self.cb_lang.setCurrentIndex(0)
            
        self.ed_url.setText(s.gotify_url)
        self.ed_recv.setText(s.gotify_recv_token)
        self.ed_send.setText(s.gotify_send_token)
        
        self.sw_fwd_rss.setChecked(getattr(s, "forward_rss", False))
        self.sw_fwd_imap.setChecked(getattr(s, "forward_imap", False))
        self.sw_fwd_web3.setChecked(getattr(s, "forward_web3", False))
        
        self.sp_poll_rss.setValue(getattr(s, "plugin_rss_poll_mins", 10))
        self.sp_poll_imap.setValue(getattr(s, "plugin_imap_poll_mins", 5))
        self.sp_poll_web3.setValue(getattr(s, "plugin_web3_poll_mins", 3))
        
        self.cb_filter.setCurrentIndex(getattr(s, "filter_mode", 0))
        self.ed_keywords.setText(getattr(s, "filter_keywords", ""))

    def _on_save(self):
        s = self._get()
        s.language = self.cb_lang.currentText()
        s.gotify_url = self.ed_url.text().strip()
        s.gotify_recv_token = self.ed_recv.text().strip()
        s.gotify_send_token = self.ed_send.text().strip()
        
        s.forward_rss = self.sw_fwd_rss.isChecked()
        s.forward_imap = self.sw_fwd_imap.isChecked()
        s.forward_web3 = self.sw_fwd_web3.isChecked()
        
        s.plugin_rss_poll_mins = self.sp_poll_rss.value()
        s.plugin_imap_poll_mins = self.sp_poll_imap.value()
        s.plugin_web3_poll_mins = self.sp_poll_web3.value()
        
        s.filter_mode = self.cb_filter.currentIndex()
        s.filter_keywords = self.ed_keywords.text().strip()
        
        self._save(s)
        self._reconnect()
        InfoBar.success(
            get_text(self.lang, "save_success"), 
            get_text(self.lang, "save_hint"), 
            duration=2000, 
            parent=self
        )

    def _on_test(self):
        s = self._get()
        ok, err = self._test_send(s)
        if ok:
            InfoBar.success(
                get_text(self.lang, "save_success"), 
                "测试指令已发出，请留意手机或顶部的红色报错！", 
                parent=self
            )
        else:
            InfoBar.error("Error", err, parent=self)

class UiBridge(QObject):
    status = Signal(str)
    message = Signal(dict)
    refresh_request = Signal()
    forward_error = Signal(str)

class NekoHubWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self._settings = load_settings()
        self.lang = getattr(self._settings, "language", "简体中文")
        self.setWindowTitle(f"NekoHub - {self.lang}")
        self.resize(1150, 750)
        
        icon_path = os.path.join(sys._MEIPASS, "icon.ico") if hasattr(sys, '_MEIPASS') else os.path.join(os.path.abspath("."), "icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        
        self._last_id = int(get_meta("last_id") or "0")
        self.ai_manager = AiManager(self._settings)
        
        self.inbox = InboxPage(self.lang)
        self.rss_page = RssPage(self.get_settings, self.save_settings, self.lang)
        self.imap_page = ImapPage(self.get_settings, self.save_settings, self.lang)
        self.web3_page = Web3Page(self.get_settings, self.save_settings, self.lang)
        
        self.ai_manager.mount_plugins(self.rss_page, self.imap_page, self.web3_page)
        
        self.ai_chat_page = AiPage(self.ai_manager, self.get_settings, self.save_settings)
        self.ai_tasks_page = AiTasksPage(self.ai_manager, self.get_settings, self.save_settings)
        self.forward_page = ForwardPage(self.get_settings, self.save_settings)
        self.settings_page = SettingsPage(self.get_settings, self.save_settings, self.send_test, lambda: self._start_ws())
        
        self.addSubInterface(self.inbox, FluentIcon.MAIL, get_text(self.lang, "inbox"))
        self.addSubInterface(self.rss_page, FluentIcon.LINK, get_text(self.lang, "rss"))
        self.addSubInterface(self.imap_page, FluentIcon.FOLDER, get_text(self.lang, "imap"))
        self.addSubInterface(self.web3_page, FluentIcon.FINGERPRINT, get_text(self.lang, "web3"))
        self.addSubInterface(self.ai_chat_page, FluentIcon.CHAT, get_text(self.lang, "ai_chat"))
        self.addSubInterface(self.ai_tasks_page, FluentIcon.CALENDAR, get_text(self.lang, "tasks"))
        self.addSubInterface(self.forward_page, FluentIcon.SEND, get_text(self.lang, "forward"))
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, get_text(self.lang, "settings"), NavigationItemPosition.BOTTOM)
        
        self.sound = SoundPlayer()
        self.toast_q = ToastQueue(max_visible=6, life_ms=self._settings.toast_duration)
        self.tray = TrayController(self, title="NekoHub", icon=QIcon(icon_path))
        
        self._refresh_coalescer = UiRefreshCoalescer(self._refresh_full_once, 200)
        self._bridge = UiBridge()
        self._bridge.status.connect(self.inbox.set_status)
        self._bridge.message.connect(self._ui_handle_message)
        self._bridge.refresh_request.connect(lambda: self._refresh_coalescer.request())
        
        self._bridge.forward_error.connect(lambda e: InfoBar.error("⚠️ 转发请求失败", e, duration=8000, parent=self))
        
        self.rss_page.new_item_signal.connect(self._handle_plugin_notification)
        self.imap_page.new_item_signal.connect(self._handle_plugin_notification)
        self.web3_page.new_item_signal.connect(self._handle_plugin_notification)
        
        self._ws = None
        self._refresh_full_once()
        self._initial_history_fetch_async()
        self._start_ws()

    def closeEvent(self, e):
        e.ignore()
        self.hide()

    def get_settings(self):
        return self._settings

    def save_settings(self, s):
        self._settings = s
        save_settings(s)
        self.ai_manager.update_settings(s)
        
        if hasattr(self, 'toast_q'):
            self.toast_q.life_ms = s.toast_duration
            
        if hasattr(self, 'rss_page'):
            self.rss_page.timer.setInterval(getattr(s, "plugin_rss_poll_mins", 10) * 60000)
        if hasattr(self, 'imap_page'):
            self.imap_page.timer.setInterval(getattr(s, "plugin_imap_poll_mins", 5) * 60000)
        if hasattr(self, 'web3_page'):
            self.web3_page.timer.setInterval(getattr(s, "plugin_web3_poll_mins", 3) * 60000)

    def _execute_external_forward(self, title: str, content: str, force=False):
        s = self._settings
        
        if not getattr(s, "forward_enabled", False) and not force:
            return

        # 1. 钉钉转发
        if getattr(s, "dingtalk_webhook", ""):
            try:
                url = s.dingtalk_webhook
                if getattr(s, "dingtalk_secret", ""):
                    timestamp = str(round(time.time() * 1000))
                    secret_enc = s.dingtalk_secret.encode('utf-8')
                    string_to_sign = f'{timestamp}\n{s.dingtalk_secret}'
                    string_to_sign_enc = string_to_sign.encode('utf-8')
                    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                    url += f"&timestamp={timestamp}&sign={sign}"
                
                payload = {
                    "msgtype": "text",
                    "text": {"content": f"【{title}】\n{content}"}
                }
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code != 200:
                    self._bridge.forward_error.emit(f"钉钉接口返回异常: {resp.text}")
            except Exception as e:
                self._bridge.forward_error.emit(f"钉钉转发崩溃: {str(e)}")

        # 2. Telegram 转发
        if getattr(s, "tg_bot_token", "") and getattr(s, "tg_chat_id", ""):
            try:
                tg_url = f"https://api.telegram.org/bot{s.tg_bot_token}/sendMessage"
                payload = {
                    "chat_id": s.tg_chat_id,
                    "text": f"*{title}*\n\n{content}",
                    "parse_mode": "Markdown"
                }
                
                resp = requests.post(tg_url, json=payload, timeout=15)
                
                if resp.status_code != 200:
                    self._bridge.forward_error.emit(f"Telegram 接口返回异常: {resp.text}")
            except Exception as e:
                self._bridge.forward_error.emit(f"TG 请求错误 (请确认系统梯子正常): {str(e)}")

        # 3. 邮件 SMTP 转发
        if getattr(s, "email_smtp", "") and getattr(s, "email_user", "") and getattr(s, "email_to", ""):
            try:
                msg = MIMEText(content, 'plain', 'utf-8')
                msg['Subject'] = f"[NekoHub Forward] {title}"
                msg['From'] = s.email_user
                msg['To'] = s.email_to
                
                server = smtplib.SMTP_SSL(s.email_smtp, 465, timeout=15)
                server.login(s.email_user, getattr(s, "email_pass", ""))
                server.sendmail(s.email_user, [s.email_to], msg.as_string())
                server.quit()
            except Exception as e:
                print(f"Email Forward Error: {e}")

    def send_test(self, s):
        try:
            if not s.gotify_url:
                return False, "Missing URL"
            send_message(s.gotify_url, s.gotify_send_token, "NekoHub Test", "Connected!")
            
            threading.Thread(
                target=self._execute_external_forward, 
                args=("NekoHub Forward Test", "If you see this, external forwarding is working!", True), 
                daemon=True
            ).start()
            
            return True, ""
        except Exception as e:
            return False, str(e)

    def _refresh_full_once(self):
        self.inbox.refresh_full(latest_messages(self.inbox.limit()))

    @Slot(dict)
    def _ui_handle_message(self, m: dict):
        upsert_messages([m])
        mid = int(m.get("id", 0))
        
        if mid > self._last_id:
            self._last_id = mid
            set_meta("last_id", str(mid))
            
            title = str(m.get("title") or "")
            msg = str(m.get("message") or "")
            s = self._settings
            should_alert = True
            
            if hasattr(s, 'filter_mode') and s.filter_mode != 0 and s.filter_keywords:
                keywords = [k.strip().lower() for k in s.filter_keywords.split(",") if k.strip()]
                content_lower = f"{title} {msg}".lower()
                hit = any(k in content_lower for k in keywords)
                
                if s.filter_mode == 1 and hit:
                    should_alert = False
                elif s.filter_mode == 2 and not hit:
                    should_alert = False
                    
            if should_alert:
                self.ai_manager.on_new_message(m)
                if getattr(s, "sound_enabled", True):
                    self.sound.play()
                self.toast_q.show(title if title else "Gotify", msg)
                
                # 【终极修复】精准判断是 AI 消息还是原始消息，从而按照设置模式放行
                if getattr(s, "forward_enabled", False):
                    f_mode = getattr(s, "forward_mode", 0)
                    is_ai_msg = "[AI任务完成]" in title
                    
                    do_forward = False
                    if f_mode == 0:
                        do_forward = True # 全部外转
                    elif f_mode == 1 and not is_ai_msg:
                        do_forward = True # 仅原始通知
                    elif f_mode == 2 and is_ai_msg:
                        do_forward = True # 仅转发 AI 结果
                        
                    if do_forward:
                        threading.Thread(target=self._execute_external_forward, args=(title if title else "Gotify", msg), daemon=True).start()
                
            self.inbox.add_unread(1)
            rows = latest_messages(1)
            if rows:
                self.inbox.insert_top(rows[0])

    @Slot(str, str, str)
    def _handle_plugin_notification(self, title, content, domain_type):
        s = self._settings
        if getattr(s, "sound_enabled", True):
            self.sound.play()
            
        self.toast_q.show(title, content)
        
        should_forward_gotify = (
            (domain_type == "rss" and getattr(s, "forward_rss", False)) or
            (domain_type == "imap" and getattr(s, "forward_imap", False)) or
            (domain_type == "web3" and getattr(s, "forward_web3", False))
        )
        
        if should_forward_gotify:
            if s.gotify_url and getattr(s, "gotify_send_token", None) and send_message:
                try:
                    send_message(s.gotify_url, s.gotify_send_token, f"[{domain_type.upper()}] {title}", content, priority=5)
                except Exception:
                    pass
            
            # Web3/RSS/IMAP 的推送也属于“原始通知”，受模式约束
            if getattr(s, "forward_enabled", False):
                f_mode = getattr(s, "forward_mode", 0)
                if f_mode in (0, 1): # 0: 全部, 1: 仅原始
                    threading.Thread(target=self._execute_external_forward, args=(f"[{domain_type.upper()}] {title}", content), daemon=True).start()

    def _initial_history_fetch_async(self):
        def _work():
            s = self._settings
            if not s.gotify_url or not s.gotify_recv_token:
                return
            try:
                msgs = fetch_latest(s.gotify_url, s.gotify_recv_token, limit=50)
                if msgs:
                    upsert_messages(msgs)
                    self._last_id = max([int(x.get("id", 0)) for x in msgs] + [self._last_id])
                    set_meta("last_id", str(self._last_id))
                self._bridge.refresh_request.emit()
            except:
                pass
        threading.Thread(target=_work, daemon=True).start()

    def _start_ws(self):
        if self._ws:
            self._ws.stop()
            
        s = self._settings
        if not s.gotify_url or not GotifyWSReceiver:
            self.inbox.set_status(get_text(self.lang, "ws_waiting"))
            return
            
        self._ws = GotifyWSReceiver(
            base_url=s.gotify_url, 
            recv_token=s.gotify_recv_token, 
            on_message=lambda mm: self._bridge.message.emit(mm), 
            on_status=lambda ss: self._bridge.status.emit(ss)
        )
        self._ws.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    setTheme(Theme.LIGHT)
    w = NekoHubWindow()
    w.show()
    sys.exit(app.exec())