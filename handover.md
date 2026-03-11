# LiveSoul Agent Handover

## 当前状态

项目已经从纯文档状态落成了一个可运行的 Python 原型，当前主链路是：

1. 截图当前屏幕
2. 启动时手动框选弹幕区域
3. 优先调用视觉模型识别弹幕
4. 视觉模型超时或失败时回退到 OCR
5. 调用 AI 生成回复
6. 调用 TTS 播放回复

当前流程已经改成严格串行：

- 一次只处理一帧完整流程
- 前一轮 TTS 未结束前，不会开始下一轮截图
- 如果当前识别出的整块弹幕文本与上一轮完全一致，会直接跳过 LLM 和 TTS

同时，项目现在已经有第一版 Windows 桌面 GUI，可直接在界面里启动/停止程序、编辑提示词、查看日志、显示监控框，并在运行中拖动监控区域位置。

## 这次已经完成的改动

- 把 LLM 接口从 `responses.create(...)` 改成了 `chat.completions.create(...)`，已适配当前使用的 iflow 兼容接口
- 验证并保留了视觉模型主路径，当前真实截图场景下明显优于 OCR
- 把识别策略改成“视觉优先，超时后回退到 OCR”
- 修复了 EasyOCR 的本地模型损坏和输入类型问题，OCR 已恢复为可运行回退方案
- 把运行时从多队列并发改成串行流水线，避免 TTS 未播完就开始下一轮
- 增加了本地记忆：
  - 最近一次识别出的弹幕快照
  - 最近几轮 `(弹幕 -> 回复)` 上下文
- 运行记忆已持久化到：
  - `runtime/memory/session_memory.json`
  - `runtime/memory/session_memory.html`
- 增加了 Windows 全局快捷键 `Ctrl+Alt+Q`，可快速停止程序
- 接入并验证了 MiniMax TTS
- 新增并验证了 SiliconFlow TTS
- 新增了第一版桌面 GUI 入口 `src/gui_app.py`
- 配置项已从 `TTS_API_BASE` 迁移为 `TTS_API_ENDPOINT`，并保留旧字段兼容
- `.env.example` 已同步更新

## 关键文件

- 入口：[src/main.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/main.py)
- 配置：[src/config.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/config.py)
- 截图：[src/screenshot.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/screenshot.py)
- 区域框选：[src/region_selector.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/region_selector.py)
- OCR：[src/ocr_module.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/ocr_module.py)
- 视觉回退：[src/vision_module.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/vision_module.py)
- AI Agent：[src/ai_agent.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/ai_agent.py)
- TTS：[src/tts_module.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/tts_module.py)
- GUI：[src/gui_app.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/gui_app.py)
- 全局热键：[src/hotkey_listener.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/hotkey_listener.py)
- 平台检查：[src/platform_support.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/platform_support.py)
- GUI 规划：[GUI_PLAN.md](/Users/luyi/Code/GithubCode/livesoul-agent/GUI_PLAN.md)

## 当前配置约定

推荐配置方式：

- `AUTO_SELECT_REGION=true`
- 每次启动程序后手动框选弹幕区域
- `VISION_TIMEOUT_SECONDS` 控制视觉识别超时
- `TTS_PROVIDER=minimaxi`
- `TTS_API_ENDPOINT=https://api.minimaxi.com/v1/t2a_v2`
- `MEMORY_DIR=runtime/memory`

如果切到 SiliconFlow，当前推荐：

- `TTS_PROVIDER=siliconflow`
- `TTS_API_ENDPOINT=https://api.siliconflow.cn/v1/audio/speech`
- `TTS_MODEL_NAME=FunAudioLLM/CosyVoice2-0.5B`
- `TTS_VOICE=susu`
- `TTS_RESPONSE_FORMAT=mp3`
- `TTS_SAMPLE_RATE=44100`

仍保留对旧字段 `TTS_API_BASE` 的兼容，但不再推荐继续使用。

## 已做过的验证

- `python -m compileall src` 通过
- `from src.main import LiveSoulRuntime` 导入通过
- `src/gui_app.py` 已加入第一版 GUI 入口
- 已安装 `PySide6`
- GUI 冒烟验证通过：主窗口可以成功拉起并自动退出
- GUI 实测通过：
  - 可以启动 / 停止 runtime
  - 可以通过 GUI 完成区域选择并进入主循环
  - 可以显示监控区域透明描边
  - 监控框在当前机器上已校准到基本贴合选区
  - 可以在运行中拖动监控框位置，并让后续截图区域跟随
- 视觉模型真实调用通过
- iflow LLM 真实调用通过
- MiniMax TTS 真实调用通过，已成功生成 MP3 文件
- SiliconFlow TTS 真实调用通过：
  - `opus` 返回和文件落地通过
  - `mp3 + 44100Hz` 端到端通过
- 真实直播截图验证过：视觉模型识别质量明显优于 OCR
- 运行记忆文件会自动生成：
  - `runtime/memory/session_memory.json`
  - `runtime/memory/session_memory.html`

