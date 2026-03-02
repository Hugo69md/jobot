import os
import json
from utils.c_ia.ollama_client import query_ollama_json
from utils.c_ia.prompt_builder import (
    build_domain_classification_prompt,
    build_extraction_prompt,
    build_single_offer_scoring_prompt,
    build_experience_selection_prompt,
    build_resume_prompt,
    build_cover_letter_prompt,
    build_skills_section_prompt,
)


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

    cv_path          = os.path.join("inputs", "cv.json")
    internships_path = os.path.join("outputs", f"data[{date}]", "internships.json")
    output_dir       = os.path.join("outputs", f"data[{date}]")

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

    # ══════════════════════════════════════════════════════════════
    # STEP 0 — Domain classification (fast filter)
    # ══════════════════════════════════════════════════════════════
    print(f"\n  [STEP 0] Classifying domains for {len(internships_data)} offers...")
    classified_offers = []
    dropped_count = 0

    for i, offer in enumerate(internships_data):
        offer_name = offer.get("name", f"offer_{i}")
        print(f"  [{i+1}/{len(internships_data)}] {offer_name[:60]}...", end=" ")

        classification_prompt = build_domain_classification_prompt(offer)
        classification = query_ollama_json(classification_prompt, temperature=0.0, num_predict=32)

        domain = classification.get("domain", "") if classification else ""

        if domain not in ("data", "supply_chain"):
            print(f"❌ DROPPED (domain='{domain}')")
            dropped_count += 1
            continue

        classified_offers.append({**offer, "offer_type": domain})
        print(f"✅ {domain}")

    print(f"\n  [STEP 0] Kept {len(classified_offers)} / {len(internships_data)} "
          f"({dropped_count} dropped)")

    if not classified_offers:
        print("  [ERROR] No offers left after classification — aborting.")
        return

    # ══════════════════════════════════════════════════════════════
    # STEP 1 — Extract structured info (only on classified offers)
    # ══════════════════════════════════════════════════════════════
    print(f"\n  [STEP 1] Extracting structured info from {len(classified_offers)} offers...")
    enriched_offers = []

    for i, offer in enumerate(classified_offers):
        offer_name = offer.get("name", f"offer_{i}")
        print(f"\n  [{i+1}/{len(classified_offers)}] Extracting: {offer_name[:60]}...")

        extraction_prompt = build_extraction_prompt(offer)
        extraction = query_ollama_json(extraction_prompt, temperature=0.1, num_predict=512)

        if extraction:
            enriched_offer = {
                **offer,                  # ← already has offer_type from STEP 0
                "profil_recherche": extraction.get("profil_recherche", ""),
                "missions":         extraction.get("missions", []),
                "competences":      extraction.get("competences", []),
            }
            print(f"  ✅ {enriched_offer['offer_type']} | "
                  f"{len(enriched_offer['competences'])} skills | "
                  f"{len(enriched_offer['missions'])} missions")
        else:
            enriched_offer = {
                **offer,
                "profil_recherche": "",
                "missions":         [],
                "competences":      [],
            }
            print(f"  ⚠️  Extraction failed")

        enriched_offers.append(enriched_offer)

    # Save enriched + filtered offers
    enriched_path = os.path.join(output_dir, "internships_enriched.json")
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(enriched_offers, f, ensure_ascii=False, indent=4)
    print(f"\n  [SAVED] Enriched offers → {enriched_path}")
    print(f"  [FILTER] Kept {len(enriched_offers)} / {len(internships_data)} "
          f"({dropped_count} dropped)")

    if not enriched_offers:
        print("  [ERROR] No offers left after filtering — aborting.")
        return

    # ══════════════════════════════════════════════════════════════
    # STEP 2 — Score each enriched offer
    # ══════════════════════════════════════════════════════════════
    print(f"\n  [STEP 2] Scoring {len(enriched_offers)} offers...")
    scoring_list = []

    for i, offer in enumerate(enriched_offers):
        offer_name = offer.get("name", f"offer_{i}")
        print(f"\n  [{i+1}/{len(enriched_offers)}] Scoring: {offer_name[:60]}...")

        prompt = build_single_offer_scoring_prompt(cv_data, offer, USER_PROMPT)
        result = query_ollama_json(prompt, temperature=0.1, num_predict=256)

        if result and "score" in result:
            score_entry = {
                "name":   result.get("name", offer_name),
                "score":  int(result.get("score", 0)),
                "reason": result.get("reason", ""),
            }
            print(f"  ✅ Score: {score_entry['score']}/100")
        else:
            score_entry = {"name": offer_name, "score": 0, "reason": "parse_error"}
            print(f"  ⚠️  Scoring failed, assigned score=0")

        scoring_list.append(score_entry)

        # Crash-safe intermediate save after each offer
        scoring_list_sorted = sorted(scoring_list, key=lambda x: x["score"], reverse=True)
        with open(os.path.join(output_dir, "scoring.json"), "w", encoding="utf-8") as f:
            json.dump({"scoring": scoring_list_sorted}, f, ensure_ascii=False, indent=4)

    scoring_list.sort(key=lambda x: x["score"], reverse=True)
    print(f"\n  [SCORING COMPLETE] Top 10:")
    for i, s in enumerate(scoring_list[:10]):
        print(f"    {i+1:2d}. [{s['score']:3d}/100] {s['name'][:55]}")

    # ══════════════════════════════════════════════════════════════
    # STEP 3 — Find best offer deterministically in Python
    # ══════════════════════════════════════════════════════════════
    best_scored     = scoring_list[0]
    best_offer_full = None
    for offer in enriched_offers:
        if offer.get("name", "") == best_scored["name"]:
            best_offer_full = {**offer, "score": best_scored["score"]}
            break

    if best_offer_full is None:
        print(f"  [ERROR] Could not find full data for: {best_scored['name']}")
        return

    print(f"\n  [BEST OFFER] Score {best_scored['score']}/100: {best_scored['name']}")
    print(f"  [BEST OFFER] Type: {best_offer_full.get('offer_type', '?')}")

    # ══════════════════════════════════════════════════════════════
    # STEP 3a — Select 6 best experiences + tailor descriptions
    # ══════════════════════════════════════════════════════════════
    print("\n  [STEP 3a] Selecting experiences + tailoring resume descriptions...")

    selection_prompt = build_experience_selection_prompt(cv_data, best_offer_full)
    selection_result = query_ollama_json(selection_prompt, temperature=0.1, num_predict=128)

    if selection_result and "skills" in selection_result:
        selected_indexes = selection_result["skills"]
        print(f"  ✅ Selected experience indexes: {selected_indexes}")
    else:
        selected_indexes = [exp["index"] for exp in cv_data.get("experiences", [])][:6]
        print(f"  ⚠️  Selection failed, fallback to first 6: {selected_indexes}")

    resume_prompt  = build_resume_prompt(cv_data, best_offer_full, selected_indexes)
    resume_result  = query_ollama_json(resume_prompt, temperature=0.2, num_predict=2048)

    if resume_result and "resume" in resume_result:
        print(f"  ✅ Tailored {len(resume_result['resume'])} descriptions")
        for exp in resume_result["resume"]:
            print(f"    → [{exp.get('index')}] {exp.get('name', '')[:50]}"
                  f" | keywords: {exp.get('keywords_injected', [])}")
    else:
        print("  ⚠️  Resume tailoring failed")
        resume_result = {"resume": []}

    # Flatten all injected keywords across all experiences (used in STEP 4)
    all_keywords_injected = []
    seen_kw = set()
    for exp_entry in resume_result.get("resume", []):
        for kw in exp_entry.get("keywords_injected", []):
            kw_norm = kw.strip()
            if kw_norm and kw_norm.lower() not in seen_kw:
                seen_kw.add(kw_norm.lower())
                all_keywords_injected.append(kw_norm)
    print(f"  [INFO] Unique keywords injected: {len(all_keywords_injected)} → {all_keywords_injected}")

    # ══════════════════════════════════════════════════════════════
    # STEP 3b — Generate cover letter
    # ══════════════════════════════════════════════════════════════
    print("\n  [STEP 3b] Generating cover letter...")

    cover_letter_prompt  = build_cover_letter_prompt(cv_data, best_offer_full, USER_PROMPT)
    cover_letter_result  = query_ollama_json(cover_letter_prompt, temperature=0.4, num_predict=2048)

    if cover_letter_result is None:
        print("  ⚠️  Cover letter generation failed")
        cover_letter_result = {"cover_letter": {"name": best_offer_full["name"], "error": "generation_failed"}}

    cover_letter_output_path = os.path.join(output_dir, "cover_letter.json")
    with open(cover_letter_output_path, "w", encoding="utf-8") as f:
        json.dump(cover_letter_result, f, ensure_ascii=False, indent=4)
    print(f"  [SAVED] Cover letter → {cover_letter_output_path}")

    # ══════════════════════════════════════════════════════════════
    # STEP 4 — Select 6 skills for CV skills section
    # ══════════════════════════════════════════════════════════════
    print("\n  [STEP 4] Selecting 6 skills for CV skills section...")

    skills_section_prompt  = build_skills_section_prompt(cv_data, best_offer_full, resume_result)
    skills_section_result  = query_ollama_json(skills_section_prompt, temperature=0.1, num_predict=128)

    if skills_section_result and "skills_section" in skills_section_result:
        cv_skills_section = skills_section_result["skills_section"][:6]
        print(f"  ✅ Skills section: {cv_skills_section}")
    else:
        cv_skills_section = all_keywords_injected[:6]
        print(f"  ⚠️  Fallback to first 6 injected keywords: {cv_skills_section}")

    # ══════════════════════════════════════════════════════════════
    # SAVE — resume.json (final, includes skills_section + offer_type)
    # ══════════════════════════════════════════════════════════════
    resume_output_path = os.path.join(output_dir, "resume.json")
    with open(resume_output_path, "w", encoding="utf-8") as f:
        json.dump({
            "offer_name":       best_offer_full["name"],
            "offer_company":    best_offer_full["company"],
            "offer_type":       best_offer_full.get("offer_type", "data"),
            "score":            best_scored["score"],
            "selected_indexes": selected_indexes,
            "skills_section":   cv_skills_section,
            **resume_result,
        }, f, ensure_ascii=False, indent=4)
    print(f"  [SAVED] Resume → {resume_output_path}")

    # ══════════════════════════════════════════════════════════════
    # SAVE — match.json (backward compat with d_files_gen)
    # ══════════════════════════════════════════════════════════════
    cover_letter_data  = cover_letter_result.get("cover_letter", {})
    match_output_path  = os.path.join(output_dir, "match.json")
    with open(match_output_path, "w", encoding="utf-8") as f:
        json.dump({
            "match": {
                "name":         best_offer_full["name"],
                "URL":          best_offer_full.get("URL", ""),
                "company":      best_offer_full["company"],
                "location":     best_offer_full.get("location", ""),
                "score":        best_scored["score"],
                "skills":       selected_indexes,
                "cover_letter": cover_letter_data.get("text", ""),
            }
        }, f, ensure_ascii=False, indent=4)
    print(f"  [SAVED] Match (compat) → {match_output_path}")

    # ══════════════════════════════════════════════════════════════
    # DONE
    # ══════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("[C_IA] AI analysis complete!")
    print(f"  Offers scraped:  {len(internships_data)}")
    print(f"  Offers kept:     {len(enriched_offers)} ({dropped_count} dropped)")
    print(f"  Offers scored:   {len(scoring_list)}")
    print(f"  Best offer:      [{best_scored['score']}/100] {best_scored['name']}")
    print(f"  Type:            {best_offer_full.get('offer_type', '?')}")
    print(f"  Skills section:  {cv_skills_section}")
    print("=" * 60)
