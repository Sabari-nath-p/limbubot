import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from . import config, db, handlers, scheduler, telegram

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    scheduler.scheduler.start()
    scheduler.reload_pending_jobs()
    if config.WEBHOOK_URL:
        await telegram.set_webhook()
    logger.info("AI companion bot started.")
    yield
    scheduler.scheduler.shutdown(wait=False)


app = FastAPI(title="AI Companion Telegram Bot", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    if x_telegram_bot_api_secret_token != config.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="invalid secret token")

    update = await request.json()
    try:
        await handlers.handle_update(update)
    except Exception:
        logger.exception("Unhandled error while processing update: %s", update)
    # Always 200 back to Telegram so it doesn't keep retrying the same update.
    return JSONResponse({"ok": True})
