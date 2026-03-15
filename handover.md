# LiveSoul Agent Handover

## 当前状态

项目已经从纯文档状态落成了一个可运行的 Python 原型，当前主链路是：

1. 截图当前屏幕
2. 启动时手动框选弹幕区域
3. 优先调用视觉模型识别弹幕
4. 调用 AI 生成回复
5. 调用 TTS 播放回复

当前流程已经改成严格串行：

- 一次只处理一帧完整流程
- 前一轮 TTS 未结束前，不会开始下一轮截图
- 如果当前识别出的整块弹幕文本与上一轮完全一致，会直接跳过 LLM 和 TTS

同时，项目现在已经有第一版 Windows 桌面 GUI，可直接在界面里启动/停止程序、编辑提示词、查看日志、显示监控框，并在运行中拖动监控区域位置。

## 这次已经完成的改动

- 把 LLM 接口从 `responses.create(...)` 改成了 `chat.completions.create(...)`，已适配当前使用的 iflow 兼容接口
- 验证并保留了视觉模型主路径，当前已改成完全依赖视觉模型识别
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
- 配置主存储已从 `.env` 迁移到 `default_config.json + runtime/config.json`
- 人设主存储已从 `agent_config/` 迁移到 `profiles/<profile_id>/`
- 配置项已从 `TTS_API_BASE` 迁移为 `TTS_API_ENDPOINT`，并保留旧字段兼容
- `.env.example` 已同步更新

## 关键文件

- 入口：[src/main.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/main.py)
- 配置：[src/config.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/config.py)
- 默认配置模板：[default_config.json](/Users/luyi/Code/GithubCode/livesoul-agent/default_config.json)
- 默认人设目录：[profiles/default](/Users/luyi/Code/GithubCode/livesoul-agent/profiles/default)
- 截图：[src/screenshot.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/screenshot.py)
- 区域框选：[src/region_selector.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/region_selector.py)
- 视觉回退：[src/vision_module.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/vision_module.py)
- AI Agent：[src/ai_agent.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/ai_agent.py)
- TTS：[src/tts_module.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/tts_module.py)
- GUI：[src/gui_app.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/gui_app.py)
- 全局热键：[src/hotkey_listener.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/hotkey_listener.py)
- 平台检查：[src/platform_support.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/platform_support.py)
- GUI 规划：[GUI_PLAN.md](/Users/luyi/Code/GithubCode/livesoul-agent/GUI_PLAN.md)

## 当前配置约定

推荐配置方式：

- 提交到 Git 的默认模板使用 [default_config.json](/Users/luyi/Code/GithubCode/livesoul-agent/default_config.json)
- 本机真实配置使用 `runtime/config.json`
- 当前激活的人设由 `active_profile_id` 指向 `profiles/<profile_id>/`
- `capture.auto_select_region=true`
- `capture.vision_timeout_seconds` 控制视觉识别超时
- `tts.provider=siliconflow` 或 `tts.provider=minimaxi`
- `runtime.memory_dir=runtime/memory`

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
- 真实直播截图验证过：视觉模型识别已能承担主链路
- 运行记忆文件会自动生成：
  - `runtime/memory/session_memory.json`
  - `runtime/memory/session_memory.html`

## 当前已知问题 / 边界

- 还没有真正做“窗口级捕获”，当前仍是整屏截图后裁剪
- TTS 播放目前仍是系统播放，还没接 OBS 音频路由
- SiliconFlow 如果使用 `mp3`，采样率必须是 `32000` 或 `44100`
- GUI 当前只支持拖动监控框位置，不支持直接拖动改变宽高
- GUI 当前已经较可用，但文案、布局、缩放与交互细节还需要继续打磨
- 没有自动化测试
- 还没有打包成桌面应用

### 2026-03-14 GUI 与配置系统迭代

#### 今天实际遇到的问题

