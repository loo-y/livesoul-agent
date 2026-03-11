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

如果暂时没有真实截图环境，可以设置：

```env
SCREENSHOT_IMAGE_PATH=/absolute/path/to/sample.png
```

这样程序会反复读取同一张图片，便于验证 OCR / Agent / TTS 链路。

注意：设置了 `SCREENSHOT_IMAGE_PATH` 时，交互式框选不会启动，因为这时程序运行在静态图片模式。

## macOS 注意事项

- 如果启动后日志里出现截图失败，先检查 Screen Recording 权限。
- 如果区域框选无法弹出，通常是 `tkinter` 不可用，换用带 Tk 的 Python 发行版。
- `afplay` 已用于 macOS 音频播放，不需要额外改代码。

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
