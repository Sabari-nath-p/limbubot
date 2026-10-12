# AI Companion Telegram Bot

A FastAPI app that runs an "AI girlfriend" style companion chatbot over Telegram,
powered by the Claude API. Features:

- **Personality from a file** — the system prompt lives in [`prompt.txt`](prompt.txt).
  Edit it any time (no restart needed) to change the personality.
- **Rolling memory** — keeps the last `HISTORY_LIMIT` messages (default 15) per
  chat as conversation context.
- **Automatic re-engagement** — if the user goes quiet after the bot's last
  reply, it automatically messages them again at increasing intervals:
  **1 hour → 3 hours → 10 hours → 1 week**, then stops sending automatic
  messages until the user writes in again (which resets the cycle).

## 1. Create the bot with BotFather

1. Open Telegram, search for **@BotFather**, and start a chat.
2. Send `/newbot` and follow the prompts (pick a name and a username ending in `bot`).
3. BotFather gives you a token like `123456789:AAExampleTokenGoesHere` — copy it.

## 2. Install & configure

```bash
cd ai-companion-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env:
#   TELEGRAM_BOT_TOKEN = the token from BotFather
#   OPENROUTER_API_KEY = your OpenRouter API key from https://openrouter.ai/keys
```

## 3. Run it

You have two options — pick whichever is easier for you.

### Option A — Long polling (simplest, no public URL needed)

Good for local testing or a bot that doesn't need to scale.

```bash
python poll.py
```

That's it — the bot is live. Leave `WEBHOOK_URL` empty in `.env` for this mode.

### Option B — FastAPI webhook (for a real deployment)

Telegram needs an HTTPS URL it can POST updates to. For local testing, expose
your machine with a tool like [ngrok](https://ngrok.com):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
# in another terminal:
ngrok http 8000
```

Set `WEBHOOK_URL` in `.env` to the ngrok HTTPS URL (e.g. `https://abcd1234.ngrok-free.app`,
no trailing slash) and restart the app. On startup it automatically calls Telegram's
`setWebhook` for you, pointing it at `<WEBHOOK_URL>/telegram/webhook`.

For a real deployment, point `WEBHOOK_URL` at your server's domain instead of ngrok.

> Only run **one** of the two modes at a time — `poll.py` calls `deleteWebhook`
> on startup, and the webhook mode will overwrite it again, so switching
> between them is safe, just don't run both at once.

## Customizing the personality

Edit [`prompt.txt`](prompt.txt) — it's read fresh on every message, so changes
apply immediately without restarting the app.

## How the follow-up schedule works

- Every time the user sends a message, the follow-up timer resets and any
  pending automatic message is cancelled.
- If the bot replies and then hears nothing back, it schedules an automatic
  check-in message:
  - Stage 0: after **1 hour**
  - Stage 1: after **3 hours**
  - Stage 2: after **10 hours**
  - Stage 3: after **1 week**
- After the stage-3 (weekly) message is sent with still no reply, automatic
  messages are **disabled** for that chat until the user sends a new message,
  which re-enables and resets the cycle.
- The schedule is stored in SQLite, so it survives restarts — on startup the
  app reloads any pending follow-ups and re-schedules them with the
  remaining time.

The delays and labels live in [`app/scheduler.py`](app/scheduler.py)
(`FOLLOWUP_DELAYS_SECONDS` / `FOLLOWUP_LABELS`) if you want to change them.

## Project layout

```
ai-companion-bot/
├── prompt.txt           # system prompt / personality — edit freely
├── poll.py              # standalone long-polling runner (no public URL needed)
├── app/
│   ├── main.py          # FastAPI app + webhook endpoint
│   ├── config.py        # env var / settings loading
│   ├── db.py             # SQLite storage (users, message history, follow-up state)
│   ├── llm.py             # Claude API calls
│   ├── telegram.py       # Telegram Bot API calls (sendMessage, webhook, getUpdates)
│   ├── scheduler.py       # APScheduler-based follow-up escalation
│   └── handlers.py        # shared logic for handling an incoming Telegram update
├── requirements.txt
└── .env.example
```

## Notes

- Data is stored in a local SQLite file (`data.db` by default).
- This is a minimal, single-process implementation meant for personal or
  small-scale use. For production scale you'd want a proper database and
  a process manager (e.g. systemd, Docker) in front of `uvicorn`.
# libinbot
# limbubot
# limbubot
