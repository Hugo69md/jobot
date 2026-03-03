def build_domain_classification_prompt(offer: dict) -> str:
    """
    STEP 0 — Classify the offer domain before any extraction.
    Lightweight prompt: only uses name + first 400 chars of content.
    Returns: {"domain": "data"} or {"domain": "supply_chain"}
    """
    return f"""Tu es un assistant RH. Classe cette offre de stage dans l'un des deux domaines suivants UNIQUEMENT.

OFFRE: {offer.get("name", "")} chez {offer.get("company", "")}
DESCRIPTION (extrait): {offer.get("content", "")[:2000]}

DOMAINES POSSIBLES:
- "data"         → Data Analyst, Data Engineer, Data Science, BI, reporting, dashboards, Python/SQL, ML, ETL, analytics...
- "supply_chain" → Logistique, Supply Chain, planification, S&OP, stocks, WMS, approvisionnement, transport, entrepôt...

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après):
{{"domain": "data"}} ou {{"domain": "supply_chain"}}"""