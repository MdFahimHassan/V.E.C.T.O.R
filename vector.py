import argparse
import re
import time

import config
import tools
from brain import Brain
from ui import Hub, open_orb
from voice import Voice

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
        voice.speak(f"Yes, {config.USER_TITLE}?")
        hub.emit(state="listening", text=None)
        audio = ear.record_utterance(max_wait=config.WAIT_FOR_SPEECH_SECONDS)
        return ear.transcribe(audio) if audio is not None else None
    if heard or in_follow_up or not require_wake:
        return command
    print(f"[ignored] {text}")
    return None


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
    brain = Brain()

    ear = None
    if not args.text:
        from ear import Ear
        ear = Ear(voice)
        ear.calibrate()

    hub.emit(state="speaking")
    voice.speak(f"Vector online, {config.USER_TITLE}.")
    hub.emit(state="idle")
    follow_up_until = 0.0

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
                voice.speak(f"Goodbye, {config.USER_TITLE}.")
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