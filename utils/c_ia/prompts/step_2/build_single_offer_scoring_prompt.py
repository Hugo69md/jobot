import json

# ── Compact CV profile (reused across all per-offer prompts) to save tokens ────────────────
def _build_cv_summary(cv_data: dict) -> str:
    perso = cv_data.get("Perso", [{}])[0]
    experiences_summary = []
    for exp in cv_data.get("experiences", []):
        experiences_summary.append({
            "index": exp["index"],
            "name": exp["name"],
            "categorization": exp["categorization"],
            "specific_skills": exp.get("specific_skills", [])  
        })
    all_candidate_skills = cv_data.get("all_candidate_skills", [])
    return f"""CANDIDAT: {perso.get("nom", "Hugo MANIPOUD")} — Ingénieur 5A ECAM Lyon (Supply Chain + Data)
RECHERCHE: Stage fin d'études 4-6 mois à partir juin 2026 — Data OU Supply Chain — Mobile France
COMPÉTENCES: Python, pandas, numpy, scikit-learn, Excel avancé, Supply Chain (Arrow, Amazon)
EXPÉRIENCES:
{json.dumps(experiences_summary, ensure_ascii=False, separators=(',', ':'))}
SKILLS DU CANDIDAT INDEXÉS:
{json.dumps(all_candidate_skills, ensure_ascii=False, separators=(',', ':'))}"""


def build_single_offer_scoring_prompt(cv_data: dict, offer: dict, user_prompt: str) -> str:
    """Score a SINGLE enriched offer using structured fields when available."""
    cv_summary = _build_cv_summary(cv_data)

    # Use structured fields if available (from extraction step), else fall back to content
    if offer.get("competences_offre"):
        offer_text = json.dumps({
            "name": offer.get("name", ""),
            "company": offer.get("company", ""),
            "location": offer.get("location", ""),
            "profil_recherche": offer.get("profil_recherche", ""),
            "missions": offer.get("missions", []),
            "competences_offre": offer.get("competences_offre", []),
        }, ensure_ascii=False)
    else:
        print("fallback data AAAAAAAAAAAAAAAAAAAAAAAA")
        # Fallback: use first 800 chars of raw content
        offer_text = json.dumps({
            "name": offer.get("name", ""),
            "company": offer.get("company", ""),
            "location": offer.get("location", ""),
            "content": offer.get("content", "")[:2000],
        }, ensure_ascii=False)

    return f"""
*** CONTEXTE ***:
        
Tu es en recherche de stage. tu dois appliquer un score à cette offre pour determiner si le stage est interessant pour toi ou non.

*** PROFIL / EXPERIENCES ***:
{cv_summary}

*** OFFRE ***:
{offer_text}

*** CRITÈRES DE SCORING ***:
- Sur un (total 100 pts) applique ce scoring:
1. *Correspondance compétences* (40 pts) : Les compétences_offre demandées dans l'offre correspondent-elles aux compétence du candidat (all_candidate_skills) (supply_chain et/ou data) ?
   - t_prio skills match avec section competence = 1 point pour chaque compétence matchée
   - prio skills match avec section competence = 0.5 point pour chaque compétence matchée
   - bonus skills match avec section competence = 0.25 point pour chaque compétence matchée
2. *Formation/niveau* (10 pts): Bac+4/5, école ingénieur, stage fin d'études = max
3. *Prestige entreprise* (20 pts): CAC40/S&P500/Big4/Big3 = max, sinon baisse en fonction de la renommée de l'entreprise
4. *Localisation* (15 pts): 
- Lyon ou Paris ou Montpellier = 15pt
- Si la ville à 1km d'un de ces 3 centre villes, -1pt, si 2Km au dela de ces 3 villes, -2pt.
- <15km = 0
- ATTENTION, PARIS ET MONTPELLIER ET LYON SONT TOUTES DES VILLES CIBLE
5. *Période* (15 pts): début juin 2026 = max sinon baisser progressivement plus le stage est loin de cette periode

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après):
{{
  "name": "nom exact de l'offre",
  "C1": {{"reason": "skill1 match t_prio +1, skill2 match prio +0.5 ...", "score": 32}},
  "C2": {{"reason": "...", "score": 8}},
  "C3": {{"reason": "...", "score": 15}},
  "C4": {{"reason": "...", "score": 10}},
  "C5": {{"reason": "...", "score": 12}}
}}"""