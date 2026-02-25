import json


def build_scoring_prompt(cv_data: dict, internships_data: list, user_prompt: str) -> str:
    """
    Build the prompt that asks the AI to score ALL job offers against the CV.
    Returns a structured prompt instructing the model to output JSON.
    """

    # Extract key CV info for the prompt
    experiences_summary = []
    for exp in cv_data.get("experiences", []):
        experiences_summary.append({
            "index": exp["index"],
            "name": exp["name"],
            "period": exp["period"],
            "categorization": exp["categorization"],
            "skills": exp.get("skills", [])
        })

    skills_summary = cv_data.get("skills", [])
    perso_info = cv_data.get("Perso", [{}])[0]

    # Simplify internship data to reduce token count
    internships_simplified = []
    for offer in internships_data:
        internships_simplified.append({
            "name": offer.get("name", ""),
            "company": offer.get("company", ""),
            "location": offer.get("location", ""),
            "content": offer.get("content", "")[:1000]  # Truncate very long descriptions
        })

    prompt = f"""Tu es un expert en recrutement et en matching de profils candidats avec des offres de stage.

CONTEXTE UTILISATEUR : {user_prompt}

PROFIL DU CANDIDAT :
- Nom : {perso_info.get("nom", "Hugo MANIPOUD")}
- Formation : Étudiant en 5ème année école d'ingénieur (ECAM Lyon), spécialisation Supply Chain Management
- Compétences supplementaires : Fort interet pour la Data, maîtrise de Python, Excel avancé, pandas, numpy, matplotlib, seaborn, scikit-learn, et à de multiples projets à son actif
- Recherche : Stage de fin d'études à partir de juin 2026
- Domaines cibles : Data Analysis ET/OU Supply Chain

EXPÉRIENCES DU CANDIDAT :
{json.dumps(experiences_summary, ensure_ascii=False, indent=2)}

COMPÉTENCES DU CANDIDAT (indexées par domaine et priorité) :
{json.dumps(skills_summary, ensure_ascii=False, indent=2)}

---

LISTE DES OFFRES DE STAGE À ÉVALUER :
{json.dumps(internships_simplified, ensure_ascii=False, indent=2)}

---

INSTRUCTIONS :
Tu dois scorer CHAQUE offre de stage sur 100 points en fonction des critères suivants :
1. **Correspondance compétences** (40 pts) : Les compétences demandées dans l'offre correspondent-elles aux compétences du candidat (supply_chain et/ou data) ?
   - t_prio skills match = max points
   - prio skills match = points moyens
   - bonus skills match = points bonus
2. **Correspondance formation/niveau** (10 pts) : L'offre demande-t-elle un Bac+4/5, école d'ingénieur, stage de fin d'études ? Si oui, points complets, sinon 0
3. **Prestige de l'entreprise** (20 pts) : Point maximum si la boite fait parti du Cac40, du S&P 500, si cest une big 3 ou une big 4. Point maximum pour les offres d'audit ou conseil, sinon réduire en fonction de la notoriété de l'entreprise (ex: 15 pts pour une entreprise de taille intermédiaire, 5 pts pour une petite entreprise locale)
4. **Localisation** (15 pts) : Point maximum si L'offres est à Lyon, Paris, ou Montpellier, reduire de 1 point pour chaque 1km au-delà, des villes citées, (ex 10 km de la ville = 5 pts, 20 km = 0 pts)
5. **Période** (15 pts) : L'offre commence-t-elle autour de juin/juillet 2026 ?


Réponds UNIQUEMENT avec un JSON valide au format suivant :
{{
  "scoring": [
    {{
      "name": "nom exact de l'offre tel que dans la liste",
      "score": 85
    }},
    ...
  ]
}}

Classe les résultats du score le plus élevé au plus bas.
Ne rajoute AUCUN texte en dehors du JSON.
"""
    
    estimated_tokens = len(prompt) // 4
    print(f"  [INFO] Scoring prompt estimated tokens: ~{estimated_tokens} tokens")
    if estimated_tokens > 32768:
        print("  [WARNING] Scoring prompt may exceed model context window!")
    return prompt


