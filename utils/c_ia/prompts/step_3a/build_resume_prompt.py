import json

def build_resume_prompt(cv_data: dict, best_offer: dict, selected_indexes: list) -> str:
    """
    NEW — Generate a tailored resume for the best offer.
    For each of the selected experiences (by index), the AI rewrites the description
    to naturally inject keywords that match the offer's competences and missions.

    Returns JSON:
    {
      "resume": [
        {
          "index": 3,
          "name": "Stage Data Engineer — Société X",
          "description_tailored": "Développement de pipelines ETL avec Python et SQL...",
          "keywords_injected": ["Python", "ETL", "SQL", "pipeline"]
        },
        ...
      ]
    }
    """
    experiences = cv_data.get("experiences", [])
    skills_catalog = cv_data.get("skills", [])

    # Filter only the selected experiences
    selected_experiences = [
        exp for exp in experiences
        if exp.get("index") in selected_indexes
    ]

    # Build the offer context (structured fields from extraction step)
    offer_context = {
        "name": best_offer.get("name", ""),
        "company": best_offer.get("company", ""),
        "profil_recherche": best_offer.get("profil_recherche", ""),
        "missions": best_offer.get("missions", []),
        "competences": best_offer.get("competences", []),
    }

    return f"""Tu es un expert en recrutement et en optimisation de CV pour les logiciels ATS.

Le candidat postule à cette offre de stage :
{json.dumps(offer_context, ensure_ascii=False, indent=2)}

---

Voici le catalogue complet des compétences du candidat (indexé par domaine et priorité) :
{json.dumps(skills_catalog, ensure_ascii=False, indent=2)}

---

Voici les {len(selected_experiences)} expériences sélectionnées pour ce CV :
{json.dumps(selected_experiences, ensure_ascii=False, indent=2)}

---

INSTRUCTIONS :

1. Identifier les mots-clés de l'offre (champs "competences" et "missions") qui sont pertinents pour cette expérience spécifique.
2. Vérifier que ces mots-clés sont présents dans le catalogue "skills" du candidat — n'invente JAMAIS de compétences que le candidat ne possède pas.
3. Réécrire le champ "description" de l'expérience pour :
   - Intégrer naturellement les mots-clés pertinents (pour maximiser le score ATS)
   - Conserver le sens original et rester factuel
   - Garder un style professionnel et concis (max 3-4 phrases)
   - Ne PAS inventer de chiffres ou de résultats qui ne sont pas dans la description originale

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après) :

***ATTENTION***: LA PREMIERE EXPERIENCE DOIT TOUJOURS AVOIR L'INDEX 1 ET LE NAME "Etudiant - ECAM Lyon" C'EST LA BASE DU CV. LES 5 EXPERIENCES SUIVANTES SONT À OPTIMISER POUR L'OFFRE EN QUESTION SELON LES INSTRUCTIONS CI-DESSUS.
{{
  "resume": [
    {{
      "index": 1,
      "name": "nom exact de l'expérience",
      "description_tailored": "description réécrite avec les mots-clés injectés...",
      "keywords_injected": ["keyword1", "keyword2", "..."]
    }},
    ...
  ]
}}"""
