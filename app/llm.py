import logging

import httpx

from . import config, db

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_TOKENS = 1024

client = httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "AI Companion Bot",
    },
    timeout=60.0,
)


async def _call_claude(messages: list[dict]) -> str:
    system_prompt = config.load_system_prompt()  # re-read so edits to prompt.txt apply live
    payload = {
        "model": config.OPENROUTER_MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
    }

    try:
        response = await client.post(OPENROUTER_URL, json=payload)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.exception("OpenRouter API error: %s", e)
        return "Sorry, I'm having trouble thinking straight right now. Can you try again in a bit?"
    except httpx.RequestError:
        logger.exception("OpenRouter API connection error")
        return "I couldn't quite connect just now — give me a moment and try again?"

    data = response.json()
    choice = data["choices"][0]

    if choice.get("finish_reason") == "content_filter":
        logger.warning("OpenRouter refused the request: %s", choice)
        return "Hmm, I don't think I should respond to that one. Can we talk about something else?"

    content = choice.get("message", {}).get("content")
    return content or "..."


async def generate_reply(chat_id: int) -> str:
    """Generate the AI girlfriend's reply using the last HISTORY_LIMIT messages as context."""
    history = db.get_history(chat_id)
    return await _call_claude(history)


async def generate_followup_message(chat_id: int, time_label: str) -> str:
    """Generate a proactive check-in message after the user has gone quiet."""
    history = db.get_history(chat_id)
    note = (
        f"(System note: {time_label} has passed and they haven't replied. "
        "Write a short, caring, in-character message to check in on them. "
        "Don't mention this note.)"
    )
    messages = history + [{"role": "user", "content": note}]
    return await _call_claude(messages)