def build_match_prompt(cv_data: dict, top_offers: list, internships_data: list, user_prompt: str) -> str:
    """
    Build the prompt for the top 5 offers: extract detailed match info,
    relevant skill indexes, and generate a cover letter for each.
    """

    # Get the full offer data for the top 5
    top_offers_full = []
    for scored_offer in top_offers:
        offer_name = scored_offer["name"]
        for internship in internships_data:
            if internship.get("name", "") == offer_name:
                top_offers_full.append({
                    "name": internship["name"],
                    "URL": internship.get("URL", ""),
                    "company": internship.get("company", ""),
                    "location": internship.get("location", ""),
                    "content": internship.get("content", ""),
                    "score": scored_offer["score"]
                })
                break

    skills_summary = cv_data.get("skills", [])
    experiences = cv_data.get("experiences", [])
    perso_info = cv_data.get("Perso", [{}])[0]

    prompt = f"""Tu es un expert en recrutement. Le candidat suivant cherche un stage de fin d'études.

CONTEXTE : {user_prompt}

PROFIL DU CANDIDAT :
- Nom : {perso_info.get("nom", "Hugo MANIPOUD")}
- Email : {perso_info.get("mail", "")}
- Téléphone : {perso_info.get("numero", "")}
- Formation : 5ème année école d'ingénieur ECAM Lyon, spécialisation Supply Chain Management
- Phrase d'intro Data : {perso_info.get("phrase_intro", {}).get("data", "")}
- Phrase d'intro Supply Chain : {perso_info.get("phrase_intro", {}).get("supply_chain", "")}

EXPÉRIENCES DU CANDIDAT (avec index) :
{json.dumps(experiences, ensure_ascii=False, indent=2)}

COMPÉTENCES DU CANDIDAT (indexées par domaine et niveau de priorité) :
{json.dumps(skills_summary, ensure_ascii=False, indent=2)}

---

TOP 5 OFFRES SÉLECTIONNÉES (avec leur score) :
{json.dumps(top_offers_full, ensure_ascii=False, indent=2)}

---

INSTRUCTIONS :
Pour l'offre avec le meileur score, tu dois produire :

1. **skills** : une liste des INDEX des expériences du CV (champ "index" dans les expériences) qui sont les plus pertinentes à mettre en avant pour CETTE offre spécifique. Choisis les 6 expériences les plus pertinentes.

2. **cover_letter** : une lettre de motivation en FRANÇAIS, professionnelle mais naturelle, personnalisée pour cette offre.
   - Sert toi de la description de l'offre et des expériences/compétences du candidat pour faire le lien et montrer pourquoi il est un bon match
   - Mentionne l'entreprise et le poste par leur nom
   - Mets en avant les expériences et compétences du candidat qui matchent le mieux
   - Environ 250-350 mots
   - Utilise \\n pour les sauts de ligne
   - NE PAS inclure d'en-tête (pas de date, pas d'adresse) — juste le corps de la lettre
   - Commence par "Madame, Monsieur," et termine par la formule de politesse suivante : "En attendant de pouvoir échanger à nouveau avec vous, veuillez accepter mes sincères salutations." 

Réponds UNIQUEMENT avec un JSON valide au format suivant :
{{
  "match": [
    {{
      "name": "nom exact de l'offre",
      "URL": "URL de l'offre",
      "company": "nom de l'entreprise",
      "location": "localisation",
      "score": 85,
      "skills": [1, 2, 4, 6],
      "cover_letter": "Madame, Monsieur,\\n\\nActuellement en 5ème année...\\n\\n..."
    }},
    ...
  ]
}}

Ne rajoute AUCUN texte en dehors du JSON.
"""
    return prompt