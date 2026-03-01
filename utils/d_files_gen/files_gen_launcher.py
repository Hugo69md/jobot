import os
import json
from utils.d_files_gen.pdf_generator import generate_cv_pdf, generate_cover_letter_pdf


def run_pdf_generation(date: str):
    """
    Main entry point for PDF generation.
    Reads resume.json + match.json + cv.json.
    Generates 1 CV + 1 cover letter for the best offer.
    Outputs go into outputs/data[{date}]/pdf/
    """

    print("=" * 60)
    print("[D_PDF] Starting PDF generation...")
    print("=" * 60)

    # ─── Paths ───────────────────────────────────────────────────
    cv_path        = os.path.join("inputs", "cv.json")
    photo_path     = os.path.join("inputs", "photo.jpeg")
    match_path     = os.path.join("outputs", f"data[{date}]", "match.json")
    resume_path    = os.path.join("outputs", f"data[{date}]", "resume.json")
    pdf_output_dir = os.path.join("outputs", f"data[{date}]", "pdf")

    # ─── Validation ──────────────────────────────────────────────
    if not os.path.exists(cv_path):
        print(f"  [ERROR] CV file not found: {cv_path}")
        return
    if not os.path.exists(match_path):
        print(f"  [ERROR] match.json not found: {match_path}")
        return
    if not os.path.exists(photo_path):
        print(f"  [WARN] Photo not found — CVs will be generated without photo")
        photo_path = None

    os.makedirs(pdf_output_dir, exist_ok=True)

    # ─── Load files ──────────────────────────────────────────────
    with open(cv_path, "r", encoding="utf-8") as f:
        cv_data = json.load(f)
    with open(match_path, "r", encoding="utf-8") as f:
        match_data = json.load(f)

    # Load resume.json if available (contains tailored descriptions + skills_section)
    resume_data = {}
    if os.path.exists(resume_path):
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_data = json.load(f)
        print(f"  [INFO] Loaded resume.json")
    else:
        print(f"  [WARN] resume.json not found — no tailored descriptions, no AI skills section")

    # ─── Build match list ────────────────────────────────────────
    raw_match = match_data.get("match", [])
    if isinstance(raw_match, dict):
        matches = [raw_match]
    elif isinstance(raw_match, list):
        matches = raw_match
    else:
        matches = []
    print(f"  [INFO] Found {len(matches)} matched offer(s)\n")

    # ─── Build tailored descriptions lookup {index: description} ─
    tailored_descriptions = {
        entry["index"]: entry["description_tailored"]
        for entry in resume_data.get("resume", [])
        if "index" in entry and "description_tailored" in entry
    }

    # ─── Extract AI-selected skills section (6 items) ────────────
    cv_skills_section = resume_data.get("skills_section", [])
    if cv_skills_section:
        print(f"  [INFO] Skills section from resume.json: {cv_skills_section}")
    else:
        print(f"  [WARN] No skills_section in resume.json — skills section will be empty")

    # ─── SC / Data keyword detection ─────────────────────────────
    sc_keywords = [
        "supply chain", "logistique", "logisticien", "approvisionnement",
        "entrepôt", "warehouse", "flux", "gestionnaire logistique",
        "s&op", "planification", "inventory", "stock"
    ]

    # ─── Generate one PDF pair per match ─────────────────────────
    for i, match in enumerate(matches):
        offer_name = match.get("name", f"offer_{i+1}")
        company    = match.get("company", "Unknown")
        safe_name  = _sanitize_filename(f"{company}_{offer_name}")

        content_check   = f"{offer_name} {company}".lower()
        is_supply_chain = any(kw in content_check for kw in sc_keywords)

        print(f"  [{i+1}/{len(matches)}] {company} — {offer_name}")
        print(f"    Type  : {'Supply Chain' if is_supply_chain else 'Data'}")
        print(f"    Score : {match.get('score', '?')}/100")

        # Filter experiences from cv.json using the indexes the AI selected
        skill_indexes = match.get("skills", [])
        selected_experiences = [
            exp for exp in cv_data.get("experiences", [])
            if exp.get("index") in skill_indexes
        ]
        print(f"    Exp indexes selected: {skill_indexes}")

        # ─── Generate CV PDF ─────────────────────────────────────
        cv_filename = os.path.join(pdf_output_dir, f"CV_{safe_name}.pdf")
        generate_cv_pdf(
            output_path=cv_filename,
            cv_data=cv_data,
            selected_experiences=selected_experiences,
            is_supply_chain=is_supply_chain,
            photo_path=photo_path,
            tailored_descriptions=tailored_descriptions,  # ← from resume.json
            cv_skills_section=cv_skills_section,          # ← from resume.json
        )
        print(f"    ✅ CV  → {cv_filename}")

        # ─── Generate Cover Letter PDF ───────────────────────────
        cl_filename = os.path.join(pdf_output_dir, f"LM_{safe_name}.pdf")
        generate_cover_letter_pdf(
            output_path=cl_filename,
            cv_data=cv_data,
            match=match,
            is_supply_chain=is_supply_chain,
            date=date,
        )
        print(f"    ✅ LM  → {cl_filename}")
        print()

    print("=" * 60)
    print(f"[D_PDF] Generated {len(matches) * 2} PDFs → {pdf_output_dir}")
    print("=" * 60)


def _sanitize_filename(name: str) -> str:
    keepchars = (" ", "-", "_")
    name = "".join(c for c in name if c.isalnum() or c in keepchars).rstrip()
    return name[:80]