## 当前已知问题 / 边界

- 还没有真正做“窗口级捕获”，当前仍是整屏截图后裁剪
- OCR 可作为回退，但在真实弹幕场景下质量仍明显不如视觉模型
- `pytesseract` 依赖系统 `tesseract`，当前这台机器未装
- TTS 播放目前仍是系统播放，还没接 OBS 音频路由
- SiliconFlow 如果使用 `mp3`，采样率必须是 `32000` 或 `44100`
- GUI 当前只支持拖动监控框位置，不支持直接拖动改变宽高
- GUI 当前已经较可用，但文案、布局、缩放与交互细节还需要继续打磨
- 没有自动化测试
- 还没有打包成桌面应用

## 下次建议优先继续的方向

1. 优化截图能力
   - 支持指定窗口捕获
   - 对 OBS / 投屏窗口做自动定位

2. 优化 LLM 层策略
   - 在提示词层面对系统提示、进场提示、重复弹幕做更细的筛选
   - 调整最近上下文的组织方式，减少机械重复

3. 优化语音链路
   - 支持更稳定的本地播放
   - 接入 OBS 可直接使用的音频输出方式

4. 提升可运维性
   - 加自动化测试
   - 增加更清晰的日志和运行状态面板

## TODO

### 2026-03-11 这次实际踩到的问题

- 当前项目的 `.venv` 绑定到 `pyenv-win` 管理的 Python `3.12.10`。
- 这套 Python 在本机上 `import tkinter` 虽然成功，但执行 `tk.Tk()` 会因为 `Tcl/Tk` 初始化失败而直接报错，所以原本“启动后用 Tk 全屏框选弹幕区域”的路径不稳定。
- 尝试过用 OpenCV 作为 Windows 选区后备，但当前环境里的 OpenCV 是无 GUI 的构建，`cv2.namedWindow` / `cv2.selectROI` 也无法使用。
- Windows 下原本的音频播放使用 `os.startfile()` 唤起系统播放器，这个行为是非阻塞的，因此不满足“前一段音频必须播完，下一轮截图/识别/TTS 才能继续”的业务要求。

### 这次已经落地的 MVP 修复

- [src/region_selector.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/region_selector.py)
  - 保留原有 `tkinter` 选区实现。
  - 新增 OpenCV 选区回退。
  - 新增 Windows 下的 PowerShell + WinForms 全屏选区回退。
  - 这样即使 Tk 运行时损坏，项目依然可以在 Windows 上完成手动框选区域这一基础能力。
- [src/tts_module.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/tts_module.py)
  - Windows 下播放逻辑改为优先使用 `ffplay` 阻塞播放。
  - 只有找不到 `ffplay` 时才退回 `os.startfile()`。
  - 已用本地现成 mp3 做过顺序播放验证，确认现在是“前一个播完再返回”，满足串行流水线要求。

### 当前 MVP 的结论

- 现在项目已经可以在本机 Windows 上满足最小可行性：
  - 手动框选屏幕中的弹幕区域
  - 进入真实截图 / 识别 / 回复 / TTS 主循环
  - 等待前一条音频播放完成后再进入下一轮
- 这只是开发态可用，不等于最终适合分发。

### 最终产品目标

- 这个项目最终目标不是交付“让懂技术的人在终端里激活 `.venv` 再执行 `python -m src.main`”。
- 最终目标应是交付一个普通用户可安装、可启动、可使用的 Windows 分发包。
- 用户下载安装后，应做到尽量开箱即用，不要求理解：
  - `pyenv-win`
  - `.venv`
  - `pip install`
  - `ffmpeg` / `ffplay`
  - 环境变量配置

### 后续需要继续完成的分发方案

1. 自动准备 `ffplay`
   - 启动时先检测项目内是否已有 `ffplay.exe`，例如 `tools/ffmpeg/bin/ffplay.exe`
   - 若项目内没有，再检查系统 PATH
   - 若系统也没有，则自动下载固定版本的 FFmpeg 分发包并缓存到项目目录
   - 下载后统一优先走项目内缓存的 `ffplay.exe`
   - 需要补上版本固定、校验、失败提示、重复启动不重复下载

2. 降低对宿主 Python GUI 环境的依赖
   - 当前 PowerShell + WinForms 选区方案可以作为 Windows MVP
   - 但后续仍应评估是否需要更稳定、可打包的桌面 GUI 选区方案
   - 目标是：分发包运行时不再依赖用户本机 Python 的 Tk/Tcl 是否完好

3. 做真正的安装包 / 桌面应用
   - 后续需要把项目打包成 Windows 可执行程序或安装包
   - 最终体验目标应是：
     - 用户下载安装
     - 双击启动
   - 首次运行自动准备依赖
   - 后续直接使用
   - 不应把当前这种开发态命令行启动方式暴露给最终用户

