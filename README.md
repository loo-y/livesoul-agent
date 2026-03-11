# LiveSoul Agent

一个用于直播场景的 Python 原型项目：抓取弹幕区域、识别文字、生成 AI 回复，并把回复转成语音播放。

当前实现状态和后续建议整理在 [handover.md](/Users/luyi/Code/GithubCode/livesoul-agent/handover.md)。

## 功能

- 截图直播画面并裁剪弹幕区域
- 优先使用视觉模型识别弹幕，超时或失败时回退到 OCR
- 动态加载 `agent_config/SOUL.md`、`IDENTITY.md`、`USER.md`
- 生成适合直播口播的短回复
- 支持 `console`、`minimaxi`、`siliconflow`、`openai`、`edge`、`pyttsx3` 六种 TTS 方式
- 持久化最近弹幕和最近几轮 `(弹幕 -> 回复)` 上下文
- 使用串行流水线执行整条处理链路，避免前一轮 TTS 未结束就开始下一轮

## 当前状态

- 已从纯设计文档落成可运行原型
- 默认行为是每次启动时手动框选弹幕区域
- 已明确支持 macOS 和 Windows
- 已补启动诊断，便于定位权限、OCR、TTS 依赖问题
- Windows 下已支持全局快捷键 `Ctrl+Alt+Q` 快速停止运行中的程序

## 项目结构

```text
livesoul-agent/
├── agent_config/
├── src/
├── runtime/
├── README.md
├── requirements.txt
└── .env.example
```

## 平台支持

当前项目明确支持：

- macOS
- Windows

两端的核心能力一致：屏幕截图、手动框选弹幕区域、视觉识别、OCR 回退、AI 回复、TTS 输出。

差异主要在系统权限和本地依赖：

- macOS：需要开启 Screen Recording 权限
- Windows：需要保证投屏窗口或 OBS 窗口可见

## 安装

### macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

如果你要用 `pytesseract`，建议再装：

```bash
brew install tesseract tesseract-lang
```

第一次运行前，确认 macOS 已授予你的终端或 Python 应用以下权限：

- `System Settings > Privacy & Security > Screen Recording`

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## 配置

默认行为已经改成“每次启动时都手动框选弹幕区域”。程序启动后会弹出一个全屏选择器：

1. 程序先抓取当前屏幕
2. 你用鼠标拖一个框选中弹幕区域
3. 按回车确认
4. 本次运行期间一直按这个区域截图

对应开关是：

- `AUTO_SELECT_REGION=true`

常用运行配置：

- `SCREENSHOT_INTERVAL`：截图频率
- `VISION_TIMEOUT_SECONDS`：视觉识别超时时间，超时后回退到 OCR
- `TTS_PROVIDER`：当前 `.env.example` 默认 `minimaxi`，也支持 `siliconflow`
- `MEMORY_DIR`：运行记忆文件目录

如需启用真实模型：

- 视觉识别：填写 `VISION_API_KEY`、`VISION_MODEL_NAME`、`VISION_API_BASE`
- 文本生成：填写 `LLM_API_KEY`、`LLM_MODEL_NAME`、`LLM_API_BASE`
- TTS：填写 `TTS_API_KEY`、`TTS_MODEL_NAME`、`TTS_API_ENDPOINT`、`TTS_VOICE`
- 如需调整 TTS 音频参数，可再设置 `TTS_RESPONSE_FORMAT`、`TTS_SAMPLE_RATE`、`TTS_STREAM`、`TTS_SPEED`、`TTS_GAIN`

TTS 供应商补充说明：

- `minimaxi` 当前按 MP3 路径工作
- `siliconflow` 已验证可用，推荐配置为 `TTS_RESPONSE_FORMAT=mp3` 且 `TTS_SAMPLE_RATE=44100`
- 如果 `siliconflow` 使用 `opus` / `ogg`，macOS 会自动改走 `ffplay` 播放；如果使用 `mp3`，则继续走系统 MP3 播放链路

如果暂时没有真实截图环境，可以设置：

```env
SCREENSHOT_IMAGE_PATH=/absolute/path/to/sample.png
```

这样程序会反复读取同一张图片，便于验证 OCR / Agent / TTS 链路。

注意：设置了 `SCREENSHOT_IMAGE_PATH` 时，交互式框选不会启动，因为这时程序运行在静态图片模式。

## macOS 注意事项

- 如果启动后日志里出现截图失败，先检查 Screen Recording 权限。
- 如果区域框选无法弹出，通常是 `tkinter` 不可用，换用带 Tk 的 Python 发行版。
- MP3 默认使用 `afplay`；`opus` / `ogg` 会优先使用 `ffplay`。