- 第一版 GUI 虽然已经能启动和运行，但配置系统仍处在 `.env` 向 JSON 迁移的中间态，界面保存配置后容易出现值来源混杂，不利于后续分发。
- 文本模型和视觉模型的提示词仍然写死在代码里，用户只能调整人设提示词，无法直接针对“回复质量不好”或“视觉识别风格不对”做精细调参。
- 实时日志区域最初只是纯文本追加：
  - `INFO / WARNING / ERROR` 没有颜色区分
  - 每条日志之间没有明显间隔
  - 时间戳直接显示毫秒和时区偏移，不适合普通用户阅读
- GUI 头部右上角状态区之前直接复用了“最新日志”式文案，导致内容过长时折行挤压，显示不完整。
- 目前启动 GUI 还依赖手动输入命令，不符合后续面向普通用户的使用方式。

#### 原因判断与结论

- `.env` 适合作为开发期环境变量容器，不适合承担桌面应用长期配置源；当前更合理的结构是：
  - 提交到 Git 的默认模板：`default_config.json`
  - 本机真实配置：`runtime/config.json`
  - 可切换的人设目录：`profiles/<profile_id>/`
- 模型提示词与人设提示词应拆开管理，才能让用户在不改代码的前提下调节回答效果和视觉识别指令。
- 日志区域应该从“终端文本视图”转成“桌面应用日志面板”，至少要解决级别区分、可读间距和时间显示问题。
- 头部状态区不应该承载日志流，而应该只展示当前状态、下一步提示和用户级说明。
- 一键启动脚本是 MVP 分发前的必要过渡方案，至少可以让非开发用户通过双击启动当前 GUI。

#### 这次已经落地的修复

- [src/config.py](/C:/Users/luyi1/code/github/livesoul-agent/src/config.py)
  - JSON 配置体系已成为主路径。
  - `runtime/config.json` 由 GUI 和 runtime 共同读写。
  - `.env` 仅保留首次迁移兼容，不再作为主配置源。
- [default_config.json](/C:/Users/luyi1/code/github/livesoul-agent/default_config.json)
  - 新增并提交默认配置模板。
  - 作为后续安装包和首次启动初始化的基线配置。
- [profiles/default](/C:/Users/luyi1/code/github/livesoul-agent/profiles/default)
  - 默认 profile 目录已补齐。
  - 在原有 `SOUL.md`、`IDENTITY.md`、`USER.md` 之外，新增：
    - [profiles/default/LLM_SYSTEM.md](/C:/Users/luyi1/code/github/livesoul-agent/profiles/default/LLM_SYSTEM.md)
    - [profiles/default/VISION_PROMPT.md](/C:/Users/luyi1/code/github/livesoul-agent/profiles/default/VISION_PROMPT.md)
- [src/ai_agent.py](/C:/Users/luyi1/code/github/livesoul-agent/src/ai_agent.py)
  - 文本模型系统提示词不再写死在代码里。
  - 运行时会读取当前 profile 下的 `LLM_SYSTEM.md`。
- [src/vision_module.py](/C:/Users/luyi1/code/github/livesoul-agent/src/vision_module.py)
  - 视觉识别提示词不再写死在代码里。
  - 运行时会读取当前 profile 下的 `VISION_PROMPT.md`。
- [src/gui_app.py](/C:/Users/luyi1/code/github/livesoul-agent/src/gui_app.py)
  - 人设页已扩展为 5 份可编辑文件，而不再只有 3 份。
  - 实时日志改成富文本卡片展示：
    - 按 `DEBUG / INFO / WARNING / ERROR / CRITICAL` 着色
    - 每条日志之间增加明显间距
    - 不再挤成一整块终端文本
  - 日志时间展示已统一处理为“本地时间，精确到秒”。
  - 头部右上角状态区已从“日志回显”改为单独状态面板，修复折行后显示不全的问题。
  - 头部、页签、按钮和状态区的视觉样式做了一轮收口，当前更接近桌面产品界面而不是调试面板。
