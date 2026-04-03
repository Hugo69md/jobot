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
        "description":         best_offer.get("description", ""),
        "missions":            best_offer.get("missions", []),
        "competences_offre":   best_offer.get("competences_offre", []),
        "offer_industry_type": best_offer.get("offer_industry_type", []),
        "offer_sector":        best_offer.get("offer_sector", []),
    }

    valid_indexes_list = [exp["index"] for exp in pool_summary]

    return f"""*** CONTEXTE ***:
Tu es un expert recrutement. Tu aides un étudiant ingénieur à compléter la sélection d'expériences pour son CV.
D'autres expériences ont déjà été sélectionnées pour ce CV. Tu dois choisir parmi celles proposées dans experiences candidat UNIQUEMENT.

*** EXPÉRIENCES CANDIDAT ***:
{json.dumps(pool_summary, ensure_ascii=False, separators=(',', ':'))}

*** INDEX VALIDES ***: {valid_indexes_list}

*** OFFRE ***:
{json.dumps(offer_summary, ensure_ascii=False, indent=2)}

*** INSTRUCTIONS DE SÉLECTION (À SUIVRE DANS CET ORDRE STRICT) ***:
1. ADÉQUATION SECTORIELLE (Niveau 1) : L'industrie de l'expérience ("type") correspond-elle à l'"offer_industry_type" de l'offre ? (ex: une asso crypto pour une banque est un excellent match sectoriel).
2. ALIGNEMENT DE LA NATURE DU POSTE (Niveau 2) : Analyse la nature des "missions" de l'offre. 
- Si l'offre est à dominante intellectuelle, analytique ou de gestion (ex: data, ingénierie, pilotage de projet), privilégie absolument les expériences démontrant des capacités de réflexion, d'organisation ou de création. Pénalise les tâches purement manuelles ou d'exécution basique pour ces offres.
- À l'inverse, si l'offre est à dominante opérationnelle, manuelle ou d'exécution sur le terrain (ex: logistique physique, ouvrier, production), valorise les expériences de terrain et de manutention correspondantes. 
Le niveau d'exécution (intellectuel vs manuel) de l'expérience doit être le miroir de l'offre.
3. COMPÉTENCES DIRECTES (Niveau 3) : Les "missions" et "competences_offre" matchent-elles avec la "description" et les "specific_skills" de l'expérience ?
4. SOFT SKILLS (Niveau 4) : Ne valorise les soft skills (persévérance, rigueur) que si l'expérience démontre une implication intellectuelle ou organisationnelle importante (ex: organisation d'un concours sur 1 an, création de projet). 

*** ATTENTION ***
- NE JUSTIFIE JAMAIS des compétences intellectuelles/analytiques par des tâches d'exécution manuelle (et vice-versa). L'argumentaire doit être cohérent avec la nature de l'offre.
- EXACTEMENT {n_to_select} EXPÉRIENCES, PAS PLUS, PAS MOINS
- UNIQUEMENT parmi ces index: {valid_indexes_list}
- Tout index en dehors de {valid_indexes_list} est INTERDIT
- Ne te laisse pas influencer par la taille de l'entreprise focus sur l'interet de l'expérience pour le poste visé. 

*** FORMAT DE RÉPONSE ***:
Réponds UNIQUEMENT avec ce JSON:
{{"reasoning": "index X car [raison], index Y car [raison]...", "selected_indexes": [indexA, indexB...]}}"""