import json


def build_skills_section_prompt(
    cv_data: dict,
    best_offer: dict,
    keywords_already_in_cv: list = None,
) -> str:
    """
    Build prompt to select 6 skills for the CV skills section.
    Prioritizes offer-relevant skills NOT already present in experience descriptions.
    """
    skills_catalog = cv_data.get("all_candidate_skills", [{}])[0]

    # Flatten catalog into one list with domain tags
    all_skills = []
    for domain in ["data", "supply_chain"]:
        domain_skills = skills_catalog.get(domain, {})
        for tier in ["t_prio", "prio", "bonus"]:
            for skill in domain_skills.get(tier, []):
                all_skills.append(skill)

    # Deduplicate
    seen = set()
    all_skills_deduped = []
    for s in all_skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            all_skills_deduped.append(s)

    offer_keywords = {
        "competences_offre": best_offer.get("competences_offre", []),
        "missions":          best_offer.get("missions", []),
    }

    already_text = ""
    if keywords_already_in_cv:
        already_text = f"""
*** MOTS-CLÉS DÉJÀ PRÉSENTS DANS LES DESCRIPTIONS DU CV ***:
{json.dumps(keywords_already_in_cv, ensure_ascii=False)}
Ces mots-clés apparaissent déjà dans les expériences. PRIVILÉGIE des compétences DIFFÉRENTES pour maximiser la couverture ATS.
"""

    return f"""Tu es un expert en optimisation de CV pour les logiciels ATS.

*** COMPÉTENCES DU CANDIDAT (catalogue complet) ***:
{json.dumps(all_skills_deduped, ensure_ascii=False)}

*** OFFRE ***:
{json.dumps(offer_keywords, ensure_ascii=False, indent=2)}
{already_text}
*** INSTRUCTIONS ***:
1. Identifie les compétences du CATALOGUE qui correspondent aux besoins de l'offre ("competences_offre" + "missions")
2. PRIORITÉ aux compétences qui sont pertinentes pour l'offre ET pas encore dans "MOTS-CLÉS DÉJÀ PRÉSENTS"
3. Si moins de 6 compétences nouvelles sont pertinentes, complète avec des compétences déjà présentes (la répétition ATS reste utile)
4. Sélectionne exactement 6 compétences

*** ATTENTION ***:
- UNIQUEMENT des compétences du CATALOGUE ci-dessus — n'invente rien
- EXACTEMENT 6, PAS PLUS, PAS MOINS

*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{"skills_section": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6"]}}"""