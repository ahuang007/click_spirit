"""应用配置：数据类 + JSON 存取。"""
from dataclasses import dataclass, field, asdict
from typing import List, Tuple
import json
import os


@dataclass
class AppConfig:
    # ---- 点击设置 ----
    click_button: str = "left"          # left / right
    click_type: str = "single"          # single / double
    interval_ms: int = 100              # 两次点击间隔
    random_jitter_ms: int = 0           # 间隔随机抖动 (0~jitter)

    # ---- 点击位置 ----
    position_mode: str = "fixed"        # fixed / follow / image
    points: List[Tuple[int, int]] = field(default_factory=list)  # 固定坐标（可多点轮流）

    # ---- 图像识别 ----
    template_path: str = ""
    match_threshold: float = 0.85       # 0~1
    poll_interval_ms: int = 300         # 未匹配时的轮询间隔

    # ---- 触发 / 停止条件 ----
    start_hotkey: str = "<f6>"          # pynput 格式；F6 = toggle 启停
    start_delay_sec: float = 0.0        # 启动前延时
    stop_condition: str = "none"        # none / max_clicks / duration_sec
    max_clicks: int = 100
    duration_sec: float = 60.0

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "AppConfig":
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return cls()
        cfg = cls()
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        # points 从 JSON 读回来是 list[list]，统一转成 list[tuple]
        cfg.points = [tuple(p) for p in cfg.points]
        return cfg
