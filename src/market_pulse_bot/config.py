from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID: str | None = os.getenv("TELEGRAM_CHANNEL_NAME") or os.getenv("TELEGRAM_CHAT_ID")
