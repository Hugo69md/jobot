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
            "skills": exp.get("skills", [])  
        })
    skills = cv_data.get("skills", [])
    return f"""CANDIDAT: {perso.get("nom", "Hugo MANIPOUD")} — Ingénieur 5A ECAM Lyon (Supply Chain + Data)
RECHERCHE: Stage fin d'études 4-6 mois à partir juin 2026 — Data OU Supply Chain — Mobile France
COMPÉTENCES: Python, pandas, numpy, scikit-learn, Excel avancé, Supply Chain (Arrow, Amazon)
EXPÉRIENCES:
{json.dumps(experiences_summary, ensure_ascii=False, separators=(',', ':'))}
SKILLS INDEXÉS:
{json.dumps(skills, ensure_ascii=False, separators=(',', ':'))}"""


def build_extraction_prompt(offer: dict) -> str:
    """
    Extract structured profil/missions/skills from the full raw description of a single offer.
    Also asks the AI to classify the offer domain and drop irrelevant ones.
    """
    return f"""Tu es un assistant RH. Analyse cette offre de stage et extrais les informations clés.

OFFRE: {offer.get("name", "")} chez {offer.get("company", "")} ({offer.get("location", "")})

DESCRIPTION COMPLÈTE:
{offer.get("content", "")}

---

INSTRUCTIONS:
Extrais UNIQUEMENT les informations suivantes depuis la description :
1. **profil_recherche**: Le niveau d'études et la spécialisation recherchés (ex: "Master 2 ou école ingénieur, spécialisation Data Science")
2. **missions**: Liste des principales missions/tâches du stage (phrases courtes)
3. **competences**: Liste des compétences techniques requises ou souhaitées (outils, langages, frameworks)
4. **domain**: Classifie cette offre parmi ces 3 valeurs UNIQUEMENT :
   - "data"         → si le poste est principalement axé Data (analyse, science des données, BI, reporting, Python/SQL, dashboards, ML, ETL...)
   - "supply_chain" → si le poste est principalement axé Supply Chain (logistique, stocks, planification, S&OP, WMS, approvisionnement, transport...)
   - "hors_domaine" → si le poste n'appartient ni à la Data ni à la Supply Chain (finance pure, marketing, droit, RH, commerce sans data, douanes...)

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après):
{{
  "profil_recherche": "...",
  "missions": ["mission 1", "mission 2", "..."],
  "competences": ["Python", "SQL", "..."],
  "domain": "data" | "supply_chain" | "hors_domaine"
}}"""


def build_single_offer_scoring_prompt(cv_data: dict, offer: dict, user_prompt: str) -> str:
    """Score a SINGLE enriched offer using structured fields when available."""
    cv_summary = _build_cv_summary(cv_data)

    # Use structured fields if available (from extraction step), else fall back to content
    if offer.get("competences"):
        offer_text = json.dumps({
            "name": offer.get("name", ""),
            "company": offer.get("company", ""),
            "location": offer.get("location", ""),
            "profil_recherche": offer.get("profil_recherche", ""),
            "missions": offer.get("missions", []),
            "competences": offer.get("competences", []),
        }, ensure_ascii=False)
    else:
        # Fallback: use first 800 chars of raw content
        offer_text = json.dumps({
            "name": offer.get("name", ""),
            "company": offer.get("company", ""),
            "location": offer.get("location", ""),
            "content": offer.get("content", "")[:800],
        }, ensure_ascii=False)

    return f"""Tu es un expert recrutement. Score cette offre de stage pour ce candidat.

{cv_summary}

OFFRE:
{offer_text}

CRITÈRES DE SCORING (total 100 pts):
1. **Correspondance compétences** (40 pts) : Les compétences demandées dans l'offre correspondent-elles aux compétences du candidat (supply_chain et/ou data) ?
   - t_prio skills match avec section competence = max points
   - prio skills match avec section competence = points moyens
   - bonus skills match avec section competence = points bonus
2. Formation/niveau (10 pts): Bac+4/5, école ingénieur, stage fin d'études = max, si certains criteres remplis, moins de points
3. Prestige entreprise (20 pts): CAC40/S&P500/Big4/Big3 = max, ETI = 15, PME = 5
4. Localisation (15 pts): Lyon/Paris/Montpellier = max, -1pt par 1km au-delà, >20km = 0
5. Période (15 pts): début autour juin/juillet 2026 = max

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après):
{{"name": "nom exact de l'offre", "score": 80 (for example)}}"""


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
***ATTENTION*** : Tu dois TOUJOURS incorporer l'experience avec l'index numero 1 : Etudiant ECAM LYON, même si ce n'est pas important pour l'experience, choisi 5 autres experiences, le total doit toujours etre de 6 expériences.

