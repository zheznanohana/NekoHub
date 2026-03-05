# tray_manager.py
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, QEvent, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QWidget, QApplication, QStyle


class TrayManager(QObject):
    """
    Robust "minimize to tray" manager:
    - Close button -> hide to tray (ignore close)
    - Minimize button / taskbar minimize -> hide to tray
    - Tray click/doubleclick -> restore
    - Tray right-click -> Show / Exit
    """

    def __init__(
        self,
        window: QWidget,
        *,
        title: str = "NekoHub",
        icon_path: str = "icon.ico",
        on_exit: Optional[Callable[[], None]] = None,
        tip_on_first_hide: bool = True,
    ):
        super().__init__(window)
        self.window = window
        self.title = title
        self.icon_path = icon_path
        self.on_exit = on_exit
        self.tip_on_first_hide = tip_on_first_hide

        self._tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self._tray: Optional[QSystemTrayIcon] = None
        self._first_hide_done = False
        self._force_quit = False

        # create tray ASAP but after event loop starts (more stable with FluentWindow)
        QTimer.singleShot(0, self._install)

    # ---------------- public ----------------
    def tray_available(self) -> bool:
        return self._tray_available

    def hide_to_tray(self, reason: str = ""):
        if not self._tray_available or not self._tray:
            # tray not available: best effort minimize
            self.window.showMinimized()
            return

        self.window.hide()

        if self.tip_on_first_hide and not self._first_hide_done:
            self._first_hide_done = True
            self._safe_message(
                "Running in tray.\nRight-click tray icon to Exit.",
                1800,
            )
        elif reason:
            self._safe_message(reason, 1200)

    def restore(self):
        self.window.show()
        self.window.setWindowState(self.window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.window.raise_()
        self.window.activateWindow()

    def exit_app(self):
        self._force_quit = True
        try:
            if self.on_exit:
                self.on_exit()
        except Exception:
            pass

        try:
            if self._tray:
                self._tray.hide()
        except Exception:
            pass

        QApplication.quit()

    def handle_close_event(self, e):
        if self._force_quit or not self._tray_available:
            e.accept()
            return
        e.ignore()
        self.hide_to_tray("Minimized to tray.")

    # ---------------- internal ----------------
    def _safe_message(self, text: str, msec: int):
        try:
            if self._tray:
                self._tray.showMessage(self.title, text, QSystemTrayIcon.Information, msec)
        except Exception:
            pass

    def _pick_icon(self) -> QIcon:
        """
        Guarantee a non-null icon so tray is always visible.
        """
        # 1) explicit icon_path
        icon = QIcon(self.icon_path)
        if not icon.isNull():
            return icon

        # 2) window icon
        try:
            icon = self.window.windowIcon()
            if not icon.isNull():
                return icon
        except Exception:
            pass

        # 3) system fallback (guaranteed)
        try:
            return QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
        except Exception:
            return QIcon()

    def _install(self):
        if not self._tray_available:
            try:
                QMessageBox.warning(
                    self.window,
                    "Tray unavailable",
                    "System tray is not available.\nClose will exit the app.",
                )
            except Exception:
                pass
            return

        # avoid double install
        if self._tray is not None:
            return

        icon = self._pick_icon()

        self._tray = QSystemTrayIcon(icon, self.window)  # strong ref
        self._tray.setToolTip(self.title)

        menu = QMenu()
        act_show = QAction("Show", self.window)
        act_exit = QAction("Exit", self.window)
        act_show.triggered.connect(self.restore)
        act_exit.triggered.connect(self.exit_app)
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_exit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

        # catch minimize events reliably
        self.window.installEventFilter(self)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.restore()

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QEvent.WindowStateChange:
            if self.window.isMinimized() and not self._force_quit:
                QTimer.singleShot(0, lambda: self.hide_to_tray("Minimized to tray."))
                return True
        return super().eventFilter(obj, event)