import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import db, llm, telegram

logger = logging.getLogger(__name__)

# Escalating re-engagement schedule: 1 hour -> 3 hours -> 10 hours -> 1 week,
# then automatic follow-ups are disabled until the user writes in again.
FOLLOWUP_DELAYS_SECONDS = [
    60 * 60,               # stage 0: 1 hour
    3 * 60 * 60,           # stage 1: 3 hours
    10 * 60 * 60,          # stage 2: 10 hours
    7 * 24 * 60 * 60,      # stage 3: 1 week
]

FOLLOWUP_LABELS = [
    "about an hour",
    "a few hours",
    "about 10 hours",
    "about a week",
]

scheduler = AsyncIOScheduler()


def _job_id(chat_id: int) -> str:
    return f"followup:{chat_id}"


def cancel_followup(chat_id: int) -> None:
    job = scheduler.get_job(_job_id(chat_id))
    if job is not None:
        job.remove()


def schedule_followup(chat_id: int, stage: int, delay_seconds: Optional[float] = None) -> None:
    """Schedule the next automatic re-engagement message for a chat."""
    if stage >= len(FOLLOWUP_DELAYS_SECONDS):
        db.set_followup_enabled(chat_id, False)
        return

    delay = FOLLOWUP_DELAYS_SECONDS[stage] if delay_seconds is None else delay_seconds
    delay = max(delay, 5)  # never schedule in the past
    run_at = datetime.now(timezone.utc) + timedelta(seconds=delay)

    scheduler.add_job(
        _send_followup,
        trigger="date",
        run_date=run_at,
        args=[chat_id, stage],
        id=_job_id(chat_id),
        replace_existing=True,
        misfire_grace_time=3600,
    )
    db.set_next_followup(chat_id, stage, run_at)


async def _send_followup(chat_id: int, stage: int) -> None:
    user = db.get_user(chat_id)
    if user is None or not user["followup_enabled"]:
        return

    try:
        text = await llm.generate_followup_message(chat_id, FOLLOWUP_LABELS[stage])
        await telegram.send_message(chat_id, text)
        db.add_message(chat_id, "assistant", text)
    except Exception:
        logger.exception("Follow-up #%s to chat %s failed", stage, chat_id)

    schedule_followup(chat_id, stage + 1)


def reload_pending_jobs() -> None:
    """Call on startup so follow-ups scheduled before a restart aren't lost."""
    for user in db.get_all_enabled_users():
        chat_id = user["chat_id"]
        stage = user["followup_stage"]
        next_at_raw = user["next_followup_at"]

        if stage >= len(FOLLOWUP_DELAYS_SECONDS):
            db.set_followup_enabled(chat_id, False)
            continue

        if next_at_raw:
            next_at = datetime.fromisoformat(next_at_raw)
            remaining = (next_at - datetime.now(timezone.utc)).total_seconds()
        else:
            remaining = FOLLOWUP_DELAYS_SECONDS[stage]

        schedule_followup(chat_id, stage, delay_seconds=remaining)
