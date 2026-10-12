"""
Standalone long-polling runner — an alternative to running the FastAPI app
behind a public webhook URL. Useful for local testing: no ngrok, no public
server needed. Automatic follow-up messages still work, since this process
also runs the same APScheduler instance.

Usage:
    python poll.py
"""

import asyncio
import logging

from app import config, db, handlers, scheduler, telegram

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    db.init_db()
    await telegram.delete_webhook()  # polling and webhooks can't be used at the same time
    scheduler.scheduler.start()
    scheduler.reload_pending_jobs()
    logger.info("AI companion bot started in long-polling mode. Press Ctrl+C to stop.")

    offset = None
    while True:
        try:
            updates = await telegram.get_updates(offset)
        except Exception:
            logger.exception("getUpdates failed, retrying in 5s")
            await asyncio.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            try:
                await handlers.handle_update(update)
            except Exception:
                logger.exception("Unhandled error while processing update: %s", update)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
