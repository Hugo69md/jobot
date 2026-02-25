import os
import json
from utils.c_ia.ollama_client import query_ollama
from utils.c_ia.prompt_builder import build_scoring_prompt, build_match_prompt


def run_ia(date: str):
    """
    Main entry point for the IA module.
    1. Load CV and scraped internships
    2. Send scoring prompt to Ollama → get all scores
    3. Extract top 5
    4. Send match prompt to Ollama → get detailed match + cover letters
    5. Save both JSON files to outputs/data[{date}]/
    """

    print("=" * 60)
    print("[C_IA] Starting AI analysis...")
    print("=" * 60)

    # ─── 1. Load input data ──────────────────────────────────────
    cv_path = os.path.join("inputs", "cv.json")
    internships_path = os.path.join("outputs", f"data[{date}]", "internships.json")

    if not os.path.exists(cv_path):
        print(f"  [ERROR] CV file not found: {cv_path}")
        return
    if not os.path.exists(internships_path):
        print(f"  [ERROR] Internships file not found: {internships_path}")
        return

    with open(cv_path, "r", encoding="utf-8") as f:
        cv_data = json.load(f)
    with open(internships_path, "r", encoding="utf-8") as f:
        internships_data = json.load(f)

    print(f"  [INFO] Loaded CV from {cv_path}")
    print(f"  [INFO] Loaded {len(internships_data)} internships from {internships_path}")

    # ─── 2. User prompt (what the AI should focus on) ────────────
    user_prompt = (
        "Je suis Hugo MANIPOUD, étudiant en 5ème année d'école d'ingénieur à l'ECAM Lyon. "
        "Je cherche un stage de fin d'études de 4 à 6 mois à partir de juin 2026, "
        "dans le domaine de la Data (Data Analyst, Data Engineer, Data Science) "
        "OU de la Supply Chain (planification, logistique, gestion des stocks, prévision de la demande). "
        "Je maîtrise Python, Excel avancé, pandas, numpy, matplotlib, seaborn, scikitlearn, "
        "et j'ai une expérience en supply chain (stage chez Arrow, stage chez Amazon). "
        "Je suis basé à Lyon mais mobile en France. "
        "Privilégier les offres qui matchent mes compétences data ET/OU supply chain."
    )

    # ─── 3. STEP 1: Score all offers ────────────────────────────
    print("\n  [STEP 1/2] Scoring all offers...")
    scoring_prompt = build_scoring_prompt(cv_data, internships_data, user_prompt)
    print(f"  [INFO] Scoring prompt size: ~{len(scoring_prompt)} chars")

    scoring_response = query_ollama(scoring_prompt, temperature=0.2)

    # Parse the scoring response
    try:
        scoring_result = json.loads(scoring_response)
    except json.JSONDecodeError as e:
        print(f"  [ERROR] Failed to parse scoring JSON: {e}")
        print(f"  [DEBUG] Raw response (first 500 chars): {scoring_response[:500]}")
        # Attempt to extract JSON from response
        scoring_result = _try_extract_json(scoring_response)
        if scoring_result is None:
            print("  [ERROR] Could not recover scoring data. Aborting.")
            return

    scoring_list = scoring_result.get("scoring", [])
    print(f"  [INFO] Scored {len(scoring_list)} offers")

    # Sort by score descending
    scoring_list.sort(key=lambda x: x.get("score", 0), reverse=True)

    # ─── 4. Extract top 5 ───────────────────────────────────────
    top_5 = scoring_list[:5]
    print(f"\n  [INFO] Top 5 offers:")
    for i, offer in enumerate(top_5):
        print(f"    {i+1}. [{offer.get('score', '?')}/100] {offer.get('name', 'Unknown')}")

    # ─── 5. STEP 2: Detailed match for top 5 ────────────────────
    print("\n  [STEP 2/2] Generating detailed match + cover letters for top 5...")
    match_prompt = build_match_prompt(cv_data, top_5, internships_data, user_prompt)
    print(f"  [INFO] Match prompt size: ~{len(match_prompt)} chars")

    match_response = query_ollama(match_prompt, temperature=0.4)

    # Parse the match response
    try:
        match_result = json.loads(match_response)
    except json.JSONDecodeError as e:
        print(f"  [ERROR] Failed to parse match JSON: {e}")
        print(f"  [DEBUG] Raw response (first 500 chars): {match_response[:500]}")
        match_result = _try_extract_json(match_response)
        if match_result is None:
            print("  [ERROR] Could not recover match data. Aborting.")
            return

    # ─── 6. Save output files ────────────────────────────────────
    output_dir = os.path.join("outputs", f"data[{date}]")

    scoring_output_path = os.path.join(output_dir, "scoring.json")
    match_output_path = os.path.join(output_dir, "match.json")

    with open(scoring_output_path, "w", encoding="utf-8") as f:
        json.dump({"scoring": scoring_list}, f, ensure_ascii=False, indent=4)
    print(f"\n  [SAVED] Scoring → {scoring_output_path}")

    with open(match_output_path, "w", encoding="utf-8") as f:
        json.dump(match_result, f, ensure_ascii=False, indent=4)
    print(f"  [SAVED] Match   → {match_output_path}")

    print("\n" + "=" * 60)
    print("[C_IA] AI analysis complete!")
    print("=" * 60)


def _try_extract_json(raw_text: str) -> dict | None:
    """
    Attempt to extract valid JSON from a response that might contain
    extra text before/after the JSON block.
    """
    # Try to find JSON between { and }
    start = raw_text.find("{")
    end = raw_text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(raw_text[start:end])
        except json.JSONDecodeError:
            pass

    # Try to find JSON between ```json and ```
    if "```json" in raw_text:
        json_block = raw_text.split("```json")[1].split("```")[0].strip()
        try:
            return json.loads(json_block)
        except json.JSONDecodeError:
            pass

    return None