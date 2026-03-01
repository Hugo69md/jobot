import os
import json
from utils.c_ia.ollama_client import query_ollama_json
from utils.c_ia.prompt_builder import (
    build_extraction_prompt,
    build_single_offer_scoring_prompt,
    build_resume_prompt,
    build_cover_letter_prompt,
    build_skills_section_prompt
)
from utils.c_ia.prompt_builder import _build_cv_summary as _build_cv_summary  # noqa


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

    # ── STEP 1: Extract structured data from each offer ──────────────────────
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

    enriched_path = os.path.join(output_dir, "internships_enriched.json")
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(enriched_offers, f, ensure_ascii=False, indent=4)
    print(f"\n  [SAVED] Enriched offers → {enriched_path}")

    # ── STEP 2: Score each enriched offer ────────────────────────────────────
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
            print(f"  ✅ Score: {score_entry['score']}/100")
        else:
            score_entry = {"name": offer_name, "score": 0, "reason": "parse_error"}
            print(f"  ⚠️  Scoring failed, assigned score=0")

        scoring_list.append(score_entry)

        # Crash-safe intermediate save
        scoring_list_sorted = sorted(scoring_list, key=lambda x: x["score"], reverse=True)
        with open(os.path.join(output_dir, "scoring.json"), "w", encoding="utf-8") as f:
            json.dump({"scoring": scoring_list_sorted}, f, ensure_ascii=False, indent=4)

    scoring_list.sort(key=lambda x: x["score"], reverse=True)
    print(f"\n  [SCORING COMPLETE] Top 10:")
    for i, s in enumerate(scoring_list[:10]):
        print(f"    {i+1:2d}. [{s['score']:3d}/100] {s['name'][:55]}")

    # ── STEP 3: Find best offer deterministically in Python ──────────────────
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

    # ── STEP 3a: Select top 6 experiences + generate tailored resume ─────────
    print("\n  [STEP 3a] Selecting top 6 experiences + tailoring resume descriptions...")

    # First ask the AI to select the best 6 experience indexes for this offer
    selection_prompt = _build_experience_selection_prompt(cv_data, best_offer_full, USER_PROMPT)
    selection_result = query_ollama_json(selection_prompt, temperature=0.1, num_predict=128)

    if selection_result and "skills" in selection_result:
        selected_indexes = selection_result["skills"]
        print(f"  ✅ Selected experience indexes: {selected_indexes}")
    else:
        # Fallback: use all experience indexes
        selected_indexes = [exp["index"] for exp in cv_data.get("experiences", [])][:6]
        print(f"  ⚠️  Selection failed, using first 6 experiences: {selected_indexes}")

    # Now tailor the descriptions of those experiences for this offer
    resume_prompt = build_resume_prompt(cv_data, best_offer_full, selected_indexes)
    print(f"  [INFO] Resume prompt: ~{len(resume_prompt)//4} tokens")

    resume_result = query_ollama_json(resume_prompt, temperature=0.2, num_predict=2048)

    if resume_result and "resume" in resume_result:
        print(f"  ✅ Tailored {len(resume_result['resume'])} experience descriptions")
        for exp in resume_result["resume"]:
            print(f"    → [{exp.get('index')}] {exp.get('name', '')[:50]} | keywords: {exp.get('keywords_injected', [])}")
    else:
        print("  ⚠️  Resume tailoring failed, saving empty resume")
        resume_result = {"resume": []}

    resume_output_path = os.path.join(output_dir, "resume.json")
    with open(resume_output_path, "w", encoding="utf-8") as f:
        json.dump({
            "offer_name": best_offer_full["name"],
            "offer_company": best_offer_full["company"],
            "score": best_scored["score"],
            "selected_indexes": selected_indexes,
            **resume_result
        }, f, ensure_ascii=False, indent=4)
    print(f"  [SAVED] Resume → {resume_output_path}")
    # Add this right after resume_result is confirmed valid (after STEP 3a):
    all_keywords_injected = []
    seen_kw = set()
    for exp_entry in resume_result.get("resume", []):
        for kw in exp_entry.get("keywords_injected", []):
            kw_norm = kw.strip()
            if kw_norm and kw_norm.lower() not in seen_kw:
                seen_kw.add(kw_norm.lower())
                all_keywords_injected.append(kw_norm)
    print(f"  [INFO] Total unique keywords injected: {len(all_keywords_injected)} → {all_keywords_injected}")

    # ── STEP 3b: Generate cover letter ───────────────────────────────────────
    print("\n  [STEP 3b] Generating cover letter...")

    cover_letter_prompt = build_cover_letter_prompt(cv_data, best_offer_full, USER_PROMPT)
    print(f"  [INFO] Cover letter prompt: ~{len(cover_letter_prompt)//4} tokens")

    cover_letter_result = query_ollama_json(cover_letter_prompt, temperature=0.4, num_predict=2048)

    if cover_letter_result is None:
        print("  ⚠️  Cover letter generation failed")
        cover_letter_result = {"cover_letter": {"name": best_offer_full["name"], "error": "generation_failed"}}

    cover_letter_output_path = os.path.join(output_dir, "cover_letter.json")
    with open(cover_letter_output_path, "w", encoding="utf-8") as f:
        json.dump(cover_letter_result, f, ensure_ascii=False, indent=4)
    print(f"  [SAVED] Cover letter → {cover_letter_output_path}")

    # ── Also write combined match.json for backward compat with d_files_gen ──
    match_output_path = os.path.join(output_dir, "match.json")
    cover_letter_data = cover_letter_result.get("cover_letter", {})
    with open(match_output_path, "w", encoding="utf-8") as f:
        json.dump({
            "match": {
                "name": best_offer_full["name"],
                "URL": best_offer_full.get("URL", ""),
                "company": best_offer_full["company"],
                "location": best_offer_full.get("location", ""),
                "score": best_scored["score"],
                "skills": selected_indexes,
                "cover_letter": cover_letter_data.get("text", ""),
            }
        }, f, ensure_ascii=False, indent=4)
    print(f"  [SAVED] Match (compat) → {match_output_path}")

    print("\n" + "=" * 60)
    print("[C_IA] AI analysis complete!")
    print(f"  Offers scored:  {len(scoring_list)}")
    print(f"  Best offer:     [{best_scored['score']}/100] {best_scored['name']}")
    print(f"  Resume file:    {resume_output_path}")
    print(f"  Cover letter:   {cover_letter_output_path}")
    print("=" * 60)
     # ── STEP 4: Select 6 skills for CV skills section ────────────────────────
    print("\n  [STEP 4] Selecting 6 skills for CV skills section...")

    skills_section_prompt = build_skills_section_prompt(
        cv_data=cv_data,
        best_offer=best_offer_full,
        resume_data=resume_result,
    )
    print(f"  [INFO] Skills section prompt: ~{len(skills_section_prompt)//4} tokens")

    skills_section_result = query_ollama_json(skills_section_prompt, temperature=0.1, num_predict=128)

    if skills_section_result and "skills_section" in skills_section_result:
        cv_skills_section = skills_section_result["skills_section"][:6]
        print(f"  ✅ Skills section: {cv_skills_section}")
    else:
        # Fallback: take first 6 keywords_injected from resume
        cv_skills_section = all_keywords_injected[:6]
        print(f"  ⚠️  Skills section selection failed, using first 6 injected keywords: {cv_skills_section}")

    # Save to resume.json (update the file already written)
    resume_output_data = {
        "offer_name":      best_offer_full["name"],
        "offer_company":   best_offer_full["company"],
        "score":           best_scored["score"],
        "selected_indexes": selected_indexes,
        "skills_section":  cv_skills_section,   # ← NEW field
        **resume_result,
    }
    with open(resume_output_path, "w", encoding="utf-8") as f:
        json.dump(resume_output_data, f, ensure_ascii=False, indent=4)
    print(f"  [UPDATED] Resume (with skills_section) → {resume_output_path}")

