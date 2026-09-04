# AI Referat & Prezentatsiya Telegram Bot

Grok AI yordamida savollarga javob beradigan, referat (.docx) va
prezentatsiya (.pptx) tayyorlaydigan Telegram bot.

## Sozlash

1. `.env.example` dan nusxa olib `.env` yarating
2. `TELEGRAM_BOT_TOKEN` va `GROK_API_KEY` ni to'ldiring
3. `pip install -r requirements.txt`
4. `python bot.py`

## Render.com'da deploy qilish

Render'da "Background Worker" yarating, Environment Variables bo'limiga
`TELEGRAM_BOT_TOKEN`, `GROK_API_KEY`, `GROK_BASE_URL`, `AI_MODEL` ni kiriting.
Start command: `python bot.py`
