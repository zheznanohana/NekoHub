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
    Windows built-in notification sound.
    No custom wav, no config complexity.
    """

    def __init__(self):
        self.enabled: bool = True

    def play(self):
        if not self.enabled:
            return
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass


class ToastPopup(QWidget):
    """Custom top-right popup (NOT Windows native notification)."""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)

        # Tool + Frameless + StayOnTop: reliable overlay
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

        card = CardWidget(self)
        card.setBorderRadius(14)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        self.lbl_title = SubtitleLabel(title if title else "NekoHub")
        lay.addWidget(self.lbl_title)

        self.lbl_msg = BodyLabel(message if message else "")
        self.lbl_msg.setWordWrap(True)
        lay.addWidget(self.lbl_msg)

        root.addWidget(card)

        # fade animation
        self._anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setDuration(220)

    def show_on_screen_top_right(self, screen_geo, margin: int = 18, y_offset: int = 18):
        """Position to screen top-right (availableGeometry)"""
        self.adjustSize()
        w = self.width()
        x = screen_geo.x() + screen_geo.width() - margin - w
        y = screen_geo.y() + y_offset
        self.move(x, y)

    def fade_in(self):
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
    Stack multiple toast popups on the cursor screen (dual-monitor safe).
    Auto dismiss, reflow on removal.
    """

    def __init__(
        self,
        max_visible: int = 6,
        life_ms: int = 3200,
        margin: int = 18,
        gap: int = 12,
        top_margin: int = 18,
    ):
        self.max_visible = int(max_visible)
        self.life_ms = int(life_ms)
        self.margin = int(margin)
        self.gap = int(gap)
        self.top_margin = int(top_margin)

        self._items: List[_ToastItem] = []

    def _screen_geo(self):
        # Prefer screen at current cursor position
        try:
            pos = QCursor.pos()
            scr = QGuiApplication.screenAt(pos)
            if scr:
                return scr.availableGeometry()
        except Exception:
            pass

        # fallback: primary
        scr = QApplication.primaryScreen()
        return scr.availableGeometry() if scr else None

    def show(self, title: str, message: str):
        geo = self._screen_geo()
        if not geo:
            return

        # trim oldest first
        while len(self._items) >= self.max_visible:
            it = self._items.pop(0)
            try:
                it.popup.close()
            except Exception:
                pass

        pop = ToastPopup(title, message)
        pop.fade_in()

        self._items.append(_ToastItem(popup=pop, y_offset=0))
        self._reflow()

        # IMPORTANT: QTimer.singleShot must run in main thread.
        # Caller should ensure ToastQueue.show() is called in UI thread.
        QTimer.singleShot(self.life_ms, lambda: self._dismiss(pop))

    def _dismiss(self, popup: ToastPopup):
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
        geo = self._screen_geo()
        if not geo:
            return

        y = geo.y() + self.top_margin
        for it in self._items:
            try:
                it.popup.show_on_screen_top_right(geo, margin=self.margin, y_offset=y - geo.y())
                it.popup.raise_()
                it.popup.adjustSize()
                y += it.popup.height() + self.gap
            except Exception:
                pass