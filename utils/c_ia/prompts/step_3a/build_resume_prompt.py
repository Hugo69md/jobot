import json

def build_resume_prompt(cv_data: dict, best_offer: dict, experience: dict) -> str:
    """
    Build a prompt to tailor ONE experience description for ATS keyword injection.
    Called once per selected experience.

    Returns JSON:
    {
      "index": 2,
      "name": "Stage - Laboratoire Arrow",
      "description_tailored": "...",
      "keywords_injected": ["keyword1", "keyword2"]
    }
    """
    skills_catalog = cv_data.get("skills", [{}])[0]

    offer_context = {
        "name":             best_offer.get("name", ""),
        "missions":         best_offer.get("missions", []),
        "competences":      best_offer.get("competences", []),
    }

    return f"""Tu es un expert ATS. Tu réécris UNE description d'expérience pour maximiser le score ATS de ce CV.

*** OFFRE ***:
{json.dumps(offer_context, ensure_ascii=False, indent=2)}

*** COMPÉTENCES DU CANDIDAT (catalogue) ***:
{json.dumps(skills_catalog, ensure_ascii=False, indent=2)}

*** EXPÉRIENCE À RÉÉCRIRE ***:
{json.dumps(experience, ensure_ascii=False, indent=2)}

*** INSTRUCTIONS ***:
1. Identifie les mots-clés de l'offre (missions + competences) pertinents pour CETTE expérience spécifique.
2. Vérifie que ces mots-clés sont dans le catalogue skills du candidat
3. Réécris uniquement le champ "description" en :
   - Intégrant naturellement les mots-clés pertinents
   - Conservant le sens original et restant factuel
   - Style professionnel et concis (max 2-3 phrases)
   - N'invente JAMAIS de chiffres ou résultats absents de la description originale

*** ATTENTION ***:
- IL EST INTERDIT D'INVENTER DES COMPÉTENCES POUR LE CANDIDAT.
- NE PAS MODIFIER LA DESCRIPTION DE LA COMPETENCE SI CELA IMPLIQUE D'INVENTER DES COMPÉTENCES

*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{"index": {experience.get("index")}, "name": "{experience.get("name", "")}", "description_tailored": "...", "keywords_injected": ["kw1", "kw2"]}}"""