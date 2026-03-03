import json

def build_skills_section_prompt(
    cv_data: dict,
    best_offer: dict,
    resume_data: dict,
) -> str:
    """
    STEP 4 — Pick the 6 best skills to display in the CV skills section.

    Inputs:
      - all keywords_injected from resume_data (already validated against cv.json)
      - offer competences + missions (from enrichment step)
      - full skills catalog from cv.json (as candidate pool)

    Output JSON:
    {
      "skills_section": ["Python", "pandas", "Supply Chain", "KPI", "Excel avancé", "Scrapy"]
    }
    → exactly 6 items, ordered by relevance to the offer (most relevant first)
    """

    # Flatten ALL keywords_injected across all tailored experiences
    all_keywords_injected = []
    seen = set()
    for exp_entry in resume_data.get("resume", []):
        for kw in exp_entry.get("keywords_injected", []):
            kw_norm = kw.strip()
            if kw_norm and kw_norm.lower() not in seen:
                seen.add(kw_norm.lower())
                all_keywords_injected.append(kw_norm)

    # Full skills catalog flattened (candidate pool the AI can pick from)
    skills_catalog = cv_data.get("skills", [{}])[0]
    all_candidate_skills = []
    for domain in ["data", "supply_chain"]:
        domain_skills = skills_catalog.get(domain, {})
        for tier in ["t_prio", "prio", "bonus"]:
            all_candidate_skills.extend(domain_skills.get(tier, []))
    # Deduplicate while preserving order
    seen2 = set()
    all_candidate_skills_deduped = []
    for s in all_candidate_skills:
        if s.lower() not in seen2:
            seen2.add(s.lower())
            all_candidate_skills_deduped.append(s)

    offer_context = {
        "name":        best_offer.get("name", ""),
        "company":     best_offer.get("company", ""),
        "missions":    best_offer.get("missions", []),
        "competences": best_offer.get("competences", []),
    }

    return f"""Tu es un expert en optimisation de CV pour les logiciels ATS.

CONTEXTE : Le candidat postule à cette offre de stage :
{json.dumps(offer_context, ensure_ascii=False, indent=2)}

---

MOTS-CLÉS INJECTÉS dans les descriptions du CV (déjà validés comme compétences réelles du candidat) :
{json.dumps(all_keywords_injected, ensure_ascii=False)}

CATALOGUE COMPLET des compétences du candidat (pool de sélection autorisé) :
{json.dumps(all_candidate_skills_deduped, ensure_ascii=False)}

---

INSTRUCTIONS :
Tu dois sélectionner EXACTEMENT 6 compétences techniques à afficher dans la section "Compétences" du CV.

Règles de sélection :
1. Priorité maximale aux compétences présentes à la fois dans "MOTS-CLÉS INJECTÉS" ET dans "competences" ou "missions" de l'offre — ce sont les mots-clés ATS les plus importants
2. Priorité secondaire aux compétences présentes dans "MOTS-CLÉS INJECTÉS" mais pas encore dans l'offre — elles montrent la polyvalence du candidat
3. En cas d'égalité, préfère les compétences les plus reconnues/valorisantes (ex: Python > "data processing")
4. Ne sélectionne QUE des compétences présentes dans le "CATALOGUE COMPLET" — n'invente rien
5. Retourne les 6 compétences triées du plus pertinent au moins pertinent

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après) :
{{"skills_section": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6"]}}"""


