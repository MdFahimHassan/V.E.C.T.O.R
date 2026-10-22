import queue
import threading
import time


class Voice:
    def __init__(self, rate: int = 185):
        self.rate = rate
        self.last_finished = 0.0
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._pending = 0
        self._lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True).start()

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._pending > 0

    def speak(self, text: str, wait: bool = True) -> None:
        text = (text or "").strip()
        if not text:
            return
        print(f"[VECTOR] {text}")
        with self._lock:
            self._pending += 1
        self._queue.put(text)
        if wait:
            self._queue.join()

    def _worker(self) -> None:
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass

        while True:
            text = self._queue.get()
            try:
                import pyttsx3
                # a fresh engine per utterance avoids pyttsx3 hanging when reused across threads
                engine = pyttsx3.init()
                engine.setProperty("rate", self.rate)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"[Voice error] {e}")
            finally:
                with self._lock:
                    self._pending -= 1
                self.last_finished = time.monotonic()
                self._queue.task_done()
