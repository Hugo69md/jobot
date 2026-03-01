import json


# ── Compact CV profile (reused across all per-offer prompts) ────────────────
def _build_cv_summary(cv_data: dict) -> str:
    perso = cv_data.get("Perso", [{}])[0]
    experiences_summary = []
    for exp in cv_data.get("experiences", []):
        experiences_summary.append({
            "index": exp["index"],
            "name": exp["name"],
            "categorization": exp["categorization"],
            "skills": exp.get("skills", [])[:5]  # top 5 skills per experience
        })
    skills = cv_data.get("skills", [])
    return f"""CANDIDAT: {perso.get("nom", "Hugo MANIPOUD")} — Ingénieur 5A ECAM Lyon (Supply Chain + Data)
RECHERCHE: Stage fin d'études 4-6 mois à partir juin 2026 — Data OU Supply Chain — Mobile France
COMPÉTENCES: Python, pandas, numpy, scikit-learn, Excel avancé, Supply Chain (Arrow, Amazon)
EXPÉRIENCES:
{json.dumps(experiences_summary, ensure_ascii=False, separators=(',', ':'))}
SKILLS INDEXÉS:
{json.dumps(skills, ensure_ascii=False, separators=(',', ':'))}"""


def build_single_offer_scoring_prompt(cv_data: dict, offer: dict, user_prompt: str) -> str:
    """Score a SINGLE offer. Returns a compact prompt (~2000-3000 tokens max)."""
    cv_summary = _build_cv_summary(cv_data)
    offer_text = json.dumps({
        "name": offer.get("name", ""),
        "company": offer.get("company", ""),
        "location": offer.get("location", ""),
        "content": offer.get("content", "")[:800]
    }, ensure_ascii=False)

    return f"""Tu es un expert recrutement. Score cette offre de stage pour ce candidat.

{cv_summary}

OFFRE:
{offer_text}

CRITÈRES DE SCORING (total 100 pts):
1. Correspondance compétences (40 pts): skills supply_chain/data du candidat vs offre
2. Formation/niveau (10 pts): Bac+4/5, école ingénieur, stage fin d'études = max
3. Prestige entreprise (20 pts): CAC40/S&P500/Big4/Big3 = max, ETI = 15, PME = 5
4. Localisation (15 pts): Lyon/Paris/Montpellier = max, -1pt par 1km au-delà, >20km = 0
5. Période (15 pts): début autour juin/juillet 2026 = max

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après):
{{"name": "nom exact de l'offre", "score": 85, "reason": "justification courte en 1 phrase"}}"""


def build_match_prompt(cv_data: dict, best_offer_full: dict, user_prompt: str) -> str:
    """
    Generate skills selection + cover letter for the SINGLE best offer.
    best_offer_full: the complete offer dict (with full content) plus "score" key.
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

OFFRE SÉLECTIONNÉE (score: {best_offer_full.get("score")}):
{json.dumps(best_offer_full, ensure_ascii=False, indent=2)}

---

INSTRUCTIONS:
1. **skills**: liste des INDEX des 6 expériences les plus pertinentes pour cette offre.
2. **cover_letter**: lettre de motivation en FRANÇAIS (250-350 mots), personnalisée.
   - Commence par "Madame, Monsieur,"
   - Termine par "En attendant de pouvoir échanger à nouveau avec vous, veuillez accepter mes sincères salutations."
   - Utilise \\n pour les sauts de ligne
   - PAS d'en-tête (pas de date, pas d'adresse)

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après):
{{
  "match": {{
    "name": "nom exact de l'offre",
    "URL": "url de l'offre",
    "company": "entreprise",
    "location": "localisation",
    "score": {best_offer_full.get("score")},
    "skills": [1, 2, 4, 6],
    "cover_letter": "Madame, Monsieur,\\n\\n..."
  }}
}}"""