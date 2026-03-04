import json

def build_experience_selection_prompt(cv_data: dict, best_offer: dict) -> str:
    """Pick the 6 best experience indexes for this offer."""
    experiences_summary = []
    for exp in cv_data.get("experiences", []):
        experiences_summary.append({
            "index":          exp["index"],
            "name":           exp["name"],
            "type":           exp.get("type", ""),
            "categorization": exp["categorization"],
            "description":    exp.get("description", ""),
            "specific_skills":         exp.get("specific_skills", []),
        })

    offer_summary = {
        "name":        best_offer.get("name", ""),
        "company":     best_offer.get("company", ""),
        "missions":    best_offer.get("missions", []),
        "competences_offre": best_offer.get("competences_offre", []),
    }

    return f"""*** CONTEXTE ***:
Tu es un expert recrutement. Tu aides un étudiant ingénieur à sélectionner ses meilleures expériences pour une offre de stage.

*** EXPÉRIENCES DU CANDIDAT ***:
{json.dumps(experiences_summary, ensure_ascii=False, separators=(',', ':'))}

*** OFFRE ***:
{json.dumps(offer_summary, ensure_ascii=False, indent=2)}

*** INSTRUCTIONS ***:
- Selectionne exactement 6 expériences (index) à mettre en avant dans le CV pour cette offre.
- Check l'entiereté des "experiences" du candidat pour trouver des matches pertinents avec les "missions" et "compétences_offre" requises de l'offre.
- L'index 1 ("Etudiant - ECAM Lyon") est OBLIGATOIRE — inclus-le toujours.
Pour les 5 restantes : 
- Aide toi du champ "type" dans experiences candidat pour identifier le domaine relatif de chaque experiencen du candidat, met le en perspective avec les missions et compétences de l'offre
- Compare les "missions" et "compétences" de l'offre avec les "specific_skills" et la "description" de CHAQUE expérience.
- Choisis celles qui apportent le plus de valeur pour CETTE offre spécifique

*** ATTENTION ***
- TU DOIS PRIORISER LES MEILLEURS MATCHS
- EN AUCUN CAS IL DOIT Y AVOIR PLUS OU MOINS DE 6 EXPERIENCES


*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{"reasoning": "index V car [raison], index W car [raison], index X car [raison], index Y car [raison], index Z car [raison]", "selected_indexes": [1, indexA, indexB, indexC, indexD, indexE]}}"""