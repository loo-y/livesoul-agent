# 📂 livesoul-agent 项目结构建议

```
livesoul-agent/
│
├── README.md                # 项目说明、整体介绍
├── SYSTEM_DESIGN.md         # 刚才给你的 system design（文字版架构说明）
├── DEVELOPER_PROMPT.md      # 给 Codex 的开发提示（Python开发需求）
├── DATA_FLOW_DIAGRAM.md     # 数据流图（ASCII或嵌入图片）
├── PROJECT_STRUCTURE.md     # 项目目录结构、模块划分说明
│
├── agent_config/            # AI Agent灵魂配置
│   ├── SOUL.md
│   ├── IDENTITY.md
│   └── USER.md
│
├── .env                     # 所有API Key /模型/参数配置
│
├── src/                     # Python源代码
│   ├── screenshot.py        # 截屏模块
│   ├── ocr_module.py        # OCR模块
│   ├── vision_module.py     # 视觉模型fallback模块
│   ├── ai_agent.py          # AI agent处理模块
│   ├── tts_module.py        # TTS模块
│   ├── config.py            # 读取.env配置
│   └── main.py              # 主运行脚本
│
└── requirements.txt         # Python依赖包列表
```