- [launch_gui.cmd](/C:/Users/luyi1/code/github/livesoul-agent/launch_gui.cmd)
  - 新增 Windows 一键启动脚本。
  - 双击后会自动激活当前 `.venv` 并启动 GUI。
- [README.md](/C:/Users/luyi1/code/github/livesoul-agent/README.md)
  - 已同步更新 JSON 配置、5 份提示词文件和 `launch_gui.cmd` 的使用说明。

#### 已验证结果

- `python -m compileall src` 通过。
- GUI 冒烟测试通过：
  - 主窗口可以正常拉起并自动退出。
- 实际重新启动 GUI 后已验证：
  - 当前版本可正常打开
  - 新的提示词编辑区已接入
  - 一键启动脚本已可用
  - 日志面板可按级别渲染样式
  - 时间显示已从“UTC+偏移”调整为本地时间

#### 当前仍存在的问题 / 边界

- 现在仍然是开发态 GUI，不是正式安装包。
- `launch_gui.cmd` 只是过渡方案，最终仍然应做成真正的安装器或可执行桌面应用。
- 当前 profile 只支持“切换现有目录”，还不支持在 GUI 内新建 / 复制 / 删除 profile。
- 模型提示词已经放开，但还没有做模板化说明、变量提示或“恢复默认值”功能。
- 日志面板已明显可读，但还没有筛选、搜索、清空或导出能力。

#### 最终想实现的产品目标

- 最终交付物仍然应是面向普通用户的 Windows 安装包或桌面应用，而不是要求用户自己理解 Python 环境和启动命令。
- 用户下载安装后，应该能直接：
  - 双击启动
  - 选择监控区域
  - 调整人设和模型提示词
  - 查看运行状态和日志
  - 不需要面对 `.venv`、`pip install`、命令行或外部依赖说明

#### 后续 TODO

1. 继续完善 profile 管理
   - 在 GUI 内支持新建 / 复制 / 删除 profile。
   - 这样用户可以维护多套不同主播风格和直播场景的人设，而不是只能复用一个默认目录。

2. 完善提示词编辑体验
   - 给 `LLM_SYSTEM.md` 和 `VISION_PROMPT.md` 增加默认模板说明、重置默认值、字段解释。
   - 这样用户调整效果时，不需要猜这些文件应该怎么写。

3. 继续打磨日志面板
   - 增加筛选、清空、搜索、导出。
   - 这样日志区域才能从“可看”变成“可排障”。

4. 做真正的分发入口
   - 当前 `launch_gui.cmd` 只是过渡。
   - 后续需要继续推进到 `PyInstaller + 安装包`，并逐步把外部依赖准备流程收进首次启动体验里。

### 2026-03-15 绿色分发包打包

#### 今天实际遇到的问题

- 用户希望的不只是源码仓库里的“一键启动”，而是可以直接发给其他 Windows 用户使用的绿色包。
- 当前 GUI 和 runtime 仍默认按源码仓库方式运行：
  - GUI 里通过 `python -m src.main` 拉起 runtime
  - 多个模块默认按源码目录推导资源路径
- 如果直接把现有仓库压缩发给别人，对方仍然需要 Python、`.venv` 和依赖，达不到“开箱即用”。

#### 原因判断与结论

- 要做成当前阶段最实用的分发方式，不是先做安装器，而是先做一个 `PyInstaller` 绿色包目录。
- 这要求把 GUI 和 runtime 拆成两个可执行文件：
  - GUI exe 负责桌面界面
  - runtime exe 负责实际截图、识别、回复和 TTS 主循环
- 同时需要把默认配置和默认 profile 一起放到可执行文件旁边，而不是继续依赖源码目录。

#### 这次已经落地的修复

