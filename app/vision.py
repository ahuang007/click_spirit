"""屏幕截图 + OpenCV 模板匹配。"""
from typing import Optional, Tuple
import numpy as np
import cv2
import mss


def capture_screen() -> np.ndarray:
    """抓取主屏幕，返回 BGR 格式的 numpy 数组。"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 1 = 主显示器
        shot = sct.grab(monitor)
        img = np.array(shot)  # BGRA
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def load_template(path: str) -> Optional[np.ndarray]:
    """加载模板图片（BGR）。失败返回 None。"""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    return img


def find_template(
    screen: np.ndarray,
    template: np.ndarray,
    threshold: float,
) -> Optional[Tuple[int, int, float]]:
    """在 screen 中查找 template。

    返回匹配区域中心坐标与得分 (center_x, center_y, score)；
    若最高得分低于 threshold 则返回 None。
    """
    if template is None or screen is None:
        return None
    th, tw = template.shape[:2]
    sh, sw = screen.shape[:2]
    if th > sh or tw > sw:
        return None

    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < threshold:
        return None
    center_x = max_loc[0] + tw // 2
    center_y = max_loc[1] + th // 2
    return center_x, center_y, float(max_val)
