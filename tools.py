from __future__ import annotations

import inspect
import json
import os
import subprocess
import threading
import typing
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Literal

import config

IS_WINDOWS = os.name == "nt"
MEMORY_FILE = Path(__file__).parent / "memory.json"

REGISTRY: dict[str, dict] = {}
_PY_TO_JSON = {int: "integer", float: "number", str: "string", bool: "boolean"}
_voice = None
_timers: list[threading.Timer] = []


def init(voice) -> None:
    global _voice
    _voice = voice


def tool(fn):
    """Register a function so the model can call it. The docstring is the model's description."""
    hints = typing.get_type_hints(fn)
    properties, required = {}, []
    for name, param in inspect.signature(fn).parameters.items():
        hint = hints.get(name, str)
        if typing.get_origin(hint) is Literal:
            properties[name] = {"type": "string", "enum": list(typing.get_args(hint))}
        else:
            properties[name] = {"type": _PY_TO_JSON.get(hint, "string")}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    REGISTRY[fn.__name__] = {
        "fn": fn,
        "schema": {
            "type": "function",
            "function": {
                "name": fn.__name__,
                "description": inspect.cleandoc(fn.__doc__ or ""),
                "parameters": {"type": "object", "properties": properties, "required": required},
            },
        },
    }
    return fn


def schemas() -> list[dict]:
    return [entry["schema"] for entry in REGISTRY.values()]


def run_tool(name: str, raw_arguments: str) -> str:
    entry = REGISTRY.get(name)
    if entry is None:
        return f"Error: there is no tool called '{name}'."
    try:
        args = json.loads(raw_arguments) if raw_arguments else {}
        if not isinstance(args, dict):
            args = {}
        return str(entry["fn"](**args))
    except TypeError as e:
        return f"Error: bad arguments for {name}: {e}"
    except Exception as e:
        return f"Error: {name} failed: {e}"


def _human_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h} hour{'s' if h != 1 else ''}")
    if m:
        parts.append(f"{m} minute{'s' if m != 1 else ''}")
    if s:
        parts.append(f"{s} second{'s' if s != 1 else ''}")
    return " ".join(parts)


def _press_key(vk_code: int, times: int = 1) -> None:
    import ctypes
    for _ in range(times):
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)


VK_VOLUME_MUTE, VK_VOLUME_DOWN, VK_VOLUME_UP = 0xAD, 0xAE, 0xAF
VK_MEDIA_NEXT, VK_MEDIA_PREV, VK_MEDIA_PLAY_PAUSE = 0xB0, 0xB1, 0xB3


@tool
def set_timer(seconds: int, label: str = "timer") -> str:
    """Start a countdown timer or reminder. `seconds` is the total duration in seconds
    (convert minutes and hours yourself). `label` is what to announce when it finishes."""
    seconds = int(seconds)
    if not 1 <= seconds <= 86400:
        return "A timer must be between 1 second and 24 hours."

    def ring():
        if _voice:
            _voice.speak(f"Your {label} is done, {config.USER_TITLE}.", wait=False)

    t = threading.Timer(seconds, ring)
    t.daemon = True
    t.start()
    _timers.append(t)
    return f"Timer '{label}' set for {_human_duration(seconds)}."


@tool
def cancel_timers() -> str:
    """Cancel every running timer and reminder."""
    count = sum(1 for t in _timers if t.is_alive())
    for t in _timers:
        t.cancel()
    _timers.clear()
    return f"Cancelled {count} timer(s)."


APPS = {
    "notepad": "notepad",
    "calculator": "calc",
    "chrome": "chrome",
    "edge": "msedge",
    "file explorer": "explorer",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "vs code": "code",
    "spotify": "spotify",
    "command prompt": "cmd",
    "paint": "mspaint",
}


@tool
def open_app(name: str) -> str:
    """Open an application by its common name, for example 'chrome', 'notepad', 'calculator',
    'vs code' or 'spotify'."""
    if not IS_WINDOWS:
        return "Opening apps only works on Windows."
    wanted = name.lower().strip()
    match = wanted if wanted in APPS else next((k for k in APPS if k in wanted or wanted in k), None)
    if not match:
        return f"I don't know an app called '{name}'. Known apps: {', '.join(APPS)}."
    subprocess.Popen(["cmd", "/c", "start", "", APPS[match]])
    return f"Opened {match}."


@tool
def open_website(url: str) -> str:
    """Open a website address in the default browser, for example 'github.com'."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}."


@tool
def search_web(query: str, site: Literal["google", "youtube"] = "google") -> str:
    """Search Google or YouTube in the browser. Use site='youtube' to find videos and music."""
    q = urllib.parse.quote_plus(query)
    base = "https://www.youtube.com/results?search_query=" if site == "youtube" else "https://www.google.com/search?q="
    webbrowser.open(base + q)
    return f"Searching {site} for '{query}'."


@tool
def change_volume(direction: Literal["up", "down", "mute"], percent: int = 10) -> str:
    """Raise or lower the laptop volume by a number of percent, or toggle mute."""
    if not IS_WINDOWS:
        return "Volume control only works on Windows."
    if direction == "mute":
        _press_key(VK_VOLUME_MUTE)
        return "Toggled mute."
    presses = max(1, min(50, round(int(percent) / 2)))
    _press_key(VK_VOLUME_UP if direction == "up" else VK_VOLUME_DOWN, presses)
    return f"Volume turned {direction} by about {presses * 2} percent."


@tool
def set_volume(percent: int) -> str:
    """Set the laptop volume to an exact level from 0 to 100 percent."""
    if not IS_WINDOWS:
        return "Volume control only works on Windows."
    percent = max(0, min(100, int(percent)))
    _press_key(VK_VOLUME_DOWN, 50)
    _press_key(VK_VOLUME_UP, round(percent / 2))
    return f"Volume set to about {percent} percent."


@tool
def media_control(action: Literal["play_pause", "next", "previous"]) -> str:
    """Control the music or video that is playing: pause or resume, next track, previous track."""
    if not IS_WINDOWS:
        return "Media control only works on Windows."
    key = {"play_pause": VK_MEDIA_PLAY_PAUSE, "next": VK_MEDIA_NEXT, "previous": VK_MEDIA_PREV}[action]
    _press_key(key)
    return f"Sent {action}."


@tool
def get_system_status() -> str:
    """Report the laptop's battery level, charging state, CPU load and RAM usage."""
    import psutil
    battery = psutil.sensors_battery()
    parts = []
    if battery:
        state = "charging" if battery.power_plugged else "on battery"
        parts.append(f"Battery {battery.percent:.0f} percent, {state}.")
    parts.append(f"CPU {psutil.cpu_percent(interval=0.5):.0f} percent busy.")
    parts.append(f"RAM {psutil.virtual_memory().percent:.0f} percent used.")
    return " ".join(parts)


def load_facts() -> list[str]:
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_facts(facts: list[str]) -> None:
    MEMORY_FILE.write_text(json.dumps(facts, indent=2), encoding="utf-8")


@tool
def remember_fact(fact: str) -> str:
    """Save a lasting fact about the user or their preferences, for example 'likes lo-fi music'.
    Only use when the user asks you to remember something."""
    facts = load_facts()
    if fact not in facts:
        facts.append(fact)
    _save_facts(facts[-50:])
    return f"Remembered: {fact}"


@tool
def forget_fact(keyword: str) -> str:
    """Delete saved facts that contain the given keyword."""
    facts = load_facts()
    kept = [f for f in facts if keyword.lower() not in f.lower()]
    _save_facts(kept)
    return f"Forgot {len(facts) - len(kept)} fact(s)."
