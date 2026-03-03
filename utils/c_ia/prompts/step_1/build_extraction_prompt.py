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

Réponds UNIQUEMENT avec ce JSON (pas de texte avant ou après):
{{
  "profil_recherche": "...",
  "missions": ["mission 1", "mission 2", "..."],
  "competences": ["Python", "SQL", "..."]
}}"""