- [src/config.py](/C:/Users/luyi1/code/github/livesoul-agent/src/config.py)
  - 新增冻结态路径解析。
  - 当程序以打包 exe 运行时，会优先以可执行文件所在目录作为配置根目录。
- [src/gui_app.py](/C:/Users/luyi1/code/github/livesoul-agent/src/gui_app.py)
  - 新增冻结态根目录解析。
  - GUI 在打包后不再尝试 `python -m src.main`，而是改为拉起同目录下的 `LiveSoulRuntime.exe`。
- [packaging/gui_entry.py](/C:/Users/luyi1/code/github/livesoul-agent/packaging/gui_entry.py)
  - 新增 GUI 打包入口。
- [packaging/runtime_entry.py](/C:/Users/luyi1/code/github/livesoul-agent/packaging/runtime_entry.py)
  - 新增 runtime 打包入口。
- [scripts/build_portable.ps1](/C:/Users/luyi1/code/github/livesoul-agent/scripts/build_portable.ps1)
  - 新增绿色包构建脚本。
  - 负责：
    - 构建 `LiveSoulGUI.exe`
    - 构建 `LiveSoulRuntime.exe`
    - 组装 `dist/LiveSoul_Portable/`
    - 复制 `default_config.json`
    - 复制 `profiles/default/`
    - 初始化空的 `runtime/` 目录
    - 生成绿色包入口 `Start-LiveSoul.cmd`

#### 已验证结果

- 已安装 `PyInstaller` 并成功完成本机构建。
- 绿色包输出目录已生成：
  - `dist/LiveSoul_Portable/`
- 打包后的 GUI 可执行文件已成功启动。
- 打包后的 runtime 可执行文件已做过最小烟测，确认能够真实拉起主循环。
- 烟测产生的临时配置和日志已清理，当前 `dist/LiveSoul_Portable/` 目录保持为可分发状态。

#### 当前仍存在的问题 / 边界

- 这还是“绿色包”，不是正式安装器。
- `LiveSoulRuntime.exe` 体积已经从约 241 MB 降到约 76 MB，但对绿色包来说仍然不算小。
- 绿色包当前已内置 `ffplay.exe`。
- 用户拿到绿色包后仍然需要填写自己的模型 API 配置。

#### 最终想实现的产品目标

- 当前绿色包已经能满足“解压后双击启动”的分发方式。
- 但最终目标仍然应是：
  - 更小体积
  - 自动准备外部依赖
  - 正式安装器或桌面应用分发形态

#### 后续 TODO

1. 做真正的首启引导
   - 当前绿色包已经能双击启动，但首次使用时仍缺少“配置 API / 检查环境 / 引导选区”的产品化引导。

2. 后续再评估正式安装器
   - 绿色包路线已经打通。
   - 下一阶段再决定是否进入 `PyInstaller + Inno Setup/MSIX` 的安装器阶段。

### 2026-03-15 移除 OCR 并内置 ffplay

#### 今天实际遇到的问题

- 用户明确要求当前版本不要再保留 OCR 回退，运行链路应完全依赖视觉模型。
- 之前绿色包虽然已经能打出来，但 runtime 体积很大，核心原因是依赖链仍然把 `easyocr / pytesseract / torch / torchvision / scipy` 带了进去。
- 之前绿色包虽然已经打通，但还没有把 `ffplay` 一起放进包里，目标机器上的音频播放仍然可能受系统是否安装 FFmpeg 影响。
- 便携包烟测时还额外暴露出一个配置读取问题：如果 `runtime/config.json` 由 PowerShell 带 BOM 写出，当前 loader 会直接报 `JSONDecodeError: Unexpected UTF-8 BOM`。

#### 原因判断与结论

- 既然当前产品策略已经决定“只依赖视觉模型”，那 OCR 相关代码和依赖继续保留只会：
  - 增加包体积
  - 增加启动检查噪音
  - 增加维护复杂度
