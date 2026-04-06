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

*** COMPÉTENCES VALIDÉES DU CANDIDAT ***:
{json.dumps(filtered_skills_deduped, ensure_ascii=False)}
{already_text}
*** EXPÉRIENCE À RÉÉCRIRE ***:
- Nom: {experience.get("name", "")}
- Description originale: {experience.get("description", "")}
- Compétences spécifiques: {json.dumps(experience.get("specific_skills", []), ensure_ascii=False)}

*** INFORMATIONS IMPORTANTES ***:

- les logiciels ATS ne cherchent pas le sens. Ils cherchent le token exact. : ("Gestion de projet" et "pilotage de projet" = même chose pour un humain. Pour l'ATS = deux tokens différents. Score : 0 pour celui qui n'est pas dans l'offre. Il faut donc injecter les mots-clés EXACTS de l'offre, meme si le mot clé present dans "all_candidate_skills" est un synonyme de ce qui est dans l'offre, il faut privilégier la formulation de l'offre pour maximiser le matching ATS)

*** INSTRUCTIONS ***:
1. Identifie les mots-clés de l'offre ("competences_offre") QUI sont similaire à ceux present dans "COMPÉTENCES VALIDÉES DU CANDIDAT"
2. EXCLUS tout mot-clé listé dans "MOTS-CLÉS DÉJÀ INJECTÉS" — ils sont déjà dans le CV
3. EXCLUS tout mot-clé déjà présent dans la description originale ou dans specific_skills — pas besoin de le réinjecter
4. Selectionne le ou les mots-clés restants les PLUS PERTINENTS pour cette expérience, garde la forme presente dans l'offre comme precisé dans "INFORMATIONS IMPORTANTES" 
5. Réécris la description en :
   - Intégrant naturellement UNIQUEMENT les mots-clés validés restants
   - Conservant le sens original — ne change pas ce que le candidat a fait
   - Style professionnel et concis (max 2-3 phrases)
   - N'invente JAMAIS de chiffres ou résultats

*** ATTENTION ***:
- il est possible que la description ne soit pas modifiable car aucun mot-clé n'est pertinent, dans ce cas : retourne la description ORIGINALE sans modification
- keywords_injected ne doit contenir QUE des NOUVEAUX mots-clés (pas déjà injectés, pas déjà présents)
- Le format de la dercription doit etre naturel et professionnel, pas une liste de mots-clés

*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{
  "index": {experience.get("index", 0)},
  "name": "{experience.get("name", "")}",
  "reasoning": "mot-clé X pertinent car [raison], mot-clé Y pertinent car [raison]...",
  "description_tailored": "...",
  "keywords_injected": ["keyword1"]
}}"""