"""
launcher.py — Entry point for Step E: send job offers to Telegram.

Usage (called by main.py):
    from utils.e_telegram.launcher import run_telegram
    run_telegram(date)

For each offer subfolder inside outputs/data[date]/pdf/:
  1. Read resume_*.json to extract offer details.
  2. Send offer URL, CV.pdf, LM.pdf, then a summary with YES/NO buttons.
  3. Poll briefly for button presses and save decisions.
"""

import asyncio
import glob
import json
import os

from telegram import Bot

from utils.e_telegram.bot import poll_callbacks, send_document, send_offer_summary, send_text
from utils.e_telegram.config import get_telegram_config
from utils.e_telegram.decisions import save_decisions

# How long (seconds) to wait for YES/NO button presses after sending all offers.
# Increase this value if you want more time to respond in a local run.
CALLBACK_POLL_TIMEOUT = int(os.environ.get("TELEGRAM_POLL_TIMEOUT", "60"))


def _find_resume_json(offer_dir: str, folder_name: str) -> dict | None:
    """Return the parsed content of resume_{folder_name}.json inside offer_dir, or None."""
    path = os.path.join(offer_dir, f"resume_{folder_name}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [E_TG] Could not read {path}: {exc}")
        return None


def _find_pdf(offer_dir: str, prefix: str) -> str | None:
    """Return path to a PDF file starting with prefix inside offer_dir, or None."""
    candidates = glob.glob(os.path.join(offer_dir, f"{prefix}*.pdf"))
    return candidates[0] if candidates else None


async def _send_all_offers(bot: Bot, chat_id: str, pdf_dir: str) -> list[str]:
    """
    Iterate over offer subfolders and send each offer to Telegram.
    Returns the list of callback prefixes that were sent (for later matching).
    """
    sent_prefixes = []

    subfolders = sorted(
        [
            d
            for d in os.listdir(pdf_dir)
            if os.path.isdir(os.path.join(pdf_dir, d))
        ]
    )

    if not subfolders:
        print("  [E_TG] No offer subfolders found — nothing to send.")
        return sent_prefixes

    print(f"  [E_TG] Found {len(subfolders)} offer subfolder(s)")

    for folder_name in subfolders:
        offer_dir = os.path.join(pdf_dir, folder_name)

        # ── Load offer metadata ──────────────────────────────────
        resume_data = _find_resume_json(offer_dir, folder_name)
        if resume_data is None:
            print(f"  [E_TG] Skipping {folder_name} — no resume JSON found")
            continue

        offer_name = resume_data.get("offer_name", folder_name)
        company    = resume_data.get("offer_company", "Unknown")
        score      = resume_data.get("score", "?")
        offer_url  = resume_data.get("offer_URL", "")

        print(f"\n  [E_TG] Sending: {company} — {offer_name} (score {score})")

        # ── 1. Offer URL ─────────────────────────────────────────
        if offer_url:
            await send_text(bot, chat_id, f"🔗 {offer_url}")
        else:
            await send_text(bot, chat_id, f"🔗 (URL not available for: {offer_name})")

        # ── 2. CV PDF ────────────────────────────────────────────
        cv_path = _find_pdf(offer_dir, "CV")
        if cv_path:
            await send_document(bot, chat_id, cv_path, caption=f"📄 CV — {offer_name}")
        else:
            print(f"    [WARN] CV.pdf not found in {offer_dir}")

        # ── 3. Cover letter PDF ───────────────────────────────────
        lm_path = _find_pdf(offer_dir, "LM")
        if lm_path:
            await send_document(bot, chat_id, lm_path, caption=f"✉️ LM — {offer_name}")
        else:
            print(f"    [WARN] LM.pdf not found in {offer_dir}")

        # ── 4. Summary + YES/NO buttons ──────────────────────────
        # Telegram limits callback_data to 64 bytes.
        # We append "|YES" or "|NO" (max 4 bytes) later in bot.py,
        # so the prefix must fit in 60 bytes when UTF-8 encoded.
        prefix_bytes = folder_name.encode("utf-8")[:60]
        callback_prefix = prefix_bytes.decode("utf-8", errors="ignore")
        await send_offer_summary(
            bot=bot,
            chat_id=chat_id,
            offer_name=offer_name,
            company=company,
            score=score,
            callback_prefix=callback_prefix,
        )
        sent_prefixes.append(callback_prefix)

    return sent_prefixes


async def _run_async(date: str) -> None:
    config  = get_telegram_config()
    token   = config["token"]
    chat_id = config["chat_id"]

    data_dir = os.path.join("outputs", f"data[{date}]")
    pdf_dir  = os.path.join(data_dir, "pdf")

    if not os.path.isdir(pdf_dir):
        print(f"  [E_TG] PDF directory not found: {pdf_dir} — skipping Telegram step")
        return

    async with Bot(token=token) as bot:
        # Send all offers
        await _send_all_offers(bot, chat_id, pdf_dir)

        # Poll for YES/NO decisions
        if CALLBACK_POLL_TIMEOUT > 0:
            decisions = await poll_callbacks(bot, timeout=CALLBACK_POLL_TIMEOUT)
            save_decisions(decisions, data_dir)
        else:
            print("  [E_TG] Callback polling disabled (TELEGRAM_POLL_TIMEOUT=0)")


def run_telegram(date: str) -> None:
    """
    Entry point called by main.py.
    Sends each scored offer (URL + CV + LM + YES/NO summary) to Telegram,
    then polls briefly for button responses.
    """
    print("=" * 60)
    print("[E_TG] Starting Telegram notification step…")
    print("=" * 60)

    try:
        asyncio.run(_run_async(date))
    except RuntimeError as exc:
        print(f"  [E_TG] Configuration error: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [E_TG] Unexpected error: {exc}")
        raise

    print("=" * 60)
    print("[E_TG] Telegram step complete.")
    print("=" * 60)
