# LiveSoul Agent

一个按仓库说明实现的 Python 原型项目，用于在直播场景中抓取弹幕区域、识别文字、生成 AI 回复，并把回复转成语音播放。

当前实现状态和后续建议已整理到 [handover.md](/Users/luyi/Code/GithubCode/livesoul-agent/handover.md)，下次继续改动时优先看这里。

## 功能

- 截图直播画面并裁剪弹幕区域
- 优先使用 OCR 识别弹幕
- OCR 失败或低置信度时回退到视觉模型
- 动态加载 `agent_config/SOUL.md`、`IDENTITY.md`、`USER.md`
- 生成适合直播口播的短回复
- 支持 `console`、`openai`、`edge`、`pyttsx3` 四种 TTS 方式
- 使用 `asyncio` 持续运行整条处理链路

## 当前状态

- 已从纯设计文档落成可运行原型
- 默认行为是每次启动时手动框选弹幕区域
- 已明确支持 macOS 和 Windows
- 已补启动诊断，便于定位权限、OCR、TTS 依赖问题

## 项目结构

```text
livesoul-agent/
├── agent_config/
├── src/
├── README.md
├── requirements.txt
└── .env.example
```

## 平台支持

当前项目明确支持：

- macOS
- Windows

两端的核心能力一致：屏幕截图、手动框选弹幕区域、OCR、视觉回退、AI 回复、TTS 输出。

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

如果不授予，截图和区域框选都会失败。

### Windows

```bash
python -m venv .venv
.venv\\Scripts\\activate
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
- `OCR_CONFIDENCE_THRESHOLD`：OCR 回退阈值
- `TTS_PROVIDER`：默认 `console`

如需启用真实模型：

- 视觉识别：填写 `VISION_API_KEY`、`VISION_MODEL_NAME`、`VISION_API_BASE`
- 文本生成：填写 `LLM_API_KEY`、`LLM_MODEL_NAME`、`LLM_API_BASE`
- OpenAI TTS：填写 `TTS_API_KEY`、`TTS_MODEL_NAME`、`TTS_API_BASE`

如果暂时没有真实截图环境，可以设置：

```env
SCREENSHOT_IMAGE_PATH=/absolute/path/to/sample.png
```

这样程序会反复读取同一张图片，便于验证 OCR/Agent/TTS 链路。

注意：设置了 `SCREENSHOT_IMAGE_PATH` 时，交互式框选不会启动，因为这时程序运行在静态图片模式。

## macOS 注意事项

- 如果启动后日志里出现截图失败，先检查 Screen Recording 权限。
- 如果区域框选无法弹出，通常是 `tkinter` 不可用，换用带 Tk 的 Python 发行版。
- `afplay` 已用于 macOS 音频播放，不需要额外改代码。
- 如果你只是把 iPhone 投屏到 Mac，这个项目同样可用，前提只是直播画面能显示在屏幕上。

## Windows 注意事项

- 保证 OBS 或投屏窗口没有最小化。
- 如果截图区域不对，重新启动后再框一次。
- `edge-tts`、`openai` 和 `pyttsx3` 都可以作为 TTS 方案。

## 运行

```bash
python -m src.main
```

程序启动后会持续执行：

1. 捕获画面
2. 裁剪弹幕区域
3. OCR 识别
4. 视觉模型回退
5. AI 生成回复
6. TTS 播放

按 `Ctrl+C` 可停止。

## 说明

- `SOUL.md`、`IDENTITY.md`、`USER.md` 每次生成回复时都会重新读取，修改后可即时生效。
- OCR、视觉模型、LLM、TTS 都做成了独立模块，方便替换实现。
- 默认配置偏向“先跑起来”。如果本机未安装 OCR/TTS 依赖或未配置 API，程序会降级为日志输出，而不是直接崩溃。
- 启动时会自动输出平台兼容性检查日志，尤其会提示 macOS 屏幕录制权限和本地依赖缺失问题。
