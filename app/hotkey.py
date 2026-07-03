"""全局热键监听：即使程序不在前台也能启停。"""
from PyQt5.QtCore import QObject, pyqtSignal
from pynput import keyboard


class GlobalHotkey(QObject):
    """监听一个全局热键，触发时发出 triggered 信号（线程安全，经由 Qt 信号转发）。"""

    triggered = pyqtSignal()

    def __init__(self, hotkey: str = "<f6>", parent=None):
        super().__init__(parent)
        self._hotkey = hotkey
        self._listener = None

    def start(self):
        self.stop()
        try:
            self._listener = keyboard.GlobalHotKeys({
                self._hotkey: self._on_activate
            })
            self._listener.start()
        except Exception as e:
            print(f"热键注册失败: {e}")

    def stop(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def set_hotkey(self, hotkey: str):
        self._hotkey = hotkey
        if self._listener is not None:
            self.start()  # 重新注册

    def _on_activate(self):
        # pynput 在自己的线程回调；用 Qt 信号安全转发到主线程
        self.triggered.emit()
