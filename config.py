import os

from dotenv import load_dotenv

load_dotenv()

BRAIN_BASE_URL = os.getenv("BRAIN_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
BRAIN_API_KEY = os.getenv("BRAIN_API_KEY") or os.getenv("GEMINI_API_KEY", "")
BRAIN_MODEL = os.getenv("BRAIN_MODEL", "gemini-3.5-flash")

FALLBACK_BASE_URL = os.getenv("FALLBACK_BASE_URL", "http://localhost:11434/v1")
FALLBACK_API_KEY = os.getenv("FALLBACK_API_KEY", "ollama")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "qwen2.5:3b")

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
