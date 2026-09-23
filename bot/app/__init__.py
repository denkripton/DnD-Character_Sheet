import sys
from pathlib import Path

BOT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = BOT_ROOT.parent / "backend"
for entry in (BOT_ROOT, BACKEND_ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))