def _build_experience_selection_prompt(cv_data: dict, best_offer: dict, user_prompt: str) -> str:
    """
    Small focused prompt: just pick the 6 best experience indexes for this offer.
    Kept separate to stay under ~1000 tokens.
    """
    cv_summary = _build_cv_summary_for_selection(cv_data)
    offer_summary = {
        "name": best_offer.get("name", ""),
        "company": best_offer.get("company", ""),
        "missions": best_offer.get("missions", []),
        "competences": best_offer.get("competences", []),
    }
    return f"""Tu es un expert recrutement. Sélectionne les 6 expériences du CV les plus pertinentes pour cette offre.

{cv_summary}

OFFRE:
{json.dumps(offer_summary, ensure_ascii=False, indent=2)}

Réponds UNIQUEMENT avec ce JSON:
{{"skills": [index1, index2, index3, index4, index5, index6]}}"""


def _build_cv_summary_for_selection(cv_data: dict) -> str:
    """Compact CV summary used only for experience selection (no full skills catalog needed)."""
    experiences_summary = []
    for exp in cv_data.get("experiences", []):
        experiences_summary.append({
            "index": exp["index"],
            "name": exp["name"],
            "categorization": exp["categorization"],
            "skills": exp.get("skills", [])
        })
    return f"""EXPÉRIENCES DU CANDIDAT:
{json.dumps(experiences_summary, ensure_ascii=False, separators=(',', ':'))}"""