- `ffplay` 属于当前 Windows 绿色包里的必要配套工具，应该直接放进包内，而不是继续依赖目标机器环境。
- JSON 配置读取应兼容 `utf-8-sig`，否则绿色包在 Windows 上很容易被 BOM 编码坑到。

#### 这次已经落地的修复

- [src/main.py](/C:/Users/luyi1/code/github/livesoul-agent/src/main.py)
  - 移除了 `OCRModule`。
  - 识别链路改为只调用视觉模型。
  - 当视觉模型超时或失败时，当前轮直接返回空结果，不再回退 OCR。
- [src/ocr_module.py](/C:/Users/luyi1/code/github/livesoul-agent/src/ocr_module.py)
  - 已删除。
- [src/platform_support.py](/C:/Users/luyi1/code/github/livesoul-agent/src/platform_support.py)
  - 移除了 OCR / `tesseract` 检查逻辑。
  - 启动日志不再输出 OCR 相关警告。
- [requirements.txt](/C:/Users/luyi1/code/github/livesoul-agent/requirements.txt)
  - 移除了 `easyocr`
  - 移除了 `pytesseract`
- [src/tts_module.py](/C:/Users/luyi1/code/github/livesoul-agent/src/tts_module.py)
  - 新增 `_resolve_ffplay()`。
  - 在冻结态运行时优先查找绿色包内的 `tools/ffmpeg/bin/ffplay.exe`。
  - 找不到项目内 `ffplay` 时才再回退到系统 PATH。
- [scripts/build_portable.ps1](/C:/Users/luyi1/code/github/livesoul-agent/scripts/build_portable.ps1)
  - 打包绿色包时会把本机 `C:\Program Files\ffmpeg\bin\ffplay.exe` 复制进：
    - `dist/LiveSoul_Portable/tools/ffmpeg/bin/ffplay.exe`
- [src/config.py](/C:/Users/luyi1/code/github/livesoul-agent/src/config.py)
  - 默认配置和运行时配置读取已统一改成 `utf-8-sig`。
  - 这样即使 `runtime/config.json` 带 BOM，也能正常加载。
- [README.md](/C:/Users/luyi1/code/github/livesoul-agent/README.md)
  - 已同步更新“当前不再依赖 OCR 回退、绿色包已内置 ffplay”的使用说明。

#### 已验证结果

- `python -m compileall src` 通过。
- OCR 相关代码搜索已清理：
  - runtime 主链路已不再引用 `OCRModule`
  - `requirements.txt` 已不再包含 OCR 依赖
- 重新构建绿色包后，实际结果为：
  - [dist/LiveSoul_Portable/LiveSoulRuntime.exe](/C:/Users/luyi1/code/github/livesoul-agent/dist/LiveSoul_Portable/LiveSoulRuntime.exe) 体积约 `76 MB`
  - 相比之前约 `241 MB` 明显下降
- 绿色包内已确认存在：
  - [dist/LiveSoul_Portable/tools/ffmpeg/bin/ffplay.exe](/C:/Users/luyi1/code/github/livesoul-agent/dist/LiveSoul_Portable/tools/ffmpeg/bin/ffplay.exe)
- 打包后的 GUI exe 已验证可正常启动。
- 打包后的 runtime exe 已做烟测，日志确认：
  - 主循环可以正常启动
  - 启动时不再出现 OCR / `tesseract` 检查日志
  - BOM 编码配置文件已可正常读取

#### 当前仍存在的问题 / 边界

- 当前识别链路完全依赖视觉模型，因此如果视觉接口不可用，就不会再有 OCR 兜底。
- `LiveSoulRuntime.exe` 虽然已经显著缩小，但对绿色包来说仍然不算小。
- 当前内置的是 `ffplay.exe`，还不是完整的 FFmpeg 工具链。
- 绿色包依然需要用户自己填写视觉模型、LLM、TTS 的 API 配置。

#### 最终想实现的产品目标

