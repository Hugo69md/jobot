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

    return f"""

*** CONTEXTE ***:    
Tu es un expert recrutement et tu apporte ton expertise à un etudiant ingénieur pour trouver un stage

*** EXPÉRIENCES DU CANDIDAT ***:
{json.dumps(experiences_summary, ensure_ascii=False, separators=(',', ':'))}

*** OFFRE ***:
{json.dumps(offer_summary, ensure_ascii=False, indent=2)}

*** INSTRUCTIONS ***:
- Tu dois d'abord regarder toutes les experiences du candidat avant de faire ton choix
- Tu dois selectionner Exactement 6 experiences (pas plus, pas moins)
- Tu dois TOUJOURS incorporer l'experience avec l'index numero 1 , "name" : 'Etudiant - ECAM Lyon', même si ce n'est pas pertinent pour l'offre.
Pour les 5 expériences restantes, tu dois :
1. Mettre en perspective les missions et competences de l'offre avec les skills et description de chaque expérience du candidat
2. Selectionner les experiences les plus pertinentes pour l'offre, même si elles ne sont pas parfaitement alignées

*** ATTENTION ***: 
1. NE DOIS PAS SEULEMENT SE FOCALISER SUR LES EXPERIENCES QUI ONT DES COMPETENCES MATCHANT EXACTEMENT CELLES DE L'OFFRE, MAIS AUSSI PRENDRE EN COMPTE LA PERTINENCE GLOBALE DE L'EXPERIENCE PAR RAPPORT AUX MISSIONS PROPOSÉES DANS L'OFFRE. IL PEUT Y AVOIR DES EXPERIENCES TRÈS PERTINENTES MÊME S'IL N'Y A PAS DE MATCH DE COMPETENCES PARFAIT, CAR ELLES PEUVENT AVOIR DES TÂCHES OU RÉALISATIONS TRANSVERSALES UTILES POUR LE POSTE.
2. LA PREMIERE EXPERIENCE DOIT TOUJOURS AVOIR L'INDEX 1 ET LE NAME "Etudiant - ECAM Lyon" C'EST LA BASE DU CV. LES 5 EXPERIENCES SUIVANTES SONT À OPTIMISER POUR L'OFFRE EN QUESTION SELON LES INSTRUCTIONS CI-DESSUS.

*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{"skills": [1, index, ... last Index ]}}"""