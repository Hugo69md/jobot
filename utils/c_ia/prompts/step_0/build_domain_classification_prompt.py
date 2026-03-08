def build_domain_classification_prompt(offer: dict) -> str:
    """
    STEP 0 — Classify the offer domain + extract industry type keywords.
    Lightweight prompt: only uses name + first 2000 chars of content.
    Returns: {"domain": "data", "type": ["keyword1", "keyword2"]}
    """
    return f"""Tu es un assistant RH. Classe cette offre de stage.

OFFRE: {offer.get("name", "")} chez {offer.get("company", "")}
DESCRIPTION (extrait): {offer.get("content", "")[:3000]}

*** INSTRUCTIONS ***:
1. "domain": Classe l'offre dans UN des deux domaines suivants UNIQUEMENT :
   - "data"         → Data Analyst, Data Engineer, Data Science, BI, reporting, dashboards, Python/SQL, ML, ETL, analytics...
   - "supply_chain" → Logistique, Supply Chain, planification, S&OP, stocks, WMS, approvisionnement, transport, entrepôt...

2. "type": Liste de 1 à 3 mots-clés décrivant le secteur d'activité et le domaine de travail de l'offre.
   Exemples :
   - Stage supply chain chez Sanofi → ["Supply_chain", "Medical"]
   - Stage data Python chez Thales → ["Data", "Defense"]
   - Stage logistique chez Airbus avec mention de programmation → ["Supply_chain", "Data", "Aerospace"]

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après):
{{"domain": "data", "type": ["keyword1", "keyword2"]}}"""