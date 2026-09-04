import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Grok (xAI) sozlamalari
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_BASE_URL = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")
AI_MODEL = os.getenv("AI_MODEL", "grok-4-fast")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN topilmadi! .env faylida TELEGRAM_BOT_TOKEN ni belgilang."
    )

if not GROK_API_KEY:
    raise RuntimeError(
        "GROK_API_KEY topilmadi! .env faylida GROK_API_KEY ni belgilang."
    )
