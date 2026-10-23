"""Orb interface plumbing.

Hub      - the rest of Vector calls hub.emit(state=..., level=..., text=...). Safe to call even
           when no UI is running (it just does nothing).
Server   - tiny local WebSocket server that pushes those events to orb.html.
open_orb - shows orb.html in its own frameless window (pywebview) or, failing that, a browser tab.

States: idle | listening | thinking | speaking
"""
import asyncio
import json
import threading
import webbrowser
from pathlib import Path

import config

ORB_FILE = Path(__file__).parent / "orb.html"


class Hub:
    def __init__(self):
        self._loop = None
        self._clients = set()
        self._last = {"state": "idle", "level": 0.0, "text": "", "who": ""}
        self.on_state = None  # optional callback, used to show/hide the window

    @property
    def state(self) -> str:
        return self._last["state"]

    # ---- called from anywhere in Vector ----
    def emit(self, **event) -> None:
        if "state" in event and self.on_state:
            try:
                self.on_state(event["state"])
            except Exception:
                pass
        self._last.update({k: v for k, v in event.items() if k != "text" or v is not None})
        if self._loop is None:
            return
        message = json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in event.items()})
        self._loop.call_soon_threadsafe(self._broadcast, message)

    def _broadcast(self, message: str) -> None:
        for ws in list(self._clients):
            asyncio.ensure_future(self._send(ws, message))

    @staticmethod
    async def _send(ws, message: str) -> None:
        try:
            await ws.send(message)
        except Exception:
            pass

    # ---- server ----
    def start_server(self) -> None:
        ready = threading.Event()
        threading.Thread(target=self._run, args=(ready,), daemon=True).start()
        ready.wait(timeout=5)

    def _run(self, ready: threading.Event) -> None:
        from websockets.asyncio.server import serve

        async def handler(ws):
            self._clients.add(ws)
            try:
                await ws.send(json.dumps(self._last))
                async for _ in ws:
                    pass
            finally:
                self._clients.discard(ws)

        async def main():
            self._loop = asyncio.get_running_loop()
            async with serve(handler, "127.0.0.1", config.UI_PORT):
                ready.set()
                await asyncio.Future()

        asyncio.run(main())


def open_orb(hub: Hub, run_in_background) -> None:
    """Show the orb. `run_in_background` is Vector's main loop: pywebview insists on owning the
    main thread, so the assistant runs in a worker thread while the window runs here."""
    url = ORB_FILE.as_uri() + f"?port={config.UI_PORT}"
    try:
        import webview
    except ImportError:
        print("[UI] pywebview not installed, opening the orb in your browser instead "
              "(pip install pywebview for a proper floating window).")
        webbrowser.open(url)
        run_in_background()
        return

    class Api:  # lets orb.html talk back to Python (Esc hides the orb)
        def hide(self):
            window.hide()

    # pywebview takes a plain file path (a ?query would be treated as part of the filename);
    # orb.html defaults to port 8765, which matches config.UI_PORT
    window = webview.create_window(
        "V.E.C.T.O.R.", str(ORB_FILE), js_api=Api(),
        fullscreen=config.UI_FULLSCREEN, width=config.UI_SIZE, height=config.UI_SIZE + 80,
        frameless=True, easy_drag=not config.UI_FULLSCREEN, on_top=True, background_color="#02050a",
        x=config.UI_X, y=config.UI_Y,
    )

    # pop up on activation, tuck away after a while idle
    hide_timer = {"t": None}

    def on_state(state):
        if hide_timer["t"]:
            hide_timer["t"].cancel()
            hide_timer["t"] = None
        if state == "idle":
            hide_timer["t"] = threading.Timer(config.UI_HIDE_AFTER, lambda: window.hide())
            hide_timer["t"].start()
        else:
            window.show()

    if config.UI_AUTO_HIDE:
        hub.on_state = on_state

    threading.Thread(target=run_in_background, daemon=True).start()
    webview.start()