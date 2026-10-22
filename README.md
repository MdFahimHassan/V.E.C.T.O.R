# V.E.C.T.O.R.

A hands-free voice assistant for Windows, inspired by J.A.R.V.I.S. Say **"Hey Vector"**, then talk to it.

Speech is transcribed locally with Whisper. An LLM decides what to do and calls Python tools to act on your laptop, then answers out loud.

## Features

- **Wake phrase:** "Hey Vector", detected from locally transcribed speech. "Hey Vector, set a timer for five minutes" works in one sentence.
- **Follow-ups:** after a reply, keep talking for a few seconds without repeating the wake phrase.
- **Local speech-to-text:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) runs on your CPU, with no upload and no rate limit.
- **Any OpenAI-compatible model:** Gemini by default, Groq or any other compatible provider through `.env`, with an optional local [Ollama](https://ollama.com) model as an automatic fallback.
- **Tool calling:** timers, open apps, open websites, Google and YouTube search, volume, media keys, battery and CPU status, persistent memory.
- **Works through speakers:** it ignores audio while speaking, so it does not hear itself.

## How it works

```
 microphone -> Ear (voice detection + Whisper) -> Brain (LLM + tool calls) -> Voice -> speakers
                                                          |
                                                    Tools (tools.py)
```

| File | Purpose |
|---|---|
| `vector.py` | Entry point and main loop |
| `ear.py` | Microphone input, speech detection, transcription |
| `brain.py` | Model client, tool-calling loop, provider fallback |
| `tools.py` | Actions the assistant can perform |
| `voice.py` | Text-to-speech and speaking state |
| `config.py` | Settings |

## Quick start

Requires Windows and Python 3.11 or 3.12.

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add your API key to `.env`, then run:

```
python vector.py
```

The first run downloads the Whisper model. Stay quiet while it calibrates to your room.

| Flag | Effect |
|---|---|
| `--text` | Type commands instead of speaking |
| `--no-wake` | Treat all speech as commands |
| `--list-devices` | List audio input devices |

## Example commands

- "Hey Vector, what time is it?"
- "Hey Vector, set a timer for ten minutes for the pasta."
- "Hey Vector, open Chrome."
- "Hey Vector, search YouTube for lo-fi music."
- "Hey Vector, turn the volume down."
- "Hey Vector, how's my battery?"
- "Hey Vector, remember that my exam is on Friday."

## Configuration

Secrets and model choices live in `.env` (see `.env.example`). Behaviour is tuned in `config.py`.

| Setting | Meaning |
|---|---|
| `BRAIN_BASE_URL`, `BRAIN_API_KEY`, `BRAIN_MODEL` | Primary model provider |
| `FALLBACK_*` | Local fallback model (Ollama) |
| `WHISPER_MODEL` | `base.en` is faster, `small.en` is more accurate |
| `WAKE_WORDS` | Spellings accepted as the wake word |
| `FOLLOW_UP_SECONDS` | How long it keeps listening after a reply |
| `MIN_SPEECH_RMS` | Lower it if the microphone is not detected as speech |
| `END_SILENCE_SECONDS` | Pause length that ends a sentence |
| `MIC_DEVICE` | Pick a specific microphone |

## Adding a tool

Write a function in `tools.py` and decorate it with `@tool`. The type hints and docstring are what the model reads.

```python
@tool
def lock_computer() -> str:
    """Lock the Windows session. Use when the user says they are leaving."""
    import ctypes
    ctypes.windll.user32.LockWorkStation()
    return "Locked."
```

There is deliberately no "run any command" tool. `open_app` only launches programs listed in `APPS`.

## Privacy

Audio never leaves your machine. The transcribed text and tool results are sent to the model provider you configure, and free API tiers may use submitted content to improve their models, so check your provider's terms. Do not dictate secrets.

## Limitations

- Windows only (voice, volume, media keys and app launching use Windows features).
- While idle, it transcribes speech it hears locally to listen for the wake phrase, which uses some CPU. A dedicated wake-word model would reduce this.
- The built-in Windows voice is functional but robotic.
- Replies are not streamed, and you cannot interrupt it mid-sentence.

## Roadmap

- [ ] Weather and web-lookup tools
- [ ] Natural offline voice (Piper)
- [ ] Streaming replies
- [ ] Interrupt with "stop"
- [ ] Dedicated "Hey Vector" wake-word model
- [ ] More tools: screenshots, clipboard, Spotify, project launcher