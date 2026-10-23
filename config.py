import os

from dotenv import load_dotenv

load_dotenv()

# ---- brains, tried in this order; a provider that is down or out of quota is skipped for a while ----
# Change the order in .env, e.g. BRAIN_ORDER=gemini,groq,ollama
BRAIN_ORDER = [p.strip() for p in os.getenv("BRAIN_ORDER", "ollama,gemini,groq").split(",") if p.strip()]

PROVIDERS = {
    # local, free, no daily limit (needs Ollama running: ollama pull qwen2.5:3b)
    "ollama": {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "api_key": "ollama",
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        "timeout": 60,  # the first reply after a pause has to load the model
    },
    # smartest of the three, but the free API tier is small (about 20 requests/day)
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GEMINI_API_KEY") or os.getenv("BRAIN_API_KEY", ""),
        "model": os.getenv("GEMINI_MODEL") or os.getenv("BRAIN_MODEL", "gemini-3.5-flash"),
        "timeout": 20,
    },
    # free key from console.groq.com, fast, much larger free allowance
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "timeout": 20,
    },
}

QUOTA_COOLDOWN_SECONDS = 1800   # skip a provider this long after a rate-limit error
OFFLINE_COOLDOWN_SECONDS = 60   # ...and this long after a connection error

USER_TITLE = "sir"
MAX_TOOL_ROUNDS = 4
HISTORY_TURNS = 8
REQUEST_TIMEOUT = 20

WAKE_WORDS = ("vector", "vektor", "vecter", "hector", "victor")
FOLLOW_UP_SECONDS = 6

SAMPLE_RATE = 16000
FRAME_SIZE = 1280
MIC_DEVICE = None
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small.en")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = "float16" if WHISPER_DEVICE == "cuda" else "int8"
WHISPER_HINT = "Hey Vector, set a timer. Hey Vector, open Chrome. Volume, Spotify, YouTube."

CALIBRATION_SECONDS = 1.5
NOISE_MULTIPLIER = 3.0
MIN_SPEECH_RMS = 150
END_SILENCE_SECONDS = 0.9
MAX_UTTERANCE_SECONDS = 15
WAIT_FOR_SPEECH_SECONDS = 5
ECHO_TAIL_SECONDS = 0.5

# ---- voice (Piper) ----
PIPER_MODEL = os.getenv("PIPER_MODEL", "voices/jarvis-medium.onnx")
PIPER_LENGTH_SCALE = float(os.getenv("PIPER_LENGTH_SCALE", "1.0"))  # >1 slower, <1 faster
WINDOWS_TTS_RATE = 1  # fallback voice speed, -10..10

# ---- orb interface ----
UI_PORT = 8765
UI_FULLSCREEN = True   # True = orb fills the screen, centred; False = small floating window
UI_SIZE = 420          # window size when UI_FULLSCREEN is False
UI_X = None            # window position on screen; None = let the OS choose
UI_Y = None
UI_AUTO_HIDE = True    # hide the orb when idle, pop it up on "Hey Vector" (False = always visible)
UI_HIDE_AFTER = 6.0    # seconds of idle before it tucks away