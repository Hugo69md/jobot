import json

def build_experience_selection_prompt(cv_data: dict, best_offer: dict) -> str:
    """Pick the 6 best experience indexes for this offer."""
    experiences_summary = []
    for exp in cv_data.get("experiences", []):
        experiences_summary.append({
            "index":          exp["index"],
            "name":           exp["name"],
            "categorization": exp["categorization"],
            "description":    exp.get("description", ""),
            "skills":         exp.get("skills", []),
        })

    offer_summary = {
        "name":        best_offer.get("name", ""),
        "company":     best_offer.get("company", ""),
        "missions":    best_offer.get("missions", []),
        "competences": best_offer.get("competences", []),
    }

    return f"""*** CONTEXTE ***:
Tu es un expert recrutement. Tu aides un étudiant ingénieur à sélectionner ses meilleures expériences pour une offre de stage.

*** EXPÉRIENCES DU CANDIDAT ***:
{json.dumps(experiences_summary, ensure_ascii=False, separators=(',', ':'))}

*** OFFRE ***:
{json.dumps(offer_summary, ensure_ascii=False, indent=2)}

*** INSTRUCTIONS ***:
- Selectionne exactement 6 expériences (index) à mettre en avant dans le CV pour cette offre spécifique.
- Check l'entiereté des experiences du candidat pour trouver des matches pertinents avec les missions et compétences requises de l'offre.
- L'index 1 ("Etudiant - ECAM Lyon") est OBLIGATOIRE — inclus-le toujours.
- Pour les 5 restantes : compare les missions et compétences de l'offre avec les skills et description de CHAQUE expérience.
- Choisis les 5 qui apportent le plus de valeur pour CETTE offre spécifique

*** ATTENTION ***
- TU DOIS PRIORISER LES MEILLEURS MATCHS
- EN AUCUN CAS IL DOIT Y AVOIR PLUS OU MOINS DE 6 EXPERIENCES


*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{"reasoning": "index V car [raison], index W car [raison], index X car [raison], index Y car [raison], index Z car [raison]", "skills": [1, indexA, indexB, indexC, indexD, indexE]}}"""