INSTRUCTIONS :
Pour CHAQUE expérience, tu dois :

1. Identifier les mots-clés de l'offre (champs "competences" et "missions") qui sont pertinents pour cette expérience spécifique.
2. Vérifier que ces mots-clés sont présents dans le catalogue "skills" du candidat — n'invente JAMAIS de compétences que le candidat ne possède pas.
3. Réécrire le champ "description" de l'expérience pour :
   - Intégrer naturellement les mots-clés pertinents (pour maximiser le score ATS)
   - Conserver le sens original et rester factuel
   - Garder un style professionnel et concis (max 3-4 phrases)
   - Ne PAS inventer de chiffres ou de résultats qui ne sont pas dans la description originale

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après) :
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

def build_skills_section_prompt(
    cv_data: dict,
    best_offer: dict,
    resume_data: dict,
) -> str:
    """
    STEP 4 — Pick the 6 best skills to display in the CV skills section.

    Inputs:
      - all keywords_injected from resume_data (already validated against cv.json)
      - offer competences + missions (from enrichment step)
      - full skills catalog from cv.json (as candidate pool)

    Output JSON:
    {
      "skills_section": ["Python", "pandas", "Supply Chain", "KPI", "Excel avancé", "Scrapy"]
    }
    → exactly 6 items, ordered by relevance to the offer (most relevant first)
    """

    # Flatten ALL keywords_injected across all tailored experiences
    all_keywords_injected = []
    seen = set()
    for exp_entry in resume_data.get("resume", []):
        for kw in exp_entry.get("keywords_injected", []):
            kw_norm = kw.strip()
            if kw_norm and kw_norm.lower() not in seen:
                seen.add(kw_norm.lower())
                all_keywords_injected.append(kw_norm)

    # Full skills catalog flattened (candidate pool the AI can pick from)
    skills_catalog = cv_data.get("skills", [{}])[0]
    all_candidate_skills = []
    for domain in ["data", "supply_chain"]:
        domain_skills = skills_catalog.get(domain, {})
        for tier in ["t_prio", "prio", "bonus"]:
            all_candidate_skills.extend(domain_skills.get(tier, []))
    # Deduplicate while preserving order
    seen2 = set()
    all_candidate_skills_deduped = []
    for s in all_candidate_skills:
        if s.lower() not in seen2:
            seen2.add(s.lower())
            all_candidate_skills_deduped.append(s)

    offer_context = {
        "name":        best_offer.get("name", ""),
        "company":     best_offer.get("company", ""),
        "missions":    best_offer.get("missions", []),
        "competences": best_offer.get("competences", []),
    }

    return f"""Tu es un expert en optimisation de CV pour les logiciels ATS.

CONTEXTE : Le candidat postule à cette offre de stage :
{json.dumps(offer_context, ensure_ascii=False, indent=2)}

---

MOTS-CLÉS INJECTÉS dans les descriptions du CV (déjà validés comme compétences réelles du candidat) :
{json.dumps(all_keywords_injected, ensure_ascii=False)}

CATALOGUE COMPLET des compétences du candidat (pool de sélection autorisé) :
{json.dumps(all_candidate_skills_deduped, ensure_ascii=False)}

---

INSTRUCTIONS :
Tu dois sélectionner EXACTEMENT 6 compétences techniques à afficher dans la section "Compétences" du CV.

Règles de sélection :
1. Priorité maximale aux compétences présentes à la fois dans "MOTS-CLÉS INJECTÉS" ET dans "competences" ou "missions" de l'offre — ce sont les mots-clés ATS les plus importants
2. Priorité secondaire aux compétences présentes dans "MOTS-CLÉS INJECTÉS" mais pas encore dans l'offre — elles montrent la polyvalence du candidat
3. En cas d'égalité, préfère les compétences les plus reconnues/valorisantes (ex: Python > "data processing")
4. Ne sélectionne QUE des compétences présentes dans le "CATALOGUE COMPLET" — n'invente rien
5. Retourne les 6 compétences triées du plus pertinent au moins pertinent

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après) :
{{"skills_section": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6"]}}"""