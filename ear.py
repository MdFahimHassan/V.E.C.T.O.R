import queue
import time
from collections import deque

import numpy as np
import sounddevice as sd

import config


class Ear:
    def __init__(self, voice):
        self.voice = voice
        self.frames: "queue.Queue[np.ndarray]" = queue.Queue()
        self.speech_threshold = config.MIN_SPEECH_RMS

        print("[Ear] Loading speech recognition...")
        from faster_whisper import WhisperModel
        self.whisper = WhisperModel(config.WHISPER_MODEL, device=config.WHISPER_DEVICE,
                                    compute_type=config.WHISPER_COMPUTE, cpu_threads=8)

        self.stream = sd.InputStream(samplerate=config.SAMPLE_RATE, channels=1, dtype="int16",
                                     blocksize=config.FRAME_SIZE, device=config.MIC_DEVICE,
                                     callback=self._on_audio)
        self.stream.start()

    def _on_audio(self, indata, frames, time_info, status):
        if self._should_ignore():
            return
        self.frames.put(indata[:, 0].copy())

    def _should_ignore(self) -> bool:
        return (self.voice.is_speaking
                or time.monotonic() < self.voice.last_finished + config.ECHO_TAIL_SECONDS)

    def _flush(self) -> None:
        while True:
            try:
                self.frames.get_nowait()
            except queue.Empty:
                return

    @staticmethod
    def _rms(frame: np.ndarray) -> float:
        return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))

    def calibrate(self) -> None:
        print(f"[Ear] Calibrating, stay quiet for {config.CALIBRATION_SECONDS:.1f}s...")
        self._flush()
        levels = []
        end = time.monotonic() + config.CALIBRATION_SECONDS
        while time.monotonic() < end:
            try:
                levels.append(self._rms(self.frames.get(timeout=0.5)))
            except queue.Empty:
                pass
        noise = float(np.median(levels)) if levels else 0.0
        self.speech_threshold = max(noise * config.NOISE_MULTIPLIER, config.MIN_SPEECH_RMS)
        print(f"[Ear] Room noise {noise:.0f}, speech threshold {self.speech_threshold:.0f}")

    def record_utterance(self, max_wait: float = config.WAIT_FOR_SPEECH_SECONDS):
        """Record one sentence. Returns float32 audio, or None if nobody spoke within max_wait."""
        self._flush()
        frame_seconds = config.FRAME_SIZE / config.SAMPLE_RATE
        end_silence_frames = int(config.END_SILENCE_SECONDS / frame_seconds)
        preroll = deque(maxlen=5)
        chunks, started, silent_frames = [], False, 0
        t0 = time.monotonic()

        while True:
            try:
                frame = self.frames.get(timeout=0.5)
            except queue.Empty:
                if not started and time.monotonic() - t0 > max_wait:
                    return None
                continue

            elapsed = time.monotonic() - t0
            loud = self._rms(frame) > self.speech_threshold
            if not started:
                preroll.append(frame)
                if loud:
                    started = True
                    chunks = list(preroll)
                elif elapsed > max_wait:
                    return None
                continue

            chunks.append(frame)
            silent_frames = 0 if loud else silent_frames + 1
            if silent_frames >= end_silence_frames or elapsed > config.MAX_UTTERANCE_SECONDS:
                break

        return np.concatenate(chunks).astype(np.float32) / 32768.0

    def transcribe(self, audio: np.ndarray) -> str:
        started = time.monotonic()
        segments, _ = self.whisper.transcribe(
            audio, language="en", beam_size=1, vad_filter=True,
            initial_prompt=config.WHISPER_HINT, condition_on_previous_text=False,
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        print(f"[timing] speech-to-text {time.monotonic() - started:.1f}s")
        return text
