import json

def build_cover_letter_prompt(cv_data: dict, best_offer: dict, user_prompt: str) -> str:
    """
    SEPARATED from resume — generates ONLY the cover letter for the best offer.
    """
    perso = cv_data.get("Perso", [{}])[0]
    experiences = cv_data.get("experiences", [])
    skills = cv_data.get("skills", [])

    return f"""Tu es un expert en recrutement. Le candidat suivant cherche un stage de fin d'études.

CONTEXTE: {user_prompt}

PROFIL DU CANDIDAT:
- Nom: {perso.get("nom", "Hugo MANIPOUD")}
- Email: {perso.get("mail", "")}
- Téléphone: {perso.get("numero", "")}
- Formation: 5ème année école d'ingénieur ECAM Lyon, spécialisation Supply Chain Management
- Phrase intro Data: {perso.get("phrase_intro", {}).get("data", "")}
- Phrase intro Supply Chain: {perso.get("phrase_intro", {}).get("supply_chain", "")}

EXPÉRIENCES (avec index):
{json.dumps(experiences, ensure_ascii=False, indent=2)}

COMPÉTENCES (indexées):
{json.dumps(skills, ensure_ascii=False, indent=2)}

---

OFFRE SÉLECTIONNÉE (score: {best_offer.get("score")}):
{json.dumps({
    "name": best_offer.get("name"),
    "company": best_offer.get("company"),
    "location": best_offer.get("location"),
    "profil_recherche": best_offer.get("profil_recherche", ""),
    "missions": best_offer.get("missions", []),
    "competences": best_offer.get("competences", []),
}, ensure_ascii=False, indent=2)}

---

INSTRUCTIONS:
Rédige une lettre de motivation en FRANÇAIS (250-350 mots), personnalisée pour cette offre.
- Commence par "Madame, Monsieur,"
- Termine par "En attendant de pouvoir échanger à nouveau avec vous, veuillez accepter mes sincères salutations."
- Utilise \\n pour les sauts de ligne
- PAS d'en-tête (pas de date, pas d'adresse)
- Mets en avant les expériences et compétences qui matchent les missions et compétences de l'offre
- Mentionne l'entreprise et le poste par leur nom

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après):
{{
  "cover_letter": {{
    "name": "nom exact de l'offre",
    "URL": "{best_offer.get("URL", "")}",
    "company": "{best_offer.get("company", "")}",
    "location": "{best_offer.get("location", "")}",
    "score": {best_offer.get("score", 0)},
    "text": "Madame, Monsieur,\\n\\n..."
  }}
}}"""