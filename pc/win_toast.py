# win_toast.py
from __future__ import annotations

class WinToast:
    """
    Reliable Windows toast via winotify.
    It auto-creates Start Menu shortcut + AppUserModelID.
    Works in dev script & packaged exe.
    """
    def __init__(self, app_id: str = "NekoHub", app_name: str = "NekoHub", icon_path: str | None = None):
        self.app_id = app_id
        self.app_name = app_name
        self.icon_path = icon_path

        from winotify import Notification, audio

        self._Notification = Notification
        self._audio = audio

    def notify(self, title: str, body: str):
        try:
            toast = self._Notification(
                app_id=self.app_id,     # AUMID
                title=title or "NekoHub",
                msg=body or "",
                icon=self.icon_path,    # can be None
            )
            # 不想要声音就注释下一行
            toast.set_audio(self._audio.Default, loop=False)
            toast.show()
        except Exception:
            pass