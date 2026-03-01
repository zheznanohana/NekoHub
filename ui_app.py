# ui_app.py
from __future__ import annotations

import sys
import os
import threading
from dataclasses import asdict
from typing import List, Tuple, Optional

from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QLineEdit,
    QSpinBox,
    QStyle,
    QSystemTrayIcon,
    QMenu,
)

from qfluentwidgets import (
    FluentWindow,
    NavigationItemPosition,
    FluentIcon,
    TitleLabel,
    SubtitleLabel,
    BodyLabel,
    CardWidget,
    PushButton,
    LineEdit,
    setTheme,
    Theme,
    SwitchButton,
    ComboBox,
    InfoBar,
    InfoBarPosition,
    StrongBodyLabel,
    ScrollArea
)

# 导入业务模块
from settings import Settings, load_settings, save_settings
from notify_fx import SoundPlayer, ToastQueue
from ai_core import AiManager
from ui_ai import AiPage
from ui_tasks import AiTasksPage
from ui_forward import ForwardPage 

# ---------------------------
# 多语言翻译字典
# ---------------------------
LANG_MAP = {
    "简体中文": {
        "inbox": "收件箱",
        "ai_chat": "AI 助手",
        "tasks": "自动化任务",
        "forward": "通知转发",
        "settings": "系统设置",
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
        "filter_kw": "关键字 (多个请用英文逗号 , 分隔):"
    },
    "English": {
        "inbox": "Inbox",
        "ai_chat": "AI Assistant",
        "tasks": "Tasks Center",
        "forward": "Forwarding",
        "settings": "Settings",
        "ws_status": "WS: ",
        "ws_ready": "Ready",
        "ws_waiting": "Waiting for config",
        "clear_unread": "Mark Read",
        "new_msg": " ● New Messages",
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
        "filter_kw": "Keywords (comma separated):"
    }
}

def get_text(lang: str, key: str) -> str:
    data = LANG_MAP.get(lang, LANG_MAP["简体中文"])
    return data.get(key, key)

# --- 存储兜底逻辑 ---
try:
    from storage import init_db, upsert_messages, latest_messages, get_meta, set_meta
except Exception:
    init_db = lambda: None
    _MEM_DB: List[Tuple[int, int, str, str, int, str]] = []
    _META = {"last_id": "0"}
    def upsert_messages(msgs):
        for m in msgs:
            mid = int(m.get("id", 0))
            if any(r[0] == mid for r in _MEM_DB): continue
            _MEM_DB.append((mid, int(m.get("appid", 0)), str(m.get("title") or ""), str(m.get("message") or ""), int(m.get("priority", 0)), str(m.get("date") or "")))
        _MEM_DB.sort(key=lambda x: x[0], reverse=True)
    def latest_messages(limit): return _MEM_DB[: max(0, int(limit))]
    def get_meta(k): return _META.get(k)
    def set_meta(k, v): _META[k] = v

# --- Gotify 通信逻辑 ---
try:
    from gotify_client import fetch_latest, send_message
    from gotify_ws import GotifyWSReceiver
except Exception:
    fetch_latest = send_message = GotifyWSReceiver = None

# ---------------------------
# 刷新合并器
# ---------------------------
class UiRefreshCoalescer:
    def __init__(self, fn, interval_ms: int = 200):
        self._fn, self._timer = fn, QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fn)
        self._int = interval_ms
    def request(self):
        if not self._timer.isActive(): self._timer.start(self._int)

