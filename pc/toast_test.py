# toast_test.py
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from notify_fx import ToastQueue, SoundPlayer

def main():
    app = QApplication(sys.argv)

    w = QWidget()
    w.setWindowTitle("Toast Test")
    w.resize(420, 200)

    q = ToastQueue(max_visible=6, timeout_ms=6000)
    snd = SoundPlayer()

    lay = QVBoxLayout(w)

    def send_one():
        snd.play()
        q.show("NekoHub", "这是一条测试通知（多屏定位：鼠标所在屏幕右上角）")

    def send_many():
        for i in range(1, 8):
            q.show(f"NekoHub #{i}", f"测试队列第 {i} 条（应该叠加下滑）")

    b1 = QPushButton("Send One Toast")
    b1.clicked.connect(send_one)
    b2 = QPushButton("Send Many Toasts")
    b2.clicked.connect(send_many)

    lay.addWidget(b1)
    lay.addWidget(b2)

    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()