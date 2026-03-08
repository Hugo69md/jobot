"""
Pre-selection logic for Step 3a-1.
Splits experiences into "forced" (matching offer_type) and "remaining" (for IA to choose from).
"""


def preselect_experiences(cv_data: dict, offer: dict) -> dict:
    """
    Pre-select experiences based on offer_type matching experience type fields.

    Returns:
        {
            "forced_indexes": [1, 2, 11],        # Always included in CV
            "remaining_pool": [3, 4, 5, ...],     # IA picks from these
            "needed_from_ia": 3,                   # How many IA must pick
            "skip_ia": False,                      # True if exactly 6 forced
        }
    """
    offer_type = offer.get("offer_type", "data")  # "data" or "supply_chain"
    experiences = cv_data.get("experiences", [])

    # Normalize offer_type for matching (handle "supply_chain" vs "Supply_chain")
    offer_type_lower = offer_type.lower().replace("_", " ")  # "supply chain" or "data"

    # Split experiences into matching and non-matching
    forced_indexes = []
    remaining_indexes = []

    for exp in experiences:
        exp_types = exp.get("type", [])
        # Normalize each type for comparison
        exp_types_lower = [t.lower().replace("_", " ") for t in exp_types]

        if offer_type_lower in exp_types_lower:
            forced_indexes.append(exp["index"])
        else:
            remaining_indexes.append(exp["index"])

    # Ensure index 1 (ECAM) is always in forced
    if 1 not in forced_indexes:
        # Move it from remaining to forced
        if 1 in remaining_indexes:
            remaining_indexes.remove(1)
        forced_indexes.insert(0, 1)
    
    n_forced = len(forced_indexes)

    # Decision logic
    if n_forced == 6:
        # Exactly 6 — skip IA entirely
        return {
            "forced_indexes": forced_indexes,
            "remaining_pool": [],
            "needed_from_ia": 0,
            "skip_ia": True,
        }
    elif n_forced > 6:
        # More than 6 — IA must pick best 6 from this pool only
        return {
            "forced_indexes": [],  # None forced, IA picks from all matching
            "remaining_pool": forced_indexes,  # All matching go to IA
            "needed_from_ia": 6,
            "skip_ia": False,
        }
    else:
        # Less than 6 — force all matching, IA picks remaining from non-matching
        needed = 6 - n_forced
        return {
            "forced_indexes": forced_indexes,
            "remaining_pool": remaining_indexes,
            "needed_from_ia": needed,
            "skip_ia": False,
        }