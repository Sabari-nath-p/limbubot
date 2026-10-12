import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-opus-5-5")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-this-to-a-random-secret")

HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "15"))
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data.db"))
PORT = int(os.getenv("PORT", "8000"))

PROMPT_FILE = BASE_DIR / "prompt.txt"


def load_system_prompt() -> str:
    try:
        return PROMPT_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "You are a warm, caring AI companion."


if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in "
        "with the token BotFather gave you."
    )

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in "
        "with a key from https://openrouter.ai/keys."
    )
