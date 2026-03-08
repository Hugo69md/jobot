import json


def build_experience_selection_prompt(
    cv_data: dict,
    best_offer: dict,
    candidate_pool_indexes: list,
    n_to_select: int,
    forced_context: list = None,
) -> str:
    """
    Pick the best N experience indexes from a filtered candidate pool.

    Args:
        cv_data: full CV data
        best_offer: enriched offer with offer_industry_type from Step 0
        candidate_pool_indexes: list of experience indexes the IA can choose from
        n_to_select: how many the IA must pick (e.g., 3 if 3 are already forced)
        forced_context: list of already-forced experience names (for IA awareness)
    """
    all_experiences = {exp["index"]: exp for exp in cv_data.get("experiences", [])}

    # Build summary of ONLY the candidate pool
    pool_summary = []
    for idx in candidate_pool_indexes:
        exp = all_experiences.get(idx)
        if exp:
            pool_summary.append({
                "index":          exp["index"],
                "name":           exp["name"],
                "type":           exp.get("type", ""),
                "categorization": exp["categorization"],
                "specific_skills": exp.get("specific_skills", []),
            })

    offer_summary = {
        "name":        best_offer.get("name", ""),
        "company":     best_offer.get("company", ""),
        "missions":    best_offer.get("missions", []),
        "competences_offre": best_offer.get("competences_offre", []),
        "offer_industry_type": best_offer.get("offer_industry_type", []),
    }

    # Context about what's already selected
    forced_text = ""
    if forced_context:
        forced_text = f"""
*** EXPÉRIENCES DÉJÀ S��LECTIONNÉES (ne pas re-sélectionner) ***:
{json.dumps(forced_context, ensure_ascii=False)}
"""

    return f"""*** CONTEXTE ***:
Tu es un expert recrutement. Tu aides un étudiant ingénieur à compléter la sélection d'expériences pour son CV.
{forced_text}
*** EXPÉRIENCES CANDIDATES (pool de sélection) ***:
{json.dumps(pool_summary, ensure_ascii=False, separators=(',', ':'))}

*** OFFRE ***:
{json.dumps(offer_summary, ensure_ascii=False, indent=2)}

*** INSTRUCTIONS ***:
- Sélectionne exactement {n_to_select} expériences (index) parmi le pool ci-dessus.
- Aide toi du champ "type" dans les expériences ET du champ "offer_industry_type" de l'offre pour identifier les domaines communs
- Compare les "missions" et "competences_offre" de l'offre avec les "specific_skills" de CHAQUE expérience du pool
- Choisis celles qui apportent le plus de valeur pour CETTE offre spécifique

*** ATTENTION ***
- EXACTEMENT {n_to_select} EXPÉRIENCES, PAS PLUS, PAS MOINS
- CHOISIS UNIQUEMENT PARMI LES INDEX DU POOL CI-DESSUS

*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{"reasoning": "index X car [raison], index Y car [raison]...", "selected_indexes": [indexA, indexB...]}}"""