import os
import json
from utils.c_ia.ollama_client import query_ollama_json
from utils.c_ia.prompts.step_0.build_domain_classification_prompt import build_domain_classification_prompt
from utils.c_ia.prompts.step_1.build_extraction_prompt import build_extraction_prompt
from utils.c_ia.prompts.step_2.build_single_offer_scoring_prompt import build_single_offer_scoring_prompt
from utils.c_ia.prompts.step_3a.build_experience_selection_prompt import build_experience_selection_prompt
from utils.c_ia.prompts.step_3a.build_resume_prompt import build_resume_prompt
from utils.c_ia.prompts.step_3b.build_cover_letter_prompt import build_cover_letter_prompt
from utils.c_ia.prompts.step_4.build_skills_section_prompt import build_skills_section_prompt


SCORE_THRESHOLD = 75  # Only generate CV + cover letter for offers above this score

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
    dropped_count     = 0

    for i, offer in enumerate(internships_data):
        offer_name = offer.get("name", f"offer_{i}")
        print(f"  [{i+1}/{len(internships_data)}] {offer_name[:60]}...", end=" ")

        classification_prompt = build_domain_classification_prompt(offer)
        classification = query_ollama_json(classification_prompt, temperature=0.0, num_predict=64)

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
        extraction = query_ollama_json(extraction_prompt, temperature=0.1, num_predict=1024)

        if extraction:
            enriched_offer = {
                **offer,
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

    enriched_path = os.path.join(output_dir, "internships_enriched.json")
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(enriched_offers, f, ensure_ascii=False, indent=4)
    print(f"\n  [SAVED] Enriched offers → {enriched_path}")

    if not enriched_offers:
        print("  [ERROR] No offers left after extraction — aborting.")
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
        result = query_ollama_json(prompt, temperature=0.1, num_predict=650)

        if result and all(k in result for k in ("C1", "C2", "C3", "C4", "C5")):
            c1 = result["C1"].get("score", 0)
            c2 = result["C2"].get("score", 0)
            c3 = result["C3"].get("score", 0)
            c4 = result["C4"].get("score", 0)
            c5 = result["C5"].get("score", 0)
            final_score = round(c1 + c2 + c3 + c4 + c5, 1)

            score_entry = {
                "name":    result.get("name", offer_name),
                "score":   int(final_score),
                "C1": result["C1"],
                "C2": result["C2"],
                "C3": result["C3"],
                "C4": result["C4"],
                "C5": result["C5"],
            }
            print(f"  ✅ Score: {final_score}/100  "
                  f"(C1={c1}/40 C2={c2}/10 C3={c3}/20 C4={c4}/15 C5={c5}/15)")
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

    # ══════════════════════════════════════════════════════════════
    # STEP 3 — Filter offers above threshold + build lookup
    # ══════════════════════════════════════════════════════════════
    scored_above_threshold = [s for s in scoring_list if s["score"] >= SCORE_THRESHOLD]

    if not scored_above_threshold:
        print(f"\n  [WARN] No offer scored ≥ {SCORE_THRESHOLD} — using best offer only.")
        scored_above_threshold = [scoring_list[0]]

    print(f"\n  [STEP 3] {len(scored_above_threshold)} offer(s) with score ≥ {SCORE_THRESHOLD} → generating CVs...")

    # Build a lookup dict: offer name → full enriched offer data
    enriched_lookup = {offer.get("name", ""): offer for offer in enriched_offers}

    # Will accumulate all match entries for match.json
    all_matches = []

    # ══════════════════════════════════════════════════════════════
    # LOOP — Run STEP 3a + 3b + 4 for each qualifying offer
    # ══════════════════════════════════════════════════════════════
    for j, scored in enumerate(scored_above_threshold):
        offer_full = enriched_lookup.get(scored["name"])
        if offer_full is None:
            print(f"  [ERROR] Could not find full data for: {scored['name']} — skipping")
            continue

        offer_full = {**offer_full, "score": scored["score"]}
        offer_name = offer_full["name"]
        offer_type = offer_full.get("offer_type", "data")

        print(f"\n  {'═' * 56}")
        print(f"  [{j+1}/{len(scored_above_threshold)}] Processing: {offer_name[:55]}")
        print(f"  Score: {scored['score']}/100 | Type: {offer_type}")
        print(f"  {'═' * 56}")

                # ── STEP 3a — Select experiences ─────────────────────────────
        print("\n  [STEP 3a-1] Selecting experience indexes...")

        selection_prompt = build_experience_selection_prompt(cv_data, offer_full)
        selection_result = query_ollama_json(selection_prompt, temperature=0.1, num_predict=800)

        if selection_result and "skills" in selection_result:
            selected_indexes    = selection_result["skills"]
            selection_reasoning = selection_result.get("reasoning", "")
            print(f"  ✅ Selected indexes: {selected_indexes}")
            print(f"  💬 Reasoning: {selection_reasoning}")
        else:
            selected_indexes    = [exp["index"] for exp in cv_data.get("experiences", [])][:6]
            selection_reasoning = "fallback"
            print(f"  ⚠️  Selection failed, fallback: {selected_indexes}")

        # Build the list of actual experience objects from the selected indexes
        exp_lookup         = {exp["index"]: exp for exp in cv_data.get("experiences", [])}
        selected_experiences = [exp_lookup[i] for i in selected_indexes if i in exp_lookup]

        # ── STEP 3a-2 — Tailor each experience individually ──────────
        print(f"\n  [STEP 3a-2] Tailoring {len(selected_experiences)} descriptions (1 call each)...")

        tailored_resume = []
        all_keywords_injected = []
        seen_kw = set()

        for exp in selected_experiences:
            exp_idx  = exp.get("index")
            exp_name = exp.get("name", f"index {exp_idx}")
            print(f"    → [{exp_idx}] {exp_name[:45]}...", end=" ", flush=True)

            resume_prompt        = build_resume_prompt(cv_data, offer_full, exp)
            resume_result_single = query_ollama_json(resume_prompt, temperature=0.1, num_predict=400)

            if resume_result_single and "description_tailored" in resume_result_single:
                tailored_resume.append(resume_result_single)
                kw = resume_result_single.get("keywords_injected", [])
                print(f"✅ {kw}")
                for k in kw:
                    k_norm = k.strip()
                    if k_norm and k_norm.lower() not in seen_kw:
                        seen_kw.add(k_norm.lower())
                        all_keywords_injected.append(k_norm)
            else:
                # Fallback: keep original description untouched
                tailored_resume.append({
                    "index":               exp_idx,
                    "name":                exp.get("name", ""),
                    "description_tailored": exp.get("description", ""),
                    "keywords_injected":   [],
                })
                print("⚠️  failed, using original")

        resume_result = {"resume": tailored_resume}
        print(f"  [INFO] {len(tailored_resume)} descriptions ready | "
              f"{len(all_keywords_injected)} unique keywords: {all_keywords_injected}")
        
        # Flatten injected keywords (used in STEP 4)
        all_keywords_injected = []
        seen_kw = set()
        for exp_entry in resume_result.get("resume", []):
            for kw in exp_entry.get("keywords_injected", []):
                kw_norm = kw.strip()
                if kw_norm and kw_norm.lower() not in seen_kw:
                    seen_kw.add(kw_norm.lower())
                    all_keywords_injected.append(kw_norm)

        # ── STEP 3b — Cover letter ────────────────────────────────
        print("\n  [STEP 3b] Generating cover letter...")

        cover_letter_prompt = build_cover_letter_prompt(cv_data, offer_full, USER_PROMPT)
        cover_letter_result = query_ollama_json(cover_letter_prompt, temperature=0.3, num_predict=4096)

        if cover_letter_result is None:
            print("  ⚠️  Cover letter generation failed")
            cover_letter_result = {"cover_letter": {"name": offer_name, "error": "generation_failed"}}

        # ── STEP 4 — Skills section ───────────────────────────────
        print("\n  [STEP 4] Selecting 6 skills for CV skills section...")

        skills_section_prompt = build_skills_section_prompt(cv_data, offer_full, resume_result)
        skills_section_result = query_ollama_json(skills_section_prompt, temperature=0.1, num_predict=128)

        if skills_section_result and "skills_section" in skills_section_result:
            cv_skills_section = skills_section_result["skills_section"][:6]
            print(f"  ✅ Skills section: {cv_skills_section}")
        else:
            cv_skills_section = all_keywords_injected[:6]
            print(f"  ⚠️  Fallback: {cv_skills_section}")

        # ── SAVE — one resume.json per offer ─────────────────────
        cover_letter_data  = cover_letter_result.get("cover_letter", {})
        safe_name          = _sanitize_filename(f"{offer_full.get('company', '')}_{offer_name}")
        resume_output_path = os.path.join(output_dir, f"resume_{safe_name}.json")

        with open(resume_output_path, "w", encoding="utf-8") as f:
            json.dump({
                "offer_name":       offer_name,
                "offer_company":    offer_full.get("company", ""),
                "offer_type":       offer_type,
                "score":            scored["score"],
                "selected_indexes": selected_indexes,
                "selection_reasoning":  selection_reasoning,
                "skills_section":   cv_skills_section,
                "cover_letter":     cover_letter_data.get("text", ""),
                **resume_result,
            }, f, ensure_ascii=False, indent=4)
        print(f"  [SAVED] Resume → {resume_output_path}")

        all_matches.append({
            "name":         offer_name,
            "URL":          offer_full.get("URL", ""),
            "company":      offer_full.get("company", ""),
            "location":     offer_full.get("location", ""),
            "offer_type":   offer_type,
            "score":        scored["score"],
            "skills":       selected_indexes,
            "skills_section": cv_skills_section,
            "cover_letter": cover_letter_data.get("text", ""),
            "resume":       tailored_resume,
        })

    # ════���═════════════════════════════════════════════════════════
    # SAVE — match.json (all qualifying offers, for d_files_gen)
    # ══════════════════════════════════════════════════════════════
    match_output_path = os.path.join(output_dir, "match.json")
    with open(match_output_path, "w", encoding="utf-8") as f:
        json.dump({"match": all_matches}, f, ensure_ascii=False, indent=4)
    print(f"\n  [SAVED] Match → {match_output_path} ({len(all_matches)} offers)")

    # ══════════════════════════════════════════════════════════════
    # DONE
    # ══════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("[C_IA] AI analysis complete!")
    print(f"  Offers scraped:   {len(internships_data)}")
    print(f"  Offers kept:      {len(enriched_offers)} ({dropped_count} dropped)")
    print(f"  Offers scored:    {len(scoring_list)}")
    print(f"  Offers ≥ {SCORE_THRESHOLD}/100:  {len(all_matches)} → CV + LM generated")
    print("=" * 60)


def _sanitize_filename(name: str) -> str:
    keepchars = (" ", "-", "_")
    name = "".join(c for c in name if c.isalnum() or c in keepchars).rstrip()
    return name[:60]