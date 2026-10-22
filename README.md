# V.E.C.T.O.R.

A voice assistant for Windows. Say "Hey Vector" and talk to it.

## Features

- Wake phrase "Hey Vector", detected by local speech recognition
- Offline speech-to-text with faster-whisper
- Works with any OpenAI-compatible model: Gemini, Groq, or a local Ollama model as fallback
- Tool calling: timers, open apps, web and YouTube search, volume, media keys, system status, persistent memory
- Spoken replies through the built-in Windows voice
- Does not listen to itself when speaking through speakers

## Structure

| File | Purpose |
|---|---|
| `vector.py` | Entry point and main loop |
| `ear.py` | Microphone input, speech detection, transcription |
| `brain.py` | Model client, tool-calling loop, provider fallback |
| `tools.py` | Actions the assistant can perform |
| `voice.py` | Text-to-speech |
| `config.py` | Settings |
