"""
decisions.py — Parse callback queries and persist YES/NO decisions.
"""

import json
import os
import datetime


def parse_callback(callback_data: str) -> dict | None:
    """
    Parse a callback_data string of the form "<offer_name>|YES" or "<offer_name>|NO".
    Returns a decision dict or None if the format is not recognised.
    """
    if "|" not in callback_data:
        return None
    offer_name, _, decision = callback_data.partition("|")
    decision = decision.strip().upper()
    if decision not in ("YES", "NO"):
        return None
    return {
        "offer_name": offer_name.strip(),
        "decision": decision,
        "timestamp": datetime.datetime.now().isoformat(),
    }


def save_decisions(decisions: list[dict], data_dir: str) -> None:
    """
    Append decisions to <data_dir>/decisions.json.
    Creates the file if it does not exist yet.
    """
    if not decisions:
        return

    decisions_path = os.path.join(data_dir, "decisions.json")

    existing: list[dict] = []
    if os.path.exists(decisions_path):
        try:
            with open(decisions_path, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
        except (json.JSONDecodeError, OSError):
            existing = []

    existing.extend(decisions)

    with open(decisions_path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, ensure_ascii=False, indent=4)

    print(f"  [E_TG] {len(decisions)} decision(s) saved → {decisions_path}")
