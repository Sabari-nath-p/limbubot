import logging
from typing import Optional

import httpx

from . import config

logger = logging.getLogger(__name__)

API_BASE = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


async def send_message(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
    if resp.status_code != 200:
        logger.error("Telegram sendMessage failed (%s): %s", resp.status_code, resp.text)


async def set_webhook() -> None:
    if not config.WEBHOOK_URL:
        logger.warning("WEBHOOK_URL not set; skipping Telegram setWebhook call.")
        return
    webhook_endpoint = f"{config.WEBHOOK_URL}/telegram/webhook"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{API_BASE}/setWebhook",
            json={
                "url": webhook_endpoint,
                "secret_token": config.WEBHOOK_SECRET,
                "allowed_updates": ["message"],
            },
        )
    if resp.status_code == 200 and resp.json().get("ok"):
        logger.info("Telegram webhook set to %s", webhook_endpoint)
    else:
        logger.error("Failed to set Telegram webhook: %s", resp.text)


async def delete_webhook() -> None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        await client.post(f"{API_BASE}/deleteWebhook")


async def get_updates(offset: Optional[int], timeout: int = 30) -> list:
    """Long-poll for updates. Used only by the standalone polling runner (poll.py)."""
    params = {"timeout": timeout, "allowed_updates": '["message"]'}
    if offset is not None:
        params["offset"] = offset
    async with httpx.AsyncClient(timeout=timeout + 10) as client:
        resp = await client.get(f"{API_BASE}/getUpdates", params=params)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        logger.error("getUpdates failed: %s", data)
        return []
    return data.get("result", [])
