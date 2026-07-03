# 按键精灵 · 自动点击器（Windows）

一个基于 Python + PyQt5 的自动点击工具，支持自定义点击频率、点击位置，并可按多种条件触发。

## 功能
- **点击设置**：左/右键、单击/双击、点击间隔（ms）、随机抖动（防机械化）
- **点击位置**：
  - 固定坐标（可添加多点，轮流点击）
  - 跟随鼠标（点在当前光标处）
  - 图像识别（在屏幕上找到模板图片时点击其中心）
- **触发 / 停止条件**：
  - 全局热键启停（默认 **F6**，切到其他窗口也生效）
  - 启动延时
  - 停止条件：无限 / 达到次数 / 达到时长
- 配置自动保存到 `config.json`
- 紧急停止：把鼠标猛地移到屏幕**左上角**即可中断（pyautogui failsafe）

## 安装
```bash
pip install -r requirements.txt
```

## 运行
```bash
python main.py
```

## 使用步骤
1. 在「点击设置」里选择按键、方式、间隔。
2. 选择「点击位置」模式：
   - **固定坐标**：点「拾取坐标」，把鼠标移到目标处，3 秒后自动记录当前光标坐标。
   - **图像识别**：点「选择模板…」加载一张要匹配的截图，调整置信度（默认 0.85）。
3. 在「触发 / 停止条件」里设置启动热键、延时和停止条件。
4. 点「开始」或按热键（F6）启动；再次点击/按键停止。

## 打包成 exe
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name ClickSpirit main.py
```
生成的可执行文件在 `dist/ClickSpirit.exe`。

## 项目结构
```
main.py                 入口
app/config.py           配置数据类 + JSON 存取
app/vision.py           截屏 + OpenCV 模板匹配
app/worker.py           点击循环（QThread）
app/hotkey.py           全局热键（pynput）
ui/main_window.py       主窗口界面
```

## 说明
- 请在获得授权的场景下使用；请勿用于违反目标程序服务条款或法律法规的用途。