### 2026-03-12 这次实际踩到的问题

- 第一版 GUI 做出来后，运行时确实可以从界面启动，但还暴露了几个非常具体的问题：
  - GUI 允许选择与当前项目实际不匹配的 TTS provider，导致 `.env` 被写成 `TTS_PROVIDER=openai`、但 endpoint / model 仍然是 SiliconFlow 的值，运行时在 TTS 阶段返回 `openai.NotFoundError: Not Found`
  - 监控框最初依赖日志里的 `Selected barrage region...` 文本读取选区坐标，但当 `.env` 的 `LOG_LEVEL=WARNING` 时，这条 `INFO` 日志根本不会输出，所以监控框完全不显示
  - 监控框在 Windows DPI 缩放场景下出现坐标偏移和尺寸放大，导致显示位置与真实截图区域不一致
  - 用户提出直播场景需要“始终知道当前截图区域在哪”，因此光有一次性选区还不够，需要常驻描边
  - 用户进一步提出直播中希望“直接拖动监控区域”，这要求拖动不只是改 GUI 浮层，而必须真实影响后续截图裁剪

### 2026-03-12 原因判断与结论

- TTS 报错不是 SiliconFlow 服务本身故障，而是 GUI 当前表单允许写入一组自相矛盾的 TTS 配置。
- 监控框不显示的根因不是浮层绘制失败，而是它最初依赖日志获取坐标，而日志级别配置把这条关键日志过滤掉了。
- 监控框位置偏移不是故意留安全边距，而是 Windows 屏幕缩放导致“截图物理像素坐标”和“Qt 浮层逻辑坐标”不在同一坐标系。
- 如果要满足“运行中拖动监控区域”的需求，必须把当前区域坐标从“GUI 的临时状态”提升成运行时和 GUI 共用的持久化状态。

### 2026-03-12 这次已经落地的修复

- [src/gui_app.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/gui_app.py)
  - 新增第一版 `PySide6` 桌面 GUI。
  - 中文化了主要界面文案、状态提示、按钮和页签。
  - 支持启动 / 停止 runtime、编辑提示词、编辑常用配置、查看日志和预览。
  - API Key 输入框新增“显示 / 隐藏”切换。
  - 新增窗口置顶。
  - 新增监控框显示开关。
  - 新增“拖动监控框”模式，可在运行中直接拖动当前监控区域位置。
  - TTS provider 下拉已收敛为当前项目实际使用的 `minimaxi` / `siliconflow`。
  - 如果 `.env` 里残留旧 provider，GUI 会自动回退到安全值并提示用户。
- [src/region_selector.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/region_selector.py)
  - 选区完成后会把当前区域坐标持久化到 `runtime/current_region.json`。
- [src/screenshot.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/screenshot.py)
  - 每轮截图裁剪前都会重新读取 `runtime/current_region.json`。
  - 这样 GUI 拖动监控框后，后续截图会立即跟随新位置，不需要重启。
- [requirements.txt](/Users/luyi/Code/GithubCode/livesoul-agent/requirements.txt)
  - 新增 `PySide6` 依赖。
- [README.md](/Users/luyi/Code/GithubCode/livesoul-agent/README.md)
  - 新增 GUI 入口说明和当前支持能力说明。
- [GUI_PLAN.md](/Users/luyi/Code/GithubCode/livesoul-agent/GUI_PLAN.md)
  - 单独记录了 GUI 的产品目标、结构规划和后续路线。

### 2026-03-12 当前阶段的结论

- 现在项目不仅有命令行 MVP，而且已经有可以实际使用的第一版 Windows 桌面 GUI。
- 当前这版 GUI 已经覆盖了真实使用中的核心能力：
  - 从 GUI 启动 / 停止 LiveSoul
  - 手动选区
  - 显示当前监控区域
  - 运行中拖动监控区域位置
  - 编辑提示词和常用运行参数
- 这仍然属于“可用的内测版 GUI”，还不是最终可分发的产品级桌面应用。

### 2026-03-12 后续具体 TODO

1. GUI 细节继续打磨
   - 继续优化窗口最小高度、信息密度、布局压缩、说明文案。
   - 继续打磨按钮反馈、状态提示和普通用户可理解性。

2. 监控框能力继续增强
   - 当前只支持拖动位置，后续补可视化缩放，允许直接调整宽高。
   - 考虑增加更明显或更低干扰的描边样式切换。

3. 配置一致性保护
   - 继续补启动前校验，避免 provider / endpoint / model 再次出现错配。
   - 把更多“容易填错但不该让用户承担”的配置逻辑收进 GUI。

4. 分发与安装
   - GUI 已经证明路线成立，下一阶段应逐步把它推进成真正的 Windows 安装包，而不是继续依赖命令行启动。

## 如何继续启动项目

### macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.main
```

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m src.main
```

### 停止方式

- 终端按 `Ctrl+C`
- Windows 下按 `Ctrl+Alt+Q`
