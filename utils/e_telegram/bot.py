"""
Core Telegram bot helpers using python-telegram-bot v20+.

All public functions are async and must be awaited inside an asyncio event loop.
"""

import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.error import TelegramError


async def send_text(bot: Bot, chat_id: str, text: str) -> None:
    """Send a plain text message."""
    await bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True)


async def send_document(bot: Bot, chat_id: str, file_path: str, caption: str = "") -> None:
    """Send a file (PDF) as a Telegram document."""
    with open(file_path, "rb") as fh:
        await bot.send_document(chat_id=chat_id, document=InputFile(fh), caption=caption)


async def send_offer_summary(
    bot: Bot,
    chat_id: str,
    offer_name: str,
    company: str,
    score,
    callback_prefix: str,
) -> None:
    """
    Send a summary message with YES / NO inline keyboard buttons.

    callback_data format: "<callback_prefix>|YES" / "<callback_prefix>|NO"
    where callback_prefix is a short identifier for the offer (e.g. a sanitized name).
    """
    text = (
        f"📋 *Offre :* {offer_name}\n"
        f"🏢 *Entreprise :* {company}\n"
        f"⭐ *Score :* {score}/100"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ YES", callback_data=f"{callback_prefix}|YES"),
                InlineKeyboardButton("❌ NO", callback_data=f"{callback_prefix}|NO"),
            ]
        ]
    )
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def poll_callbacks(bot: Bot, timeout: int = 60) -> list[dict]:
    """
    Poll the Telegram API for incoming callback queries for `timeout` seconds.

    Returns a list of dicts: [{"offer_name": ..., "decision": "YES|NO", ...}, ...]

    Note: In a persistent server the Application class (with handlers) is preferable.
    This simple polling loop is designed for short-lived CI/CD runs.
    """
    from utils.e_telegram.decisions import parse_callback

    collected = []
    offset = None
    deadline = asyncio.get_event_loop().time() + timeout

    print(f"  [E_TG] Listening for YES/NO responses for {timeout}s …")

    while asyncio.get_event_loop().time() < deadline:
        remaining = deadline - asyncio.get_event_loop().time()
        poll_timeout = min(10, int(remaining))
        if poll_timeout <= 0:
            break

        try:
            updates = await bot.get_updates(
                offset=offset,
                timeout=poll_timeout,
                allowed_updates=["callback_query"],
            )
        except TelegramError as exc:
            print(f"  [E_TG] Polling error: {exc}")
            await asyncio.sleep(2)
            continue

        for update in updates:
            offset = update.update_id + 1
            if update.callback_query:
                cq = update.callback_query
                decision = parse_callback(cq.data)
                if decision:
                    collected.append(decision)
                    print(
                        f"  [E_TG] Decision received — {decision['offer_name']}: {decision['decision']}"
                    )
                try:
                    await cq.answer()
                except TelegramError:
                    pass

    return collected
