import os
import json
from utils.c_ia.ollama_client import query_ollama_json
from utils.c_ia.cloud_client import query_cloud_json
from utils.c_ia.preselect_experiences import preselect_experiences
from utils.c_ia.prompts.step_0.build_domain_classification_prompt import build_domain_classification_prompt
from utils.c_ia.prompts.step_1.build_extraction_prompt import build_extraction_prompt
from utils.c_ia.prompts.step_2.build_single_offer_scoring_prompt import build_single_offer_scoring_prompt
from utils.c_ia.prompts.step_3a.build_experience_selection_prompt import build_experience_selection_prompt
from utils.c_ia.prompts.step_3a.build_resume_prompt import build_resume_prompt
from utils.c_ia.prompts.step_3b.build_cover_letter_prompt import build_cover_letter_prompt
from utils.c_ia.prompts.step_4.build_skills_section_prompt import build_skills_section_prompt


SCORE_THRESHOLD = 80  # Only generate CV + cover letter for offers above this score

USER_PROMPT = (
    "Je suis Hugo MANIPOUD, étudiant en 5ème année d'école d'ingénieur à l'ECAM Lyon. "
    "Je cherche un stage de fin d'études de 4 à 6 mois à partir de juin 2026, "
    "dans le domaine de la Data (Data Analyst, Data Engineer, Data Science) "
    "OU de la Supply Chain (planification, logistique, gestion des stocks, prévision de la demande). "
    "Je maîtrise Python, Excel avancé, pandas, numpy, matplotlib, seaborn, scikitlearn, "
    "et j'ai une expérience en supply chain (stage chez Arrow, stage chez Amazon). "
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
        classification = query_ollama_json(classification_prompt, temperature=0.0, num_predict=128)

        domain = classification.get("domain", "") if classification else ""
        offer_industry_type = classification.get("type", []) if classification else []
        offer_sector = classification.get("sector", []) if classification else []

        if domain not in ("data", "supply_chain"):
            print(f"❌ DROPPED (domain='{domain}')")
            dropped_count += 1
            continue

        classified_offers.append({
            **offer,
            "offer_type": domain,
            "offer_industry_type": offer_industry_type,
            "offer_sector": offer_sector,
        })
        print(f"✅ {domain} | industry: {offer_industry_type} | sector: {offer_sector}")

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
                "competences_offre":      extraction.get("competences_offre", []),
            }
            print(f"  ✅ {enriched_offer['offer_type']} | "
                  f"{len(enriched_offer['competences_offre'])} skills | "
                  f"{len(enriched_offer['missions'])} missions")
        else:
            enriched_offer = {
                **offer,
                "profil_recherche": "",
                "missions":         [],
                "competences_offre":      [],
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

        prompt = build_single_offer_scoring_prompt(cv_data, offer)
        result = query_ollama_json(prompt, temperature=0.0, num_predict=1000)

        if result and all(k in result for k in ("C1", "C2", "C3", "C4", "C5")):
            final_score = _compute_score(result)

            score_entry = {
                "name":    result.get("name", offer_name),
                "score":   final_score,
                "C1": result["C1"],
                "C2": result["C2"],
                "C3": result["C3"],
                "C4": result["C4"],
                "C5": result["C5"],
            }
            c1 = min(result["C1"].get("score", 0), 40)
            c2 = min(result["C2"].get("score", 0), 10)
            c3 = min(result["C3"].get("score", 0), 20)
            c4 = min(result["C4"].get("score", 0), 15)
            c5 = min(result["C5"].get("score", 0), 15)
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

    # Build lookup early — needed for Step 2b re-scoring
    enriched_lookup = {offer.get("name", ""): offer for offer in enriched_offers}

    # ══════════════════════════════════════════════════════════════
    # STEP 2b — Re-score borderline offers (below threshold)
    # ══════════════════════════════════════════════════════════════
    scored_above_threshold = [s for s in scoring_list if s["score"] >= SCORE_THRESHOLD]
    scored_below_threshold = [s for s in scoring_list if s["score"] < SCORE_THRESHOLD]

    rescued_count = 0

    if scored_below_threshold:
        print(f"\n  [STEP 2b] Re-scoring {len(scored_below_threshold)} borderline offers (score < {SCORE_THRESHOLD})...")

        for i, scored_entry in enumerate(scored_below_threshold):
            offer_name   = scored_entry["name"]
            score_r1     = scored_entry["score"]
            offer_for_rescore = enriched_lookup.get(offer_name)
            if offer_for_rescore is None:
                continue

            print(f"\n  [2b] [{i+1}/{len(scored_below_threshold)}] Re-scoring: {offer_name[:55]}... (R1={score_r1})")

            # ── Round 2 ──
            prompt_r2 = build_single_offer_scoring_prompt(cv_data, offer_for_rescore)
            result_r2 = query_ollama_json(prompt_r2, temperature=0.0, num_predict=1000)
            score_r2  = _compute_score(result_r2) if result_r2 and all(k in result_r2 for k in ("C1", "C2", "C3", "C4", "C5")) else 0

            print(f"    R2 score: {score_r2}/100", end=" ")

            if score_r2 < SCORE_THRESHOLD:
                print(f"→ ❌ DROPPED (R1={score_r1}, R2={score_r2})")
                continue

            print(f"→ ✅ R2 passed, running R3...")

            # ── Round 3 ──
            prompt_r3 = build_single_offer_scoring_prompt(cv_data, offer_for_rescore)
            result_r3 = query_ollama_json(prompt_r3, temperature=0.0, num_predict=1000)
            score_r3  = _compute_score(result_r3) if result_r3 and all(k in result_r3 for k in ("C1", "C2", "C3", "C4", "C5")) else 0

            print(f"    R3 score: {score_r3}/100", end=" ")

            if score_r3 >= SCORE_THRESHOLD:
                avg_score = int((score_r2 + score_r3) / 2)
                print(f"→ ✅ RESCUED (2/3 passed, avg={avg_score})")

                scored_entry["score"] = avg_score
                scored_entry["rescue_detail"] = {
                    "R1": score_r1,
                    "R2": score_r2,
                    "R3": score_r3,
                    "passes": 2,
                    "avg": avg_score,
                }
                scored_above_threshold.append(scored_entry)
                rescued_count += 1
            else:
                print(f"→ ❌ DROPPED (only 1/3 passed: just R2)")

        print(f"\n  [STEP 2b] Rescued {rescued_count} / {len(scored_below_threshold)} borderline offers")

        # Re-sort after adding rescued offers
        scored_above_threshold.sort(key=lambda x: x["score"], reverse=True)

        # Save updated scoring.json with rescue info
        rescued_names = {e["name"] for e in scored_above_threshold if "rescue_detail" in e}
        all_scoring_final = scored_above_threshold + [
            s for s in scored_below_threshold if s["name"] not in rescued_names
        ]
        all_scoring_final.sort(key=lambda x: x["score"], reverse=True)
        with open(os.path.join(output_dir, "scoring.json"), "w", encoding="utf-8") as f:
            json.dump({"scoring": all_scoring_final}, f, ensure_ascii=False, indent=4)

    # ══════════════════════════════════════════════════════════════
    # STEP 3 — Filter offers above threshold + build lookup
    # ══════════════════════════════════════════════════════════════
    if not scored_above_threshold:
        print(f"\n  [WARN] No offer scored ≥ {SCORE_THRESHOLD} — using best offer only.")
        scored_above_threshold = [scoring_list[0]]

    print(f"\n  [STEP 3] {len(scored_above_threshold)} offer(s) with score ≥ {SCORE_THRESHOLD} → generating CVs...")

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

        # ── STEP 3a-1 — Pre-select + select experiences ──────────────
        print("\n  [STEP 3a-1] Pre-selecting experiences...")

        preselection = preselect_experiences(cv_data, offer_full)
        forced_indexes = preselection["forced_indexes"]
        remaining_pool = preselection["remaining_pool"]
        needed_from_ia = preselection["needed_from_ia"]
        skip_ia        = preselection["skip_ia"]

        print(f"  [PRE-SELECT] offer_type={offer_type}")
        print(f"  [PRE-SELECT] Forced: {forced_indexes} ({len(forced_indexes)} exp)")
        print(f"  [PRE-SELECT] Pool for IA: {remaining_pool} ({len(remaining_pool)} exp)")
        print(f"  [PRE-SELECT] IA must pick: {needed_from_ia} | Skip IA: {skip_ia}")

        exp_lookup = {exp["index"]: exp for exp in cv_data.get("experiences", [])}

        if skip_ia:
            # Exactly 6 matching — no IA needed
            selected_indexes = forced_indexes[:6]
            selection_reasoning = "pre-selection: exactly 6 experiences match offer_type"
            print(f"  ✅ Skipped IA — direct selection: {selected_indexes}")

        elif needed_from_ia == 6 and not forced_indexes:
            # More than 6 matched offer_type → IA picks best 6 from all matching
            pool_for_ia = remaining_pool
            pool_experiences = [exp_lookup[idx] for idx in pool_for_ia if idx in exp_lookup]
            valid_pool_indexes = set(pool_for_ia)
            ia_selected = None
            selection_reasoning = ""

            for attempt in range(1, 4):
                selection_prompt = build_experience_selection_prompt(
                    pool_experiences, offer_full, 6
                )
                selection_result = query_cloud_json(
                    selection_prompt, temperature=0.0, num_predict=800
                )

                if selection_result and "selected_indexes" in selection_result:
                    raw = selection_result["selected_indexes"]
                    selection_reasoning = selection_result.get("reasoning", "")

                    seen = set()
                    cleaned = []
                    for idx in raw:
                        if idx in valid_pool_indexes and idx not in seen:
                            seen.add(idx)
                            cleaned.append(idx)

                    if len(cleaned) == 6:
                        ia_selected = cleaned
                        print(f"  ✅ IA selected (attempt {attempt}/3): {ia_selected}")
                        break
                    else:
                        print(f"  ⚠️  Attempt {attempt}/3: got {len(cleaned)} indexes {cleaned}, expected 6 — retrying...")
                else:
                    print(f"  ⚠️  Attempt {attempt}/3: selection failed — retrying...")

            if ia_selected is None:
                ia_selected = pool_for_ia[:6]
                selection_reasoning += " | fallback after 3 failed attempts"
                print(f"  ❌ Fallback IA selection: {ia_selected}")

            selected_indexes = ia_selected

        else:
            # Less than 6 matched → forced are locked, IA picks remaining from non-matching pool
            pool_for_ia = remaining_pool
            pool_experiences = [exp_lookup[idx] for idx in pool_for_ia if idx in exp_lookup]
            valid_pool_indexes = set(pool_for_ia)
            ia_selected = None
            selection_reasoning = ""

            for attempt in range(1, 4):
                selection_prompt = build_experience_selection_prompt(
                    pool_experiences, offer_full, needed_from_ia
                )
                selection_result = query_cloud_json(
                    selection_prompt, temperature=0.0, num_predict=800
                )

                if selection_result and "selected_indexes" in selection_result:
                    raw = selection_result["selected_indexes"]
                    selection_reasoning = selection_result.get("reasoning", "")

                    seen = set()
                    cleaned = []
                    for idx in raw:
                        if idx in valid_pool_indexes and idx not in seen:
                            seen.add(idx)
                            cleaned.append(idx)

                    if len(cleaned) == needed_from_ia:
                        ia_selected = cleaned
                        print(f"  ✅ IA selected (attempt {attempt}/3): {ia_selected}")
                        break
                    else:
                        print(f"  ⚠️  Attempt {attempt}/3: got {len(cleaned)} indexes {cleaned}, expected {needed_from_ia} — retrying...")
                else:
                    print(f"  ⚠️  Attempt {attempt}/3: selection failed — retrying...")

            if ia_selected is None:
                ia_selected = pool_for_ia[:needed_from_ia]
                selection_reasoning += " | fallback after 3 failed attempts"
                print(f"  ❌ Fallback IA selection: {ia_selected}")

            selected_indexes = forced_indexes + ia_selected
            selected_indexes = selected_indexes[:6]

        print(f"  ✅ Final selection: {selected_indexes}")
        print(f"  💬 Reasoning: {selection_reasoning}")

        # Build the list of actual experience objects from the selected indexes
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

            resume_prompt = build_resume_prompt(
                cv_data, offer_full, exp,
                already_injected=list(all_keywords_injected),
            )
            resume_result_single = query_ollama_json(
                resume_prompt, temperature=0.1, num_predict=350
            )

            if resume_result_single and "description_tailored" in resume_result_single:
                tailored_resume.append(resume_result_single)
                kw = resume_result_single.get("keywords_injected", [])
                # Filter: only add truly new keywords
                new_kw = []
                for k in kw:
                    k_norm = k.strip()
                    if k_norm and k_norm.lower() not in seen_kw:
                        seen_kw.add(k_norm.lower())
                        all_keywords_injected.append(k_norm)
                        new_kw.append(k_norm)
                print(f"✅ new: {new_kw}" if new_kw else "✅ no new keywords (original kept)")
            else:
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
        cover_letter_result = query_ollama_json(cover_letter_prompt, temperature=0.3, num_predict=1500)

        if cover_letter_result is None:
            print("  ⚠️  Cover letter generation failed")
            cover_letter_result = {"cover_letter": {"name": offer_name, "error": "generation_failed"}}

        # ── STEP 4 — Skills section ───────────────────────────────
        print("\n  [STEP 4] Selecting 6 skills for CV skills section...")

        skills_section_prompt = build_skills_section_prompt(cv_data, offer_full, keywords_already_in_cv=all_keywords_injected,)
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
            "selected_indexes":       selected_indexes,
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
    print(f"  Offers rescued:   {rescued_count} (from Step 2b re-scoring)")
    print(f"  Offers ≥ {SCORE_THRESHOLD}/100:  {len(all_matches)} → CV + LM generated")
    print("=" * 60)


def _compute_score(result: dict) -> int:
    """Extract and cap the C1–C5 scores from a scoring result dict, returning the total (0–100)."""
    c1 = min(result["C1"].get("score", 0), 40)
    c2 = min(result["C2"].get("score", 0), 10)
    c3 = min(result["C3"].get("score", 0), 20)
    c4 = min(result["C4"].get("score", 0), 15)
    c5 = min(result["C5"].get("score", 0), 15)
    return int(c1 + c2 + c3 + c4 + c5)


def _sanitize_filename(name: str) -> str:
    keepchars = (" ", "-", "_")
    name = "".join(c for c in name if c.isalnum() or c in keepchars).rstrip()
    return name[:60]