# LiveSoul Agent Handover

## 当前状态

项目已经从纯文档状态落成了一个可运行的 Python 原型，主链路完整：

1. 截图当前屏幕
2. 启动时手动框选弹幕区域
3. OCR 识别弹幕
4. OCR 失败时回退到视觉模型
5. 调用 AI 生成回复
6. 调用 TTS 播放回复

默认设计目标是“先跑起来，再替换真实能力”。

## 这次已经完成的改动

- 建立了项目代码结构和运行入口
- 实现了配置加载、日志和异步主循环
- 实现了截图模块和弹幕区域裁剪
- 实现了 OCR 模块，支持 EasyOCR / pytesseract
- 实现了视觉模型 fallback，使用 OpenAI-compatible API
- 实现了 AI Agent，动态读取 `agent_config/SOUL.md`、`IDENTITY.md`、`USER.md`
- 实现了 TTS 模块，支持 `console`、`openai`、`edge`、`pyttsx3`
- 默认改成每次启动时手动框选弹幕区域，不再依赖 `.env` 中的固定坐标
- 明确补齐了 macOS 支持说明和启动诊断

## 关键文件

- 入口：[src/main.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/main.py)
- 配置：[src/config.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/config.py)
- 截图：[src/screenshot.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/screenshot.py)
- 区域框选：[src/region_selector.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/region_selector.py)
- OCR：[src/ocr_module.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/ocr_module.py)
- 视觉回退：[src/vision_module.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/vision_module.py)
- AI Agent：[src/ai_agent.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/ai_agent.py)
- TTS：[src/tts_module.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/tts_module.py)
- 平台检查：[src/platform_support.py](/Users/luyi/Code/GithubCode/livesoul-agent/src/platform_support.py)

## 当前配置约定

`.env.example` 已清理，不再暴露 `BARRAGE_REGION_X/Y/W/H` 给新用户。

当前推荐配置方式：

- `AUTO_SELECT_REGION=true`
- 每次启动程序后手动框选弹幕区域
- `SCREENSHOT_INTERVAL` 控制截图频率
- `OCR_CONFIDENCE_THRESHOLD` 控制 OCR 回退阈值
- `TTS_PROVIDER` 控制 TTS 方案

保留了对旧坐标配置的代码兼容，但不再推荐继续使用。

## 平台支持说明

### macOS

已明确支持，但要注意：

- 首次运行前需要开启 `Screen Recording`
- 如果框选器不能弹出，通常是 `tkinter` 不可用
- 如果用 `pytesseract`，需要本机安装 `tesseract`
- TTS 播放默认可走 `afplay`

### Windows

已明确支持，但要注意：

- OBS 或投屏窗口不能最小化
- 截图区域每次启动需要重新手动框选

## 已做过的验证

- `python3 -m compileall src` 通过
- `from src.main import LiveSoulRuntime` 导入通过
- 截图链路做过本地 smoke test，能生成裁剪后的图片文件

## 已知问题 / 还没做的事

- 还没有真正做“窗口级捕获”，当前仍是整屏截图后裁剪
- 区域框选器目前是基础版本，还可以继续增强交互体验
- OCR 目前偏原型，未做更细的去重、分行归并和聊天气泡过滤
- TTS 播放还没接 OBS 音频路由，只是系统播放
- 没有自动化测试
- 还没有打包成桌面应用

## 下次建议优先继续的方向

1. 增强区域框选器
   - 显示实时坐标和宽高
   - 支持重选
   - 支持多显示器更稳定的选择体验

2. 优化截图能力
   - 支持指定窗口捕获
   - 对 OBS / 投屏窗口做自动定位

3. 优化弹幕识别
   - 做文本去重和节流
   - 提升 OCR 预处理
   - 对连续弹幕做批处理

4. 优化语音链路
   - 支持更稳定的本地播放
   - 接入 OBS 可直接使用的音频输出方式

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
