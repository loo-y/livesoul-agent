# 🎯 System Design（Python 原生版）

## 1️⃣ 高级模块划分

| 模块           | 功能                     | 技术选型                                                                     |
| ------------ | ---------------------- | ------------------------------------------------------------------------ |
| **投屏捕获**     | 获取 iPhone 直播画面         | LetsView / ApowerMirror / OBS窗口捕获                                        |
| **截图模块**     | 定时抓取屏幕或窗口帧             | Python: `mss` 或 `PIL`                                                    |
| **弹幕识别模块**   | OCR / 视觉模型识别弹幕         | Tesseract / EasyOCR / OpenAI GPT-4V / PaddleOCR                          |
| **AI Agent** | 解析弹幕并生成带灵魂的回答          | OpenAI GPT / LLaMA / 本地大模型；加载 SOUL.md / IDENTITY.md / USER.md            |
| **SOUL管理**   | 定义 AI 人格、身份、用户偏好       | SOUL.md / IDENTITY.md / USER.md 文件，动态加载                                  |
| **TTS模块**    | AI 回复语音化输出             | OpenAI TTS / Edge TTS / Coqui TTS；可通过 .env 配置 API Key / Model / Base URL |
| **配置管理**     | API Key、模型、阈值、TTS参数等   | `.env` 文件 + `python-dotenv`                                              |
| **异步队列**     | 弹幕处理、OCR/视觉调用、TTS输出异步化 | Python asyncio / queue / threading                                       |

---

## 2️⃣ 数据流

```text
iPhone直播画面
       ↓ (AirPlay/USB)
Windows 投屏窗口
       ↓ (OBS窗口捕获或截图)
截图模块 → 弹幕区域裁剪
       ↓
OCR识别 (OCR_CONFIDENCE_THRESHOLD)
   成功? ──> 弹幕文本
   否 ──> 视觉模型识别 (VISION_API_KEY / MODEL_NAME / BASE_URL)
       ↓
AI Agent (加载SOUL.md/IDENTITY.md/USER.md)
       ↓
生成回复文本
       ↓
TTS模块 (TTS_API_KEY / MODEL_NAME / BASE_URL)
       ↓
播放音频 (OBS Audio / 扬声器)
```

---

## 3️⃣ 弹幕识别策略

1. **优先OCR**：

   * 截图弹幕区域 → OCR识别 → 如果置信度 > threshold → 返回文本
2. **OCR失败或低置信度**：

   * 调用视觉模型（GPT-4V等） → 图片识别 → 返回文本
3. **文本交给 AI Agent**：

   * 使用 SOUL.md/IDENTITY.md/USER.md 指定风格和行为

---

## 4️⃣ SOUL/IDENTITY/USER 文件示例

```text
# SOUL.md
你是一个幽默风趣、积极正向、乐于互动的直播 AI 助手。

# IDENTITY.md
姓名: LiveSoul
角色: 直播间 AI 助手
目标: 提升观众互动，回答弹幕问题，鼓励互动

# USER.md
目标观众: 喜欢轻松幽默
禁忌: 不回答违法或敏感话题
```

* 每次生成 AI 回复都把这些内容注入 **system prompt**。

---

## 5️⃣ 配置管理 (.env)

```text
OCR_CONFIDENCE_THRESHOLD=0.8
VISION_API_KEY=sk-xxxx
VISION_MODEL_NAME=gpt-4v-mini
VISION_API_BASE=https://api.openai.com/v1

TTS_API_KEY=sk-xxxx
TTS_MODEL_NAME=gpt-4o-mini-tts
TTS_API_BASE=https://api.openai.com/v1

SCREENSHOT_INTERVAL=0.5  # 每0.5秒截图
BARRAGE_REGION_X=1000
BARRAGE_REGION_Y=500
BARRAGE_REGION_W=400
BARRAGE_REGION_H=300
```

---

## 6️⃣ 弹性 &扩展性

* 支持 **OCR失败 fallback 视觉模型**
* 弹幕识别 & AI处理 & TTS 输出 **异步化**
* 灵魂可随时修改 → SOUL.md/IDENTITY.md/USER.md 文件
* 可切换 TTS / AI 模型
* 可通过 OBS 控制输出音频/弹幕显示

---