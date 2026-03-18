import os


def get_telegram_config() -> dict:
    """
    Read Telegram credentials from environment variables.
    Raises RuntimeError if any required variable is missing.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN environment variable is not set. "
            "Add it as a GitHub Secret or export it before running."
        )
    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID environment variable is not set. "
            "Add it as a GitHub Secret or export it before running."
        )

    return {"token": token, "chat_id": chat_id}
