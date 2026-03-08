import json


def build_resume_prompt(
    cv_data: dict,
    best_offer: dict,
    experience: dict,
    already_injected: list = None,
) -> str:
    """
    Build a prompt to tailor ONE experience description for ATS keyword injection.
    Called once per selected experience.
    """
    skills_catalog = cv_data.get("all_candidate_skills", [{}])[0]

    # Filter catalog to only domains matching this experience's type
    exp_types = experience.get("type", [])
    filtered_skills = []

    for exp_type in exp_types:
        domain_key = exp_type.lower().replace(" ", "_")
        if domain_key in skills_catalog:
            domain_skills = skills_catalog[domain_key]
            for tier in ["t_prio", "prio", "bonus"]:
                filtered_skills.extend(domain_skills.get(tier, []))

    # Deduplicate
    seen = set()
    filtered_skills_deduped = []
    for s in filtered_skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            filtered_skills_deduped.append(s)

    offer_context = {
        "name":             best_offer.get("name", ""),
        "missions":         best_offer.get("missions", []),
        "competences_offre":      best_offer.get("competences_offre", []),
    }

    # Already injected keywords block
    already_text = ""
    if already_injected:
        already_text = f"""
*** MOTS-CLÉS DÉJÀ INJECTÉS DANS D'AUTRES EXPÉRIENCES (NE PAS RÉUTILISER) ***:
{json.dumps(already_injected, ensure_ascii=False)}
"""

    return f"""Tu es un expert ATS. Tu réécris UNE description d'expérience pour maximiser le score ATS de ce CV.

*** OFFRE ***:
{json.dumps(offer_context, ensure_ascii=False, indent=2)}

*** COMPÉTENCES VALIDÉES DU CANDIDAT (pour cette expérience uniquement) ***:
{json.dumps(filtered_skills_deduped, ensure_ascii=False)}
{already_text}
*** EXPÉRIENCE À RÉÉCRIRE ***:
- Nom: {experience.get("name", "")}
- Description originale: {experience.get("description", "")}
- Compétences spécifiques: {json.dumps(experience.get("specific_skills", []), ensure_ascii=False)}

*** INSTRUCTIONS ***:
1. Identifie les mots-clés de l'offre ("missions" + "competences_offre") QUI APPARAISSENT AUSSI dans "COMPÉTENCES VALIDÉES DU CANDIDAT"
2. EXCLUS tout mot-clé listé dans "MOTS-CLÉS DÉJÀ INJECTÉS" — ils sont déjà dans le CV
3. EXCLUS tout mot-clé déjà présent dans la description originale ou dans specific_skills — pas besoin de le réinjecter
4. Réécris la description en :
   - Intégrant naturellement UNIQUEMENT les mots-clés validés restants
   - Conservant le sens original — ne change pas ce que le candidat a fait
   - Style professionnel et concis (max 2-3 phrases)
   - N'invente JAMAIS de chiffres ou résultats

*** ATTENTION ***:
- Si AUCUN nouveau mot-clé ne peut être injecté, retourne la description ORIGINALE sans modification
- keywords_injected ne doit contenir QUE des NOUVEAUX mots-clés (pas déjà injectés, pas déjà présents)

*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{
  "index": {experience.get("index", 0)},
  "name": "{experience.get("name", "")}",
  "reasoning": "mot-clé X pertinent car [raison], mot-clé Y exclu car déjà injecté",
  "description_tailored": "...",
  "keywords_injected": ["keyword1"]
}}"""