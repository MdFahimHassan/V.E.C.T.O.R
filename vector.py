import argparse
import json
import re
import threading
import time
from datetime import date, datetime
from pathlib import Path

import config
import lines
import tools
from brain import Brain
from ui import Hub, open_orb
from voice import Voice

STATE_FILE = Path(__file__).parent / "state.json"
EXIT_PHRASES = {"exit", "quit", "goodbye", "goodbye vector", "shut down", "shut down vector", "go to sleep"}
WAKE_PATTERN = re.compile(r"^\W*(?:(?:hey|hi|hello|okay|ok)\W+)?(\w+)\W*(.*)$", re.IGNORECASE | re.DOTALL)


def is_exit(text: str) -> bool:
    return re.sub(r"[^a-z ]", "", text.lower()).strip() in EXIT_PHRASES


def split_wake_word(text: str) -> tuple[bool, str]:
    match = WAKE_PATTERN.match(text)
    if match and match.group(1).lower() in config.WAKE_WORDS:
        return True, match.group(2).strip()
    return False, text


def next_command(ear, voice, hub, follow_up_until: float, require_wake: bool):
    now = time.monotonic()
    in_follow_up = now < follow_up_until
    audio = ear.record_utterance(max_wait=(follow_up_until - now) if in_follow_up else float("inf"))
    if audio is None:
        return None

    text = ear.transcribe(audio)
    if not text:
        return None

    heard, command = split_wake_word(text)
    if heard and not command:
        hub.emit(state="listening")
        voice.speak(lines.pick("wake"))
        hub.emit(state="listening", text=None)
        audio = ear.record_utterance(max_wait=config.WAIT_FOR_SPEECH_SECONDS)
        return ear.transcribe(audio) if audio is not None else None
    if heard or in_follow_up or not require_wake:
        return command
    print(f"[ignored] {text}")
    return None


def first_launch_today() -> bool:
    """True the first time Vector starts on a given date (remembered in state.json)."""
    today = date.today().isoformat()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    first = data.get("last_launch") != today
    data["last_launch"] = today
    try:
        STATE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass
    return first


def monitor(voice, hub) -> None:
    """Background watcher: low battery, late night and break reminders, said only when idle."""
    started = time.monotonic()
    next_break = config.BREAK_REMINDER_MINUTES * 60
    late_night_done = False
    battery_warned = False
    while True:
        time.sleep(30)
        if hub.state in ("thinking", "speaking") or voice.is_speaking:
            continue

        try:
            import psutil
            battery = psutil.sensors_battery()
        except Exception:
            battery = None
        if battery:
            if battery.power_plugged or battery.percent > config.LOW_BATTERY_PERCENT + 10:
                battery_warned = False
            elif battery.percent <= config.LOW_BATTERY_PERCENT and not battery_warned:
                battery_warned = True
                voice.speak(lines.pick("low_battery", percent=round(battery.percent)), wait=False)
                continue

        hour = datetime.now().hour
        if (not late_night_done
                and config.LATE_NIGHT_START_HOUR <= hour < config.LATE_NIGHT_END_HOUR):
            late_night_done = True
            voice.speak(lines.pick("late_night", hour=lines.hour_phrase(hour)), wait=False)
            continue

        elapsed = time.monotonic() - started
        if elapsed >= next_break:
            next_break += config.BREAK_REMINDER_MINUTES * 60
            voice.speak(lines.pick("break_nudge", hours=lines.duration_phrase(elapsed)), wait=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="V.E.C.T.O.R. voice assistant")
    parser.add_argument("--text", action="store_true", help="type commands instead of speaking")
    parser.add_argument("--no-wake", action="store_true", help="treat all speech as commands")
    parser.add_argument("--list-devices", action="store_true", help="list audio devices and exit")
    parser.add_argument("--ui", action="store_true", help="show the animated orb")
    args = parser.parse_args()

    if args.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        return

    hub = Hub()
    if args.ui:
        hub.start_server()
        open_orb(hub, lambda: run(args, hub))  # returns when the window is closed
    else:
        run(args, hub)


def run(args, hub: Hub) -> None:
    voice = Voice(hub)
    tools.init(voice)
    brain = Brain(hub)

    ear = None
    if not args.text:
        from ear import Ear
        ear = Ear(voice)
        ear.calibrate()

    hub.emit(state="speaking")
    voice.speak(lines.startup_line(first_launch_today()))
    hub.emit(state="idle")
    follow_up_until = 0.0
    if config.PROACTIVE_LINES:
        threading.Thread(target=monitor, args=(voice, hub), daemon=True).start()

    try:
        while True:
            if args.text:
                text = input("you> ").strip()
            else:
                text = next_command(ear, voice, hub, follow_up_until, require_wake=not args.no_wake)
                if text is None:
                    follow_up_until = 0.0
                    hub.emit(state="idle")
                    continue
            if not text:
                continue
            print(f"[YOU] {text}")
            hub.emit(state="thinking", text=text, who="you")

            if is_exit(text):
                voice.speak(lines.pick("shutdown"))
                break

            started = time.monotonic()
            reply = brain.ask(text)
            print(f"[timing] thinking {time.monotonic() - started:.1f}s")

            voice.speak(reply)
            follow_up_until = time.monotonic() + config.FOLLOW_UP_SECONDS
            hub.emit(state="listening")  # follow-up window is open
    except KeyboardInterrupt:
        print("\nBye.")
    finally:
        hub.emit(state="idle")
        if args.ui:
            import os
            os._exit(0)  # close the orb window with us


if __name__ == "__main__":
    main()