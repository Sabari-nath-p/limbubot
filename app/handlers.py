import logging

from . import db, llm, scheduler, telegram

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "Hey, it's me 💕 I'm so happy you're here. Just talk to me like you would "
    "anyone else — tell me about your day, or whatever's on your mind."
)


async def handle_update(update: dict) -> None:
    message = update.get("message")
    if not message or "text" not in message:
        return  # ignore non-text updates (photos, stickers, etc.) for now

    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    text = message["text"]

    db.upsert_user(chat_id, from_user.get("id"), from_user.get("username"))

    if text.strip() == "/start":
        db.reset_followup(chat_id)
        scheduler.cancel_followup(chat_id)
        await telegram.send_message(chat_id, WELCOME_TEXT)
        return

    # Any real message resets the "they went quiet" escalation.
    db.reset_followup(chat_id)
    scheduler.cancel_followup(chat_id)

    db.add_message(chat_id, "user", text)

    try:
        reply = await llm.generate_reply(chat_id)
    except Exception:
        logger.exception("Failed to generate reply for chat %s", chat_id)
        reply = "Sorry, my mind went blank for a second — can you say that again?"

    db.add_message(chat_id, "assistant", reply)
    await telegram.send_message(chat_id, reply)

    scheduler.schedule_followup(chat_id, stage=0)
