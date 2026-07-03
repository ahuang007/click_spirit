"""主窗口：所有设置项 + 启停控制。"""
import os

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QRadioButton,
    QButtonGroup, QLineEdit, QFileDialog, QListWidget, QSlider, QStatusBar,
    QMessageBox,
)

import pyautogui

from app.config import AppConfig
from app.worker import ClickWorker
from app.hotkey import GlobalHotkey

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# 界面上显示的热键 -> pynput 格式
HOTKEY_MAP = {
    "F6": "<f6>", "F7": "<f7>", "F8": "<f8>",
    "F9": "<f9>", "F10": "<f10>", "F12": "<f12>",
}
HOTKEY_REVERSE = {v: k for k, v in HOTKEY_MAP.items()}


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("按键精灵 · 自动点击器")
        self.setMinimumWidth(440)

        self.config = AppConfig.load(CONFIG_PATH)
        self.worker = None
        self.picking = False

        self._build_ui()
        self._apply_config_to_ui()

        # 全局热键
        self.hotkey = GlobalHotkey(self.config.start_hotkey)
        self.hotkey.triggered.connect(self.toggle_run)
        self.hotkey.start()

    # ---------------- UI 构建 ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # --- 点击设置 ---
        g_click = QGroupBox("点击设置")
        gl = QGridLayout(g_click)
        self.cmb_button = QComboBox(); self.cmb_button.addItems(["左键", "右键"])
        self.cmb_type = QComboBox(); self.cmb_type.addItems(["单击", "双击"])
        self.spin_interval = QSpinBox(); self.spin_interval.setRange(1, 600000); self.spin_interval.setSuffix(" ms")
        self.spin_jitter = QSpinBox(); self.spin_jitter.setRange(0, 60000); self.spin_jitter.setSuffix(" ms")
        gl.addWidget(QLabel("按键"), 0, 0); gl.addWidget(self.cmb_button, 0, 1)
        gl.addWidget(QLabel("方式"), 0, 2); gl.addWidget(self.cmb_type, 0, 3)
        gl.addWidget(QLabel("间隔"), 1, 0); gl.addWidget(self.spin_interval, 1, 1)
        gl.addWidget(QLabel("随机抖动"), 1, 2); gl.addWidget(self.spin_jitter, 1, 3)
        root.addWidget(g_click)

        # --- 点击位置 ---
        g_pos = QGroupBox("点击位置")
        pl = QVBoxLayout(g_pos)
        mode_row = QHBoxLayout()
        self.rb_fixed = QRadioButton("固定坐标")
        self.rb_follow = QRadioButton("跟随鼠标")
        self.rb_image = QRadioButton("图像识别")
        self.pos_group = QButtonGroup(self)
        for i, rb in enumerate((self.rb_fixed, self.rb_follow, self.rb_image)):
            self.pos_group.addButton(rb, i); mode_row.addWidget(rb)
        pl.addLayout(mode_row)

        self.list_points = QListWidget(); self.list_points.setMaximumHeight(90)
        pl.addWidget(self.list_points)
        pt_btns = QHBoxLayout()
        self.btn_pick = QPushButton("拾取坐标(3秒后取光标)")
        self.btn_del_point = QPushButton("删除选中")
        self.btn_clear_points = QPushButton("清空")
        pt_btns.addWidget(self.btn_pick); pt_btns.addWidget(self.btn_del_point); pt_btns.addWidget(self.btn_clear_points)
        pl.addLayout(pt_btns)
        root.addWidget(g_pos)

        # --- 图像识别 ---
        g_img = QGroupBox("图像识别（图像模式生效）")
        il = QGridLayout(g_img)
        self.edit_template = QLineEdit(); self.edit_template.setReadOnly(True)
        self.btn_browse = QPushButton("选择模板…")
        self.slider_thr = QSlider(Qt.Horizontal); self.slider_thr.setRange(50, 99)
        self.lbl_thr = QLabel("0.85")
        self.spin_poll = QSpinBox(); self.spin_poll.setRange(50, 10000); self.spin_poll.setSuffix(" ms")
        il.addWidget(QLabel("模板"), 0, 0); il.addWidget(self.edit_template, 0, 1); il.addWidget(self.btn_browse, 0, 2)
        il.addWidget(QLabel("置信度"), 1, 0); il.addWidget(self.slider_thr, 1, 1); il.addWidget(self.lbl_thr, 1, 2)
        il.addWidget(QLabel("轮询间隔"), 2, 0); il.addWidget(self.spin_poll, 2, 1)
        root.addWidget(g_img)

        # --- 触发 / 停止 ---
        g_trig = QGroupBox("触发 / 停止条件")
        tl = QGridLayout(g_trig)
        self.cmb_hotkey = QComboBox(); self.cmb_hotkey.addItems(list(HOTKEY_MAP.keys()))
        self.spin_delay = QDoubleSpinBox(); self.spin_delay.setRange(0, 3600); self.spin_delay.setSuffix(" s")
        self.cmb_stop = QComboBox(); self.cmb_stop.addItems(["无限（手动/热键停止）", "达到次数", "达到时长"])
        self.spin_maxclicks = QSpinBox(); self.spin_maxclicks.setRange(1, 10_000_000)
        self.spin_duration = QDoubleSpinBox(); self.spin_duration.setRange(0.1, 86400); self.spin_duration.setSuffix(" s")
        tl.addWidget(QLabel("启动热键"), 0, 0); tl.addWidget(self.cmb_hotkey, 0, 1)
        tl.addWidget(QLabel("启动延时"), 0, 2); tl.addWidget(self.spin_delay, 0, 3)
        tl.addWidget(QLabel("停止条件"), 1, 0); tl.addWidget(self.cmb_stop, 1, 1)
        tl.addWidget(QLabel("次数"), 2, 0); tl.addWidget(self.spin_maxclicks, 2, 1)
        tl.addWidget(QLabel("时长"), 2, 2); tl.addWidget(self.spin_duration, 2, 3)
        root.addWidget(g_trig)

        # --- 控制区 ---
        ctrl = QHBoxLayout()
        self.btn_start = QPushButton("开始")
        self.btn_start.setStyleSheet("font-weight:bold;padding:6px;")
        self.lbl_count = QLabel("点击次数: 0")
        ctrl.addWidget(self.btn_start); ctrl.addStretch(); ctrl.addWidget(self.lbl_count)
        root.addLayout(ctrl)

        self.status = QStatusBar()
        self.status.showMessage("就绪")
        root.addWidget(self.status)

        # --- 信号连接 ---
        self.btn_start.clicked.connect(self.toggle_run)
        self.btn_pick.clicked.connect(self.pick_point)
        self.btn_del_point.clicked.connect(self.delete_point)
        self.btn_clear_points.clicked.connect(self.list_points.clear)
        self.btn_browse.clicked.connect(self.browse_template)
        self.slider_thr.valueChanged.connect(lambda v: self.lbl_thr.setText(f"{v/100:.2f}"))
        self.cmb_hotkey.currentTextChanged.connect(self.change_hotkey)
        self.pos_group.buttonClicked.connect(self._update_enabled)
        self.cmb_stop.currentIndexChanged.connect(self._update_enabled)

    # ---------------- 配置 <-> UI ----------------
    def _apply_config_to_ui(self):
        c = self.config
        self.cmb_button.setCurrentIndex(0 if c.click_button == "left" else 1)
        self.cmb_type.setCurrentIndex(0 if c.click_type == "single" else 1)
        self.spin_interval.setValue(c.interval_ms)
        self.spin_jitter.setValue(c.random_jitter_ms)

        {"fixed": self.rb_fixed, "follow": self.rb_follow, "image": self.rb_image}\
            .get(c.position_mode, self.rb_fixed).setChecked(True)
        for p in c.points:
            self.list_points.addItem(f"{p[0]}, {p[1]}")

        self.edit_template.setText(c.template_path)
        self.slider_thr.setValue(int(c.match_threshold * 100))
        self.lbl_thr.setText(f"{c.match_threshold:.2f}")
        self.spin_poll.setValue(c.poll_interval_ms)

        self.cmb_hotkey.setCurrentText(HOTKEY_REVERSE.get(c.start_hotkey, "F6"))
        self.spin_delay.setValue(c.start_delay_sec)
        self.cmb_stop.setCurrentIndex({"none": 0, "max_clicks": 1, "duration_sec": 2}.get(c.stop_condition, 0))
        self.spin_maxclicks.setValue(c.max_clicks)
        self.spin_duration.setValue(c.duration_sec)
        self._update_enabled()

    def _collect_config(self) -> AppConfig:
        c = self.config
        c.click_button = "left" if self.cmb_button.currentIndex() == 0 else "right"
        c.click_type = "single" if self.cmb_type.currentIndex() == 0 else "double"
        c.interval_ms = self.spin_interval.value()
        c.random_jitter_ms = self.spin_jitter.value()

        c.position_mode = {0: "fixed", 1: "follow", 2: "image"}[self.pos_group.checkedId()]
        c.points = []
        for i in range(self.list_points.count()):
            x, y = self.list_points.item(i).text().split(",")
            c.points.append((int(x.strip()), int(y.strip())))

        c.template_path = self.edit_template.text()
        c.match_threshold = self.slider_thr.value() / 100
        c.poll_interval_ms = self.spin_poll.value()

        c.start_hotkey = HOTKEY_MAP[self.cmb_hotkey.currentText()]
        c.start_delay_sec = self.spin_delay.value()
        c.stop_condition = {0: "none", 1: "max_clicks", 2: "duration_sec"}[self.cmb_stop.currentIndex()]
        c.max_clicks = self.spin_maxclicks.value()
        c.duration_sec = self.spin_duration.value()
        return c

    def _update_enabled(self, *_):
        is_fixed = self.rb_fixed.isChecked()
        is_image = self.rb_image.isChecked()
        for w in (self.list_points, self.btn_pick, self.btn_del_point, self.btn_clear_points):
            w.setEnabled(is_fixed)
        for w in (self.edit_template, self.btn_browse, self.slider_thr, self.spin_poll):
            w.setEnabled(is_image)
        stop_idx = self.cmb_stop.currentIndex()
        self.spin_maxclicks.setEnabled(stop_idx == 1)
        self.spin_duration.setEnabled(stop_idx == 2)

    # ---------------- 交互动作 ----------------
    def pick_point(self):
        """3 秒后读取当前光标位置并加入列表，方便用户移动到目标处。"""
        self.btn_pick.setEnabled(False)
        self._pick_remaining = 3
        self.status.showMessage("3 秒后拾取光标位置…")
        self._pick_timer = QTimer(self)
        self._pick_timer.timeout.connect(self._pick_tick)
        self._pick_timer.start(1000)

    def _pick_tick(self):
        self._pick_remaining -= 1
        if self._pick_remaining > 0:
            self.status.showMessage(f"{self._pick_remaining} 秒后拾取光标位置…")
            return
        self._pick_timer.stop()
        x, y = pyautogui.position()
        self.list_points.addItem(f"{x}, {y}")
        self.status.showMessage(f"已添加坐标 ({x}, {y})")
        self.btn_pick.setEnabled(True)

    def delete_point(self):
        row = self.list_points.currentRow()
        if row >= 0:
            self.list_points.takeItem(row)

    def browse_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择模板图片", "", "图片 (*.png *.jpg *.bmp)")
        if path:
            self.edit_template.setText(path)

    def change_hotkey(self, text):
        self.hotkey.set_hotkey(HOTKEY_MAP[text])
        self.status.showMessage(f"启动热键已设为 {text}")

    # ---------------- 运行控制 ----------------
    def toggle_run(self):
        if self.worker and self.worker.isRunning():
            self.stop_run()
        else:
            self.start_run()

    def start_run(self):
        cfg = self._collect_config()
        if cfg.position_mode == "fixed" and not cfg.points:
            QMessageBox.warning(self, "提示", "固定坐标模式请先拾取至少一个坐标。")
            return
        if cfg.position_mode == "image" and not os.path.exists(cfg.template_path):
            QMessageBox.warning(self, "提示", "图像模式请先选择有效的模板图片。")
            return

        cfg.save(CONFIG_PATH)
        self.lbl_count.setText("点击次数: 0")
        self.worker = ClickWorker(cfg)
        self.worker.count_updated.connect(lambda n: self.lbl_count.setText(f"点击次数: {n}"))
        self.worker.status.connect(self.status.showMessage)
        self.worker.finished_run.connect(self._on_finished)
        self.worker.start()
        self.btn_start.setText("停止")

    def stop_run(self):
        if self.worker:
            self.worker.stop()

    def _on_finished(self):
        self.btn_start.setText("开始")

    def closeEvent(self, event):
        self.stop_run()
        if self.worker:
            self.worker.wait(2000)
        self.hotkey.stop()
        self._collect_config().save(CONFIG_PATH)
        event.accept()