## Windows 注意事项

- 保证 OBS 或投屏窗口没有最小化。
- 如果截图区域不对，重新启动后再框一次。
- 当前已验证 `minimaxi` TTS 可用。
- 运行中可按 `Ctrl+Alt+Q` 全局快捷退出。

## 运行

```bash
python -m src.main
```

程序启动后会持续执行：

1. 捕获画面
2. 裁剪弹幕区域
3. 视觉模型识别
4. 超时或失败时回退到 OCR
5. AI 生成回复
6. TTS 播放

当前是严格串行执行：上一轮 TTS 未结束前，不会开始下一轮截图。

停止方式：

- 终端里按 `Ctrl+C`
- Windows 下按全局快捷键 `Ctrl+Alt+Q`

## 说明

- `SOUL.md`、`IDENTITY.md`、`USER.md` 每次生成回复时都会重新读取，修改后可即时生效。
- OCR、视觉模型、LLM、TTS 都做成了独立模块，方便替换实现。
- 程序会把最近一次识别出的弹幕和最近几轮 `(弹幕 -> 回复)` 持久化到 `runtime/memory/session_memory.json`，同时生成便于查看的 `runtime/memory/session_memory.html`。
- LLM 会带上最近几轮本地上下文，降低重复回复概率。
- 如果当前截图识别结果与上一轮完全一致，会跳过 LLM 和 TTS，避免弹幕未变化时重复说话。
- 默认配置偏向“先跑起来”。如果本机未安装 OCR / TTS 依赖或未配置 API，程序会降级为日志输出，而不是直接崩溃。
- 启动时会自动输出平台兼容性检查日志，尤其会提示 macOS 屏幕录制权限和本地依赖缺失问题。

## TODO

### 今天实际遇到的问题

- Windows 上当前 `.venv` 绑定的是 `pyenv-win` 管理的 Python `3.12.10`。
- 该解释器里的 `tkinter` 可以导入，但在执行 `tk.Tk()` 时会因为 `Tcl/Tk` 初始化失败而报错，导致原始的手动框选区域逻辑无法启动。
- 当前环境里的 OpenCV 也不是带 GUI 的构建，`cv2.namedWindow` / `cv2.selectROI` 无法作为稳定替代。
- Windows 默认的 `os.startfile()` 音频播放是非阻塞的，无法可靠保证“前一个音频播放完，再进入下一轮主循环”。

### 当前 MVP 已做的临时方案

- 区域选择已改成多后端回退：
  - 优先 `tkinter`
  - `tkinter` 失败时回退 OpenCV
  - OpenCV GUI 不可用时，Windows 下回退到 PowerShell + WinForms 的全屏选区
- Windows 音频播放已改成优先使用 `ffplay` 阻塞播放；只有在找不到 `ffplay` 时才回退到系统默认播放器。
- 当前这套方案已经能满足 MVP：手动框选区域、进入识别主循环、并且等待前一段音频播完再进入下一轮。

### 最终想实现的分发目标

- 项目最终不是交付一套 Python 命令，而是交付一个面向普通用户的安装包或桌面应用。
- 用户下载并安装后，应当可以开箱即用，而不是要求用户理解 `pyenv-win`、`.venv`、`pip install`、`ffmpeg`、环境变量等开发概念。
- 首次启动时，应用应自动准备运行所需的外部依赖，并给出图形化或足够清晰的错误提示，而不是把终端报错直接暴露给最终用户。

### 后续要做的具体事项

- 安装与分发
  - 实现首次启动自动检测 `ffplay`。
  - 若系统中缺失 `ffplay`，自动下载固定版本的 FFmpeg 分发包并缓存到项目目录，例如 `tools/ffmpeg/bin/ffplay.exe`。
  - 播放逻辑优先查找项目内缓存的 `ffplay.exe`，其次查找系统 PATH，避免依赖用户手动安装。
  - 下载流程需要加入版本固定、失败提示、重复启动不重复下载。
- 区域选择
  - 评估是否保留当前的 PowerShell + WinForms 选区方案作为 Windows 长期实现，或后续替换为更稳的桌面 GUI 实现。
  - 需要保证分发后的安装包中，区域选择不再依赖用户机器上的 Python Tk 环境是否完好。
- 最终产品形态
  - 后续需要把项目打成 Windows 安装包或桌面可执行程序。
  - 最终交付目标应是“双击安装、双击启动、首次自动准备依赖、随后可直接使用”，而不是文档驱动的开发者式启动流程。
