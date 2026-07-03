"""点击工作线程：在后台执行点击循环，避免阻塞界面。"""
import time
import random

from PyQt5.QtCore import QThread, pyqtSignal

import pyautogui

from .config import AppConfig
from . import vision

# 关闭 pyautogui 的移动缓动 & 失败保护延迟，让点击更快更可控
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True  # 鼠标猛移到屏幕左上角可紧急停止


class ClickWorker(QThread):
    clicked = pyqtSignal(int, int)      # 每次点击后发出坐标
    status = pyqtSignal(str)            # 状态文本
    count_updated = pyqtSignal(int)     # 累计点击次数
    finished_run = pyqtSignal()         # 循环结束（区别于 QThread.finished）

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._cfg = config
        self._stop = False
        self._template = None

    def stop(self):
        self._stop = True

    def _do_click(self, x, y):
        button = self._cfg.click_button
        if self._cfg.click_type == "double":
            pyautogui.doubleClick(x=x, y=y, button=button)
        else:
            pyautogui.click(x=x, y=y, button=button)
        self.clicked.emit(int(x), int(y))

    def _next_target(self, index):
        """根据位置模式返回本次点击坐标；image 模式下返回 None 表示未找到。"""
        mode = self._cfg.position_mode
        if mode == "follow":
            return pyautogui.position()  # 当前鼠标位置
        if mode == "image":
            screen = vision.capture_screen()
            hit = vision.find_template(screen, self._template, self._cfg.match_threshold)
            if hit is None:
                return None
            return hit[0], hit[1]
        # fixed：多点则轮流
        pts = self._cfg.points
        if not pts:
            return pyautogui.position()
        return pts[index % len(pts)]

    def _sleep_ms(self, ms):
        """可被 stop 中断的睡眠。"""
        end = time.time() + ms / 1000.0
        while time.time() < end:
            if self._stop:
                return
            time.sleep(min(0.02, end - time.time()) if end - time.time() > 0 else 0)

    def run(self):
        cfg = self._cfg

        # image 模式先加载模板
        if cfg.position_mode == "image":
            self._template = vision.load_template(cfg.template_path)
            if self._template is None:
                self.status.emit("错误：无法加载模板图片")
                self.finished_run.emit()
                return

        # 启动延时
        if cfg.start_delay_sec > 0:
            self.status.emit(f"{cfg.start_delay_sec:.1f}s 后开始…")
            self._sleep_ms(int(cfg.start_delay_sec * 1000))

        count = 0
        start_time = time.time()
        self.status.emit("运行中")

        while not self._stop:
            # 停止条件
            if cfg.stop_condition == "max_clicks" and count >= cfg.max_clicks:
                break
            if cfg.stop_condition == "duration_sec" and (time.time() - start_time) >= cfg.duration_sec:
                break

            target = self._next_target(count)
            if target is None:
                # image 模式未找到目标，等待后重试
                self.status.emit("等待图像出现…")
                self._sleep_ms(cfg.poll_interval_ms)
                continue

            try:
                self._do_click(*target)
            except pyautogui.FailSafeException:
                self.status.emit("已触发紧急停止（鼠标移到左上角）")
                break

            count += 1
            self.count_updated.emit(count)
            self.status.emit("运行中")

            # 间隔 + 随机抖动
            interval = cfg.interval_ms
            if cfg.random_jitter_ms > 0:
                interval += random.randint(0, cfg.random_jitter_ms)
            self._sleep_ms(interval)

        self.status.emit("已停止")
        self.finished_run.emit()
