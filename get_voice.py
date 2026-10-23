"""Download the Jarvis voice for Piper into ./voices (about 64 MB, run once).

    python get_voice.py            # medium quality (fast, recommended)
    python get_voice.py high       # higher quality, slower

Source: https://huggingface.co/jgkawell/jarvis (MIT licensed community voice).
"""
import sys
import urllib.request
from pathlib import Path

quality = sys.argv[1] if len(sys.argv) > 1 else "medium"
base = f"https://huggingface.co/jgkawell/jarvis/resolve/main/en/en_GB/jarvis/{quality}"
out = Path(__file__).parent / "voices"
out.mkdir(exist_ok=True)

for name in (f"jarvis-{quality}.onnx", f"jarvis-{quality}.onnx.json"):
    target = out / name
    if target.exists():
        print(f"already have {name}")
        continue
    print(f"downloading {name} ...")
    urllib.request.urlretrieve(f"{base}/{name}", target)

print(f"\nDone. Set PIPER_MODEL=voices/jarvis-{quality}.onnx in your .env (or edit config.py).")