# notify_fx.py
from __future__ import annotations

import winsound
from dataclasses import dataclass
from typing import List

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QGuiApplication, QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication

from qfluentwidgets import CardWidget, SubtitleLabel, BodyLabel


class SoundPlayer:
    """
    Windows 内置通知音。
    无需自定义 wav，保持轻量。
    """

    def __init__(self):
        self.enabled: bool = True

    def play(self):
        if not self.enabled:
            return
        try:
            # 使用标准的 Windows 消息提示音
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass


class ToastPopup(QWidget):
    """自定义右上角弹窗（支持 Markdown 渲染）。"""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)

        # 窗口属性：无边框、最顶层、工具窗口（不在任务栏显示）、点击不激活
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # 使用 Fluent 设计风格的卡片组件
        self.card = CardWidget(self)
        self.card.setBorderRadius(14)

        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        # 标题栏
        self.lbl_title = SubtitleLabel(title if title else "NekoHub")
        # 允许标题也支持简单的 Markdown（比如加粗）
        self.lbl_title.setTextFormat(Qt.MarkdownText) 
        lay.addWidget(self.lbl_title)

        # 消息正文
        self.lbl_msg = BodyLabel(message if message else "")
        self.lbl_msg.setWordWrap(True)
        # --- 核心优化：开启 Markdown 渲染，让 DeepSeek 的 **加粗** 生效 ---
        self.lbl_msg.setTextFormat(Qt.MarkdownText) 
        # 设置最大宽度，防止弹窗过长
        self.lbl_msg.setMinimumWidth(280)
        self.lbl_msg.setMaximumWidth(400)
        lay.addWidget(self.lbl_msg)

        root.addWidget(self.card)

        # 淡入淡出动画
        self._anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setDuration(250)

    def show_on_screen_top_right(self, screen_geo, margin: int = 18, y_offset: int = 18):
        """将弹窗定位到屏幕右上角"""
        self.adjustSize()
        w = self.width()
        x = screen_geo.x() + screen_geo.width() - margin - w
        y = screen_geo.y() + y_offset
        self.move(x, y)

    def fade_in(self):
        """触发淡入显示"""
        try:
            self.setWindowOpacity(0.0)
            self.show()
            self.raise_()
            self._anim.stop()
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        except Exception:
            self.show()
            self.raise_()


@dataclass
class _ToastItem:
    popup: ToastPopup
    y_offset: int


class ToastQueue:
    """
    弹窗队列管理（支持多显示器）。
    负责弹窗的堆叠、自动消失和重排。
    """

    def __init__(
        self,
        max_visible: int = 6,
        life_ms: int = 5000,  # 默认 5 秒
        margin: int = 18,
        gap: int = 12,
        top_margin: int = 18,
    ):
        self.max_visible = int(max_visible)
        self.life_ms = int(life_ms) # 该值会被 ui_app.py 动态修改
        self.margin = int(margin)
        self.gap = int(gap)
        self.top_margin = int(top_margin)

        self._items: List[_ToastItem] = []

    def _screen_geo(self):
        """获取当前鼠标所在屏幕的可用区域"""
        try:
            pos = QCursor.pos()
            scr = QGuiApplication.screenAt(pos)
            if scr:
                return scr.availableGeometry()
        except Exception:
            pass

        # 回退到主显示器
        scr = QApplication.primaryScreen()
        return scr.availableGeometry() if scr else None

    def show(self, title: str, message: str):
        """显示一条新的通知"""
        geo = self._screen_geo()
        if not geo:
            return

        # 如果超过最大显示数量，移除最早的一条
        while len(self._items) >= self.max_visible:
            it = self._items.pop(0)
            try:
                it.popup.close()
            except Exception:
                pass

        # 创建并显示弹窗
        pop = ToastPopup(title, message)
        pop.fade_in()

        self._items.append(_ToastItem(popup=pop, y_offset=0))
        self._reflow()

        # 按照当前设定的时长计时消失
        # QTimer.singleShot 必须在 UI 线程运行
        QTimer.singleShot(self.life_ms, lambda: self._dismiss(pop))

    def _dismiss(self, popup: ToastPopup):
        """移除指定的弹窗并重排剩余弹窗"""
        idx = -1
        for i, it in enumerate(self._items):
            if it.popup == popup:
                idx = i
                break

        try:
            popup.close()
        except Exception:
            pass

        if idx >= 0:
            self._items.pop(idx)
            self._reflow()

    def _reflow(self):
        """垂直排列所有当前显示的弹窗"""
        geo = self._screen_geo()
        if not geo:
            return

        y = geo.y() + self.top_margin
        for it in self._items:
            try:
                # 重新计算位置，实现平滑堆叠
                it.popup.show_on_screen_top_right(geo, margin=self.margin, y_offset=y - geo.y())
                it.popup.raise_()
                it.popup.adjustSize()
                y += it.popup.height() + self.gap
            except Exception:
                pass