# ---------------------------
# 系统托盘
# ---------------------------
class TrayController:
    def __init__(self, window: QWidget, title: str = "NekoHub", icon: Optional[QIcon] = None):
        self.window = window
        self.tray = QSystemTrayIcon(window)
        self.tray.setToolTip(title)
        self.tray.setIcon(icon if icon and not icon.isNull() else QApplication.style().standardIcon(QStyle.SP_ComputerIcon))
        menu = QMenu()
        menu.addAction("Show").triggered.connect(self.restore)
        menu.addAction("Exit").triggered.connect(QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.restore() if r in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
        self.tray.show()
    def restore(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

# ---------------------------
# 收件箱 (Fluent 滚动条 + 翻译)
# ---------------------------
class InboxPage(QWidget):
    def __init__(self, lang):
        super().__init__()
        self.setObjectName("inbox_page")
        self.lang = lang
        self._limit = 100  
        self._unread = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(10)

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
        self.v.setSpacing(12)
        self.v.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)
        self._cards: List[CardWidget] = []

    def set_status(self, s: str): self.lbl_status.setText(get_text(self.lang, "ws_status") + s)
    def limit(self) -> int: return self._limit
    def add_unread(self, n: int = 1):
        self._unread += n; self._sync_unread()
    def clear_unread(self):
        self._unread = 0; self._sync_unread()
    def _sync_unread(self):
        if self._unread <= 0: self.lbl_unread.hide()
        else: self.lbl_unread.setText(f"● {self._unread}"); self.lbl_unread.show()

    def _make_card(self, row: Tuple) -> CardWidget:
        card = CardWidget(); lay = QVBoxLayout(card); lay.setContentsMargins(16, 14, 16, 14)
        head = QHBoxLayout(); head.addWidget(SubtitleLabel(str(row[2]) if row[2] else "Gotify"), 0)
        head.addStretch(1); meta = BodyLabel(f"#{row[0]}")
        meta.setStyleSheet("opacity:0.4; font-size:10px;"); head.addWidget(meta); lay.addLayout(head)
        body = BodyLabel(str(row[3]) or ""); body.setWordWrap(True); body.setTextFormat(Qt.MarkdownText) 
        lay.addWidget(body)
        if row[5]:
            dt = BodyLabel(str(row[5])); dt.setStyleSheet("opacity:0.4; font-size:9px;"); lay.addWidget(dt)
        return card

    def refresh_full(self, rows: List[Tuple]):
        while self.v.count():
            w = self.v.takeAt(0).widget()
            if w: w.deleteLater()
        self._cards.clear()
        for r in rows:
            card = self._make_card(r); self.v.addWidget(card); self._cards.append(card)

    def insert_top(self, row: Tuple):
        card = self._make_card(row); self.v.insertWidget(0, card); self._cards.insert(0, card)
        if len(self._cards) > self._limit:
            last = self._cards.pop(); last.deleteLater()

# ---------------------------
# 设置页面 (黑白名单过滤 UI)
# ---------------------------
class SettingsPage(QWidget):
    def __init__(self, get_cb, save_cb, test_send_cb, reconnect_cb):
        super().__init__()
        self.setObjectName("settings_page")
        self._get, self._save = get_cb, save_cb
        self._test_send, self._reconnect = test_send_cb, reconnect_cb
        
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
        lay.setSpacing(15)
        lay.setAlignment(Qt.AlignTop)

        def make_row(label: str, w: QWidget):
            r = QHBoxLayout()
            r.addWidget(BodyLabel(label), 0)
            r.addWidget(w, 1)
            return r

        # 1. 常规
        card_l = CardWidget(); l_l = QVBoxLayout(card_l)
        self.cb_lang = ComboBox(); self.cb_lang.addItems(["简体中文", "English"])
        l_l.addLayout(make_row(get_text(self.lang, "lang_choice"), self.cb_lang))
        lay.addWidget(card_l)

        # 2. Gotify
        card_g = CardWidget(); l_g = QVBoxLayout(card_g); l_g.addWidget(SubtitleLabel("Gotify Config"))
        self.ed_url = LineEdit(); self.ed_recv = LineEdit(); self.ed_recv.setEchoMode(QLineEdit.Password)
        self.ed_send = LineEdit(); self.ed_send.setEchoMode(QLineEdit.Password)
        l_g.addLayout(make_row("Server URL:", self.ed_url))
        l_g.addLayout(make_row("Receive Token:", self.ed_recv))
        l_g.addLayout(make_row("Send Token:", self.ed_send))
        lay.addWidget(card_g)

        # 3. 过滤设置
        card_f = CardWidget(); l_f = QVBoxLayout(card_f)
        l_f.addWidget(SubtitleLabel(get_text(self.lang, "filter_title")))
        self.cb_filter = ComboBox()
        self.cb_filter.addItems([
            get_text(self.lang, "filter_none"), 
            get_text(self.lang, "filter_black"), 
            get_text(self.lang, "filter_white")
        ])
        self.ed_keywords = LineEdit()
        self.ed_keywords.setPlaceholderText("e.g. 广告,测试,error")
        l_f.addLayout(make_row(get_text(self.lang, "filter_mode"), self.cb_filter))
        l_f.addLayout(make_row(get_text(self.lang, "filter_kw"), self.ed_keywords))
        lay.addWidget(card_f)

        # 4. 通知
        card_n = CardWidget(); l_n = QVBoxLayout(card_n); l_n.addWidget(SubtitleLabel("Notification"))
        self.sp_toast = QSpinBox(); self.sp_toast.setRange(1000, 120000); self.sp_toast.setSingleStep(1000); self.sp_toast.setSuffix(" ms")
        self.sp_poll = QSpinBox(); self.sp_poll.setRange(2, 3600); self.sp_poll.setSuffix(" s")
        self.sw_sound = SwitchButton(get_text(self.lang, "sound_enable"))
        l_n.addLayout(make_row(get_text(self.lang, "toast_time"), self.sp_toast))
        l_n.addLayout(make_row(get_text(self.lang, "poll_time"), self.sp_poll))
        l_n.addWidget(self.sw_sound)
        lay.addWidget(card_n)

        btns = QHBoxLayout()
        self.btn_save = PushButton(get_text(self.lang, "save_all"))
        self.btn_save.clicked.connect(self._on_save)
        self.btn_test = PushButton(get_text(self.lang, "test_push"))
        self.btn_test.clicked.connect(self._on_test)
        btns.addWidget(self.btn_save); btns.addWidget(self.btn_test); btns.addStretch(1)
        lay.addLayout(btns)

        self.scroll.setWidget(self.container); root.addWidget(self.scroll); self.load_to_ui()

    def load_to_ui(self):
        s = self._get()
        l_list = ["简体中文", "English"]
        self.cb_lang.setCurrentIndex(l_list.index(s.language) if s.language in l_list else 0)
        self.ed_url.setText(s.gotify_url); self.ed_recv.setText(s.gotify_recv_token); self.ed_send.setText(s.gotify_send_token)
        self.cb_filter.setCurrentIndex(getattr(s, "filter_mode", 0))
        self.ed_keywords.setText(getattr(s, "filter_keywords", ""))
        self.sp_toast.setValue(int(getattr(s, "toast_duration", 5000)))
        self.sp_poll.setValue(int(getattr(s, "poll_seconds", 2)))
        self.sw_sound.setChecked(bool(getattr(s, "sound_enabled", True)))

    def _on_save(self):
        s = self._get()
        s.language = self.cb_lang.currentText()
        s.gotify_url = self.ed_url.text().strip(); s.gotify_recv_token = self.ed_recv.text().strip(); s.gotify_send_token = self.ed_send.text().strip()
        s.filter_mode = self.cb_filter.currentIndex()
        s.filter_keywords = self.ed_keywords.text().strip()
        s.toast_duration = self.sp_toast.value(); s.poll_seconds = self.sp_poll.value()
        s.sound_enabled = self.sw_sound.isChecked()
        self._save(s)
        InfoBar.success(get_text(self.lang, "save_success"), get_text(self.lang, "save_hint"), duration=2000, parent=self)

    def _on_test(self):
        ok, err = self._test_send(self._get())
        if ok: InfoBar.success(get_text(self.lang, "save_success"), get_text(self.lang, "test_ok"), parent=self)
        else: InfoBar.error("Error", err, parent=self)

# ---------------------------
# 主窗口 (核心过滤逻辑 + 图标修复)
# ---------------------------
class UiBridge(QObject):
    status = Signal(str); message = Signal(dict); refresh_request = Signal()

class NekoHubWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self._settings = load_settings()
        self.lang = getattr(self._settings, "language", "简体中文")
        
        self.setWindowTitle(f"NekoHub - {self.lang}")
        self.resize(1150, 750)

        # --- 核心修复：PyInstaller 打包后的绝对路径寻址 ---
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "icon.ico")
        else:
            icon_path = os.path.join(os.path.abspath("."), "icon.ico")

        icon = QIcon(icon_path)
        if icon.isNull(): 
            icon = QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
        self.setWindowIcon(icon)
        # ------------------------------------------------

        self._last_id = int(get_meta("last_id") or "0")
        self.ai_manager = AiManager(self._settings)

        self.inbox = InboxPage(self.lang)
        self.ai_chat_page = AiPage(self.ai_manager, self.get_settings, self.save_settings)
        self.ai_tasks_page = AiTasksPage(self.ai_manager, self.get_settings, self.save_settings)
        self.forward_page = ForwardPage(self.get_settings, self.save_settings)
        self.settings_page = SettingsPage(self.get_settings, self.save_settings, self.send_test, lambda: self._start_ws())

        self.addSubInterface(self.inbox, FluentIcon.MAIL, get_text(self.lang, "inbox"))
        self.addSubInterface(self.ai_chat_page, FluentIcon.CHAT, get_text(self.lang, "ai_chat"))
        self.addSubInterface(self.ai_tasks_page, FluentIcon.CALENDAR, get_text(self.lang, "tasks"))
        self.addSubInterface(self.forward_page, FluentIcon.SEND, get_text(self.lang, "forward"))
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, get_text(self.lang, "settings"), NavigationItemPosition.BOTTOM)

        self.sound = SoundPlayer()
        self.toast_q = ToastQueue(max_visible=6, life_ms=self._settings.toast_duration)
        self.tray = TrayController(self, title="NekoHub", icon=icon)

        self._refresh_coalescer = UiRefreshCoalescer(self._refresh_full_once, 200)
        self._bridge = UiBridge()
        self._bridge.status.connect(self.inbox.set_status)
        self._bridge.message.connect(self._ui_handle_message)
        self._bridge.refresh_request.connect(lambda: self._refresh_coalescer.request())

        self._ws = None
        self._refresh_full_once()
        self._initial_history_fetch_async()
        self._start_ws()

    def closeEvent(self, e): e.ignore(); self.hide()

    def get_settings(self): return self._settings
    def save_settings(self, s):
        self._settings = s; save_settings(s)
        self.ai_manager.update_settings(s)
        self.toast_q.life_ms = s.toast_duration
        self._start_ws()

    def send_test(self, s):
        try:
            if not s.gotify_url: return False, "Missing URL"
            send_message(s.gotify_url, s.gotify_send_token, "NekoHub Test", "Connected!")
            return True, ""
        except Exception as e: return False, str(e)

    def _refresh_full_once(self):
        self.inbox.refresh_full(latest_messages(self.inbox.limit()))

    @Slot(dict)
    def _ui_handle_message(self, m: dict):
        upsert_messages([m])
        mid = int(m.get("id", 0))
        if mid > self._last_id:
            self._last_id = mid; set_meta("last_id", str(mid))
            
            title = str(m.get("title") or "")
            msg = str(m.get("message") or "")
            
            # --- 黑白名单过滤逻辑 ---
            s = self._settings
            should_alert = True
            
            if hasattr(s, 'filter_mode') and s.filter_mode != 0 and s.filter_keywords:
                keywords = [k.strip().lower() for k in s.filter_keywords.split(",") if k.strip()]
                text_to_check = f"{title} {msg}".lower()
                hit = any(k in text_to_check for k in keywords)

                if s.filter_mode == 1: # 黑名单
                    if hit: should_alert = False
                elif s.filter_mode == 2: # 白名单
                    if not hit: should_alert = False

            if should_alert:
                self.ai_manager.on_new_message(m)
                self.sound.play()
                self.toast_q.show(title if title else "Gotify", msg)

            self.inbox.add_unread(1)
            rows = latest_messages(1)
            if rows: self.inbox.insert_top(rows[0])

    def _initial_history_fetch_async(self):
        def _work():
            s = self._settings
            if not s.gotify_url or not s.gotify_recv_token: return
            try:
                msgs = fetch_latest(s.gotify_url, s.gotify_recv_token, limit=50)
                if msgs:
                    upsert_messages(msgs)
                    mx = max([int(x.get("id", 0)) for x in msgs] + [self._last_id])
                    self._last_id = mx; set_meta("last_id", str(mx))
                self._bridge.refresh_request.emit()
            except: pass
        threading.Thread(target=_work, daemon=True).start()

    def _start_ws(self):
        if self._ws: self._ws.stop()
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
    w = NekoHubWindow(); w.show()
    sys.exit(app.exec())