import os
import json
from utils.c_ia.ollama_client import query_ollama_json
from utils.c_ia.prompt_builder import build_extraction_prompt, build_single_offer_scoring_prompt, build_match_prompt


USER_PROMPT = (
    "Je suis Hugo MANIPOUD, étudiant en 5ème année d'école d'ingénieur à l'ECAM Lyon. "
    "Je cherche un stage de fin d'études de 4 à 6 mois à partir de juin 2026, "
    "dans le domaine de la Data (Data Analyst, Data Engineer, Data Science) "
    "OU de la Supply Chain (planification, logistique, gestion des stocks, prévision de la demande). "
    "Je maîtrise Python, Excel avancé, pandas, numpy, matplotlib, seaborn, scikitlearn, "
    "et j'ai une expérience en supply chain (stage chez Arrow, stage chez Amazon). "
    "Je suis basé à Lyon mais mobile en France. "
    "Privilégier les offres qui matchent mes compétences data ET/OU supply chain."
)


def run_ia(date: str):
    print("=" * 60)
    print("[C_IA] Starting AI analysis (full description pipeline)...")
    print("=" * 60)

    cv_path = os.path.join("inputs", "cv.json")
    internships_path = os.path.join("outputs", f"data[{date}]", "internships.json")
    output_dir = os.path.join("outputs", f"data[{date}]")

    if not os.path.exists(cv_path):
        print(f"  [ERROR] CV not found: {cv_path}")
        return
    if not os.path.exists(internships_path):
        print(f"  [ERROR] Internships not found: {internships_path}")
        return

    with open(cv_path, "r", encoding="utf-8") as f:
        cv_data = json.load(f)
    with open(internships_path, "r", encoding="utf-8") as f:
        internships_data = json.load(f)

    print(f"  [INFO] Loaded CV + {len(internships_data)} offers")

    # ── STEP 1: Extract structured data from each offer's full description ──
    print(f"\n  [STEP 1] Extracting structured info from {len(internships_data)} offers...")
    enriched_offers = []

    for i, offer in enumerate(internships_data):
        offer_name = offer.get("name", f"offer_{i}")
        print(f"\n  [{i+1}/{len(internships_data)}] Extracting: {offer_name[:60]}...")
        print(f"  [INFO] Content length: {len(offer.get('content', ''))} chars")

        extraction_prompt = build_extraction_prompt(offer)
        extraction = query_ollama_json(extraction_prompt, temperature=0.1, num_predict=512)

        if extraction:
            enriched_offer = {
                **offer,
                "profil_recherche": extraction.get("profil_recherche", ""),
                "missions": extraction.get("missions", []),
                "competences": extraction.get("competences", []),
            }
            print(f"  ✅ Extracted {len(enriched_offer['competences'])} skills, {len(enriched_offer['missions'])} missions")
        else:
            enriched_offer = {**offer, "profil_recherche": "", "missions": [], "competences": []}
            print(f"  ⚠️  Extraction failed, using empty structured fields")

        enriched_offers.append(enriched_offer)

    # Save enriched offers for debugging
    enriched_path = os.path.join(output_dir, "internships_enriched.json")
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(enriched_offers, f, ensure_ascii=False, indent=4)
    print(f"\n  [SAVED] Enriched offers → {enriched_path}")

    # ── STEP 2: Score each enriched offer ───────────────────────────────────
    print(f"\n  [STEP 2] Scoring {len(enriched_offers)} enriched offers...")
    scoring_list = []

    for i, offer in enumerate(enriched_offers):
        offer_name = offer.get("name", f"offer_{i}")
        print(f"\n  [{i+1}/{len(enriched_offers)}] Scoring: {offer_name[:60]}...")

        prompt = build_single_offer_scoring_prompt(cv_data, offer, USER_PROMPT)
        result = query_ollama_json(prompt, temperature=0.1, num_predict=256)

        if result and "score" in result:
            score_entry = {
                "name": result.get("name", offer_name),
                "score": int(result.get("score", 0)),
                "reason": result.get("reason", ""),
            }
            print(f"  ✅ Score: {score_entry['score']}/100 — {score_entry['reason'][:80]}")
        else:
            score_entry = {"name": offer_name, "score": 0, "reason": "parse_error"}
            print(f"  ⚠️  Scoring failed, assigned score=0")

        scoring_list.append(score_entry)

        # Crash-safe intermediate save
        scoring_list_sorted = sorted(scoring_list, key=lambda x: x["score"], reverse=True)
        with open(os.path.join(output_dir, "scoring.json"), "w", encoding="utf-8") as f:
            json.dump({"scoring": scoring_list_sorted}, f, ensure_ascii=False, indent=4)

    # ── STEP 2b: Final sort & summary ───────────────────────────────────────
    scoring_list.sort(key=lambda x: x["score"], reverse=True)
    print(f"\n  [SCORING COMPLETE] {len(scoring_list)} offers scored")
    print("  Top 10:")
    for i, s in enumerate(scoring_list[:10]):
        print(f"    {i+1:2d}. [{s['score']:3d}/100] {s['name'][:55]}")

    # ── STEP 3: Find best offer deterministically in Python ─────────────────
    best_scored = scoring_list[0]
    best_offer_full = None
    for offer in enriched_offers:
        if offer.get("name", "") == best_scored["name"]:
            best_offer_full = {**offer, "score": best_scored["score"]}
            break

    if best_offer_full is None:
        print(f"  [ERROR] Could not find full data for: {best_scored['name']}")
        return

    print(f"\n  [BEST OFFER] Score {best_scored['score']}/100: {best_scored['name']}")

    # ── STEP 4: Cover letter + skills for best offer ─────────────────────────
    print("\n  [STEP 4] Generating cover letter + skills for best offer...")
    match_prompt = build_match_prompt(cv_data, best_offer_full, USER_PROMPT)
    print(f"  [INFO] Match prompt: ~{len(match_prompt)} chars (~{len(match_prompt)//4} tokens)")

    match_result = query_ollama_json(match_prompt, temperature=0.4, num_predict=4096)

    if match_result is None:
        print("  [ERROR] Failed to generate cover letter.")
        match_result = {"match": {"name": best_offer_full["name"], "error": "generation_failed"}}

    match_output_path = os.path.join(output_dir, "match.json")
    with open(match_output_path, "w", encoding="utf-8") as f:
        json.dump(match_result, f, ensure_ascii=False, indent=4)
    print(f"  [SAVED] Match → {match_output_path}")

    print("\n" + "=" * 60)
    print("[C_IA] AI analysis complete!")
    print(f"  Offers scored: {len(scoring_list)}")
    print(f"  Best offer:    [{best_scored['score']}/100] {best_scored['name']}")
    print("=" * 60)