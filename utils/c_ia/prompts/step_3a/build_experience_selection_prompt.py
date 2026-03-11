import json


def build_experience_selection_prompt(
    pool_experiences: list,
    best_offer: dict,
    n_to_select: int,
) -> str:
    """
    Pick the best N experience indexes from a pre-filtered pool.

    Args:
        pool_experiences: list of experience dicts (already filtered, only pool)
        best_offer: enriched offer with offer_industry_type from Step 0
        n_to_select: how many the IA must pick
    """
    # Build compact summary — only fields needed for selection
    pool_summary = []
    for exp in pool_experiences:
        pool_summary.append({
            "index":           exp["index"],
            "name":            exp["name"],
            "type":            exp.get("type", ""),
            "role":            exp.get("role", ""),
            "description":     exp.get("description", "")[:150],
            "categorization":  exp["categorization"],
            "specific_skills": exp.get("specific_skills", []),
        })

    offer_summary = {
        "name":                best_offer.get("name", ""),
        "company":             best_offer.get("company", ""),
        "missions":            best_offer.get("missions", []),
        "competences_offre":   best_offer.get("competences_offre", []),
        "offer_industry_type": best_offer.get("offer_industry_type", []),
    }

    valid_indexes_list = [exp["index"] for exp in pool_summary]

    return f"""*** CONTEXTE ***:
Tu es un expert recrutement. Tu aides un étudiant ingénieur à compléter la sélection d'expériences pour son CV.
D'autres expériences ont déjà été sélectionnées pour ce CV. Tu dois choisir parmi le pool ci-dessous UNIQUEMENT.

*** EXPÉRIENCES CANDIDATES (pool de sélection) ***:
{json.dumps(pool_summary, ensure_ascii=False, separators=(',', ':'))}

*** INDEX VALIDES ***: {valid_indexes_list}

*** OFFRE ***:
{json.dumps(offer_summary, ensure_ascii=False, indent=2)}

*** INSTRUCTIONS ***:
- Sélectionne exactement {n_to_select} expériences parmi les INDEX VALIDES ci-dessus: {valid_indexes_list}
- Aide toi du champs "role" de chaque experience pour comprendre quel etait mon role dans cette experience et comment ce role peut il etre utile à la mission du stage proposé dans l'offre
- Aide toi du champs "type" de chaque experience pour comprendre le domaine de cette experience et comment ce domaine peut il être utile à la mission du stage proposé dans l'offre
- Aide toi du champs "description" de chaque experience pour comprendre les missions réalisées dans cette experience et comment ces missions peuvent elles être utiles à la mission du stage proposé dans l'offre
- Aide toi du champ "offer_industry_type" de l'offre pour identifier les domaines communs
- fais ta selection en suivant cette logique : role > type > description > specific_skills, 
- Compare les "missions" et "competences_offre" de l'offre avec les "specific_skills" de CHAQUE expérience du pool
- Choisis celles qui apportent le plus de valeur pour CETTE offre spécifique, certaines experiences apportent des soft skills non negligeables même si elles n'ont pas de match de compétences directes avec l'offre, prends en compte ce facteur dans ta sélection (ex : concours sur 1an avec 300h de travail, même si ce n'est pas directement lié à la mission du stage, ça montre une capacité de travail et de persévérance qui peut être très précieuse pour l'offre)
- Une grande entreprise ne signifie pas forcément une expérience plus pertinente, concentre toi sur la valeur que chaque expérience apporte pour CETTE offre spécifique

*** ATTENTION ***
- EXACTEMENT {n_to_select} EXPÉRIENCES, PAS PLUS, PAS MOINS
- UNIQUEMENT parmi ces index: {valid_indexes_list}
- Tout index en dehors de {valid_indexes_list} est INTERDIT

*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{"reasoning": "index X car [raison], index Y car [raison]...", "selected_indexes": [indexA, indexB...]}}"""