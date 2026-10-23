"""Text-to-speech.

Primary: Piper (local neural voice, supports the community Jarvis model).
Fallback: Windows built-in speech through PowerShell, used if Piper or its voice file is missing.

The public interface is unchanged (speak / is_speaking / last_finished), so ear.py keeps
ignoring the mic while Vector talks. While speaking, Voice also reports the loudness of
what it is playing to the orb UI.
"""
import queue
import re
import subprocess
import threading
import time
from pathlib import Path

import numpy as np

import config

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class Voice:
    def __init__(self, hub=None):
        self.hub = hub
        self.last_finished = 0.0
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._pending = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._piper = self._load_piper()
        threading.Thread(target=self._worker, daemon=True).start()

    # ---------- setup ----------
    def _load_piper(self):
        model = Path(config.PIPER_MODEL)
        if not model.is_absolute():
            model = Path(__file__).parent / model
        if not model.exists():
            print(f"[Voice] Piper voice not found at {model}. Using Windows voice. "
                  f"Run: python get_voice.py")
            return None
        try:
            from piper import PiperVoice, SynthesisConfig
            voice = PiperVoice.load(str(model))
            self._syn_config = SynthesisConfig(length_scale=config.PIPER_LENGTH_SCALE)
            print(f"[Voice] Piper voice loaded: {model.name}")
            return voice
        except Exception as e:
            print(f"[Voice] Piper failed to load ({type(e).__name__}: {e}). Using Windows voice.")
            return None

    # ---------- public ----------
    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._pending > 0

    def speak(self, text: str, wait: bool = True) -> None:
        text = (text or "").strip()
        if not text:
            return
        print(f"[VECTOR] {text}")
        if self.hub:
            self.hub.emit(text=text, who="vector")
        with self._lock:
            self._pending += 1
        self._queue.put(text)
        if wait:
            self._queue.join()

    def stop(self) -> None:
        """Cut off speech immediately (used for the 'stop' command)."""
        self._stop.set()

    # ---------- worker ----------
    def _worker(self) -> None:
        while True:
            text = self._queue.get()
            self._stop.clear()
            before = self.hub.state if self.hub else "idle"
            if self.hub:
                self.hub.emit(state="speaking")
            try:
                if self._piper:
                    self._speak_piper(text)
                else:
                    self._speak_windows(text)
            except Exception as e:
                print(f"[Voice error] {type(e).__name__}: {e}")
            finally:
                with self._lock:
                    self._pending -= 1
                self.last_finished = time.monotonic()
                if self.hub:
                    # after a reply the follow-up window is open; after an alert, go back to sleep
                    back = "listening" if before in ("thinking", "speaking") else before
                    self.hub.emit(level=0.0, state=back)
                self._queue.task_done()

    def _speak_piper(self, text: str) -> None:
        import sounddevice as sd

        sentences = [s for s in _SENTENCE_SPLIT.split(text) if s.strip()]
        audio_q: "queue.Queue" = queue.Queue(maxsize=3)

        def synth():
            # synthesise the next sentence while the previous one is still playing
            for sentence in sentences:
                if self._stop.is_set():
                    break
                for chunk in self._piper.synthesize(sentence, syn_config=self._syn_config):
                    audio_q.put((chunk.audio_int16_array, chunk.sample_rate))
            audio_q.put(None)

        threading.Thread(target=synth, daemon=True).start()

        stream = None
        try:
            while not self._stop.is_set():
                item = audio_q.get()
                if item is None:
                    break
                samples, rate = item
                if stream is None:
                    stream = sd.OutputStream(samplerate=rate, channels=1, dtype="int16")
                    stream.start()
                block = int(rate * 0.04)  # 40 ms blocks -> 25 level updates per second
                for i in range(0, len(samples), block):
                    if self._stop.is_set():
                        break
                    part = samples[i:i + block]
                    stream.write(part)
                    if self.hub:
                        rms = float(np.sqrt(np.mean(part.astype(np.float32) ** 2))) / 32768.0
                        self.hub.emit(level=min(1.0, rms * 6))
        finally:
            if stream is not None:
                stream.stop()
                stream.close()

    def _speak_windows(self, text: str) -> None:
        # PowerShell's built-in synthesiser: slower to start, but unlike pyttsx3 it never goes
        # silent after the first sentence.
        safe = text.replace("'", "''")
        script = ("Add-Type -AssemblyName System.Speech; "
                  "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                  f"$s.Rate = {config.WINDOWS_TTS_RATE}; $s.Speak('{safe}')")
        # fake a gentle pulse so the orb still animates when we have no audio stream to measure
        stop_pulse = threading.Event()

        def pulse():
            t = 0.0
            while not stop_pulse.is_set():
                t += 0.12
                if self.hub:
                    self.hub.emit(level=0.35 + 0.25 * np.sin(t * 5) * np.sin(t * 1.7))
                time.sleep(0.04)

        threading.Thread(target=pulse, daemon=True).start()
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", script],
                           check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        finally:
            stop_pulse.set()