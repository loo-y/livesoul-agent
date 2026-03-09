# 💻 Developer Prompt（给 Codex）

```text
You are a Python developer. Generate a Python project that implements a live-stream AI agent with the following requirements:

1. Capture iPhone live-stream screen on Windows (via AirPlay or USB), either through OBS window capture or direct screenshot using Python.
2. Crop the screenshot to the live chat (barrage) area.
3. Recognize text from the barrage:
   - Use OCR (Tesseract or EasyOCR) first.
   - If OCR fails or confidence < threshold, fallback to a visual AI model (GPT-4V or other API) for text extraction.
4. Pass the recognized text to an AI agent that:
   - Loads and uses SOUL.md, IDENTITY.md, and USER.md to define personality, identity, and user preferences.
   - Generates a reply to the barrage according to the AI agent's "soul".
5. Convert the AI reply to speech (TTS) using an API (OpenAI TTS / Edge TTS / Coqui TTS), with configuration stored in `.env`.
6. Play the TTS audio output via system audio or OBS audio input for live listening.
7. The system should be configurable via `.env` for:
   - OCR threshold
   - Visual model API key, model name, base URL
   - TTS API key, model name, base URL
   - Screenshot interval and barrage area coordinates
8. Ensure the workflow is asynchronous and can handle continuous barrage in real-time.
9. Structure the project so SOUL.md, IDENTITY.md, USER.md, and .env can be modified at runtime.
10. Include clear modular design for easy extension (OCR module, visual model module, AI agent module, TTS module, screenshot module).

Please write Python code with proper module separation, comments explaining each part, and include an example main script to run the agent.
```