- 当前路线已经从“开发态命令行项目”推进到“可分发的 Windows 绿色包”。
- 最终目标仍然是：
  - 普通用户拿到包后直接双击启动
  - 首次进入图形化引导
  - 自动准备必要工具
  - 不需要理解 Python、OCR、FFmpeg、环境变量

#### 后续 TODO

1. 做首启配置引导
   - 当前绿色包虽然能启动，但首次使用仍然要用户手动理解配置结构。
   - 后续应把 API Key、模型地址、默认 provider 等收进 GUI 引导流程。

2. 优化视觉模型不可用时的用户反馈
   - 现在移除 OCR 之后，视觉模型不可用就会直接没有识别结果。
   - 后续需要把这种情况在 GUI 里做成更明确的提示，而不是只留在日志里。

3. 继续收分发体验
   - 当前已经内置 `ffplay`，后续可以再决定是否补 `ffmpeg` / `ffprobe`。
   - 也可以继续推进到正式安装器，而不是只停留在绿色包阶段。

### 2026-03-14 配置存储重构

#### 今天实际遇到的问题

- 当前 GUI 仍然读写 `.env`，而 `.env` 更适合开发环境，不适合作为桌面应用的主配置存储。
- `TTS_PROVIDER`、`TTS_API_ENDPOINT`、`TTS_MODEL_NAME` 这种有关联关系的配置在 `.env` 里容易被保存成错配状态，导致运行时调用失败。
- `SOUL.md`、`IDENTITY.md`、`USER.md` 目前只有一套固定文件，不适合未来做多个人设切换。

#### 原因判断与结论

- `.env` 不适合承担“桌面 GUI 主配置 + 多配置切换 + 未来分发安装”的职责。
- 机器配置应该改成结构化 JSON。
- 人设文本仍然适合保留为 Markdown，但需要放进 profile 目录体系里。

#### 这次已经落地的修复

- [src/config.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/config.py)
  - 重构为 JSON 配置中心。
  - 默认模板来自 [default_config.json](/Users/luyi/Code/GithubCode/livesoul-agent/default_config.json)。
  - 本机实际配置使用 `runtime/config.json`。
  - 如果 `runtime/config.json` 不存在，会优先尝试从旧 `.env` 迁移，否则复制默认模板。
- [profiles/default](/Users/luyi/Code/GithubCode/livesoul-agent/profiles/default)
  - 新增默认 profile 目录。
  - `SOUL.md`、`IDENTITY.md`、`USER.md` 迁移到 `profiles/default/`。
  - 新增 `meta.json` 描述 profile 信息。
- [src/gui_app.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/gui_app.py)
  - GUI 不再把 `.env` 当主配置源。
  - 改为读写 `runtime/config.json`。
  - 提示词编辑改为读写当前 `active_profile_id` 对应的 profile 目录。
  - 新增 profile 下拉切换入口，为后续多套人设切换打基础。
- [.gitignore](/Users/luyi/Code/GithubCode/livesoul-agent/.gitignore)
  - 明确忽略 `runtime/config.json`。

#### 当前结论

- 配置系统已经完成从 `.env` 到 JSON 的主存储迁移。
- 后续桌面 GUI 和未来安装包都应该围绕：
  - 可提交的默认模板：`default_config.json`
  - 本机真实配置：`runtime/config.json`
  - 多人设目录：`profiles/<profile_id>/`

#### 后续 TODO

1. 继续把 GUI 细节适配到 JSON 配置
   - 增加更明确的 provider / endpoint / model 弱提醒
   - 后续支持新增 / 复制 / 删除 profile

2. 清理旧 `.env` 路径
   - 目前保留 `.env` 仅用于迁移兼容
   - 后续可以在文档和代码里逐步降级为 legacy

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
python -m src.main
```

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

### 停止方式

- 终端按 `Ctrl+C`
- Windows 下按 `Ctrl+Alt+Q`
