import os
import json
from utils.d_files_gen.pdf_generator import generate_cv_pdf, generate_cover_letter_pdf


def run_pdf_generation(date: str):
    """
    Main entry point for PDF generation.
    Reads match.json and cv.json, generates 1 CV + 1 cover letter per matched offer.
    Outputs go into outputs/data[{date}]/pdf/
    """

    print("=" * 60)
    print("[D_PDF] Starting PDF generation...")
    print("=" * 60)

    # ─── Load input files ────────────────────────────────────────
    cv_path = os.path.join("inputs", "cv.json")
    photo_path = os.path.join("inputs", "photo.jpeg")
    match_path = os.path.join("outputs", f"data[{date}]", "match.json")
    pdf_output_dir = os.path.join("outputs", f"data[{date}]", "pdf")

    if not os.path.exists(cv_path):
        print(f"  [ERROR] CV file not found: {cv_path}")
        return
    if not os.path.exists(match_path):
        print(f"  [ERROR] Match file not found: {match_path}")
        return
    if not os.path.exists(photo_path):
        print(f"  [WARN] Photo not found: {photo_path} — CVs will be generated without photo")
        photo_path = None

    # Create pdf output dir if it doesn't exist
    os.makedirs(pdf_output_dir, exist_ok=True)

    with open(cv_path, "r", encoding="utf-8") as f:
        cv_data = json.load(f)
    with open(match_path, "r", encoding="utf-8") as f:
        match_data = json.load(f)

    matches = match_data.get("match", [])
    print(f"  [INFO] Found {len(matches)} matched offers to generate PDFs for\n")

    # ─── Determine offer type (supply_chain or data) ─────────────
    # Keywords that indicate a supply chain offer
    sc_keywords = [
        "supply chain", "logistique", "logisticien", "approvisionnement",
        "entrepôt", "warehouse", "flux", "gestionnaire logistique",
        "s&op", "planification", "inventory", "stock"
    ]

    for i, match in enumerate(matches):
        offer_name = match.get("name", f"offer_{i+1}")
        company = match.get("company", "Unknown")
        safe_name = _sanitize_filename(f"{company}_{offer_name}")

        # Detect if supply chain offer
        name_lower = offer_name.lower()
        content_check = f"{offer_name} {company}".lower()
        is_supply_chain = any(kw in content_check for kw in sc_keywords)

        print(f"  [{i+1}/{len(matches)}] {company} — {offer_name}")
        print(f"    Type: {'Supply Chain' if is_supply_chain else 'Data'}")

        # Get the experience indexes the AI selected for this offer
        skill_indexes = match.get("skills", [])

        # Filter experiences from cv.json based on those indexes
        selected_experiences = [
            exp for exp in cv_data.get("experiences", [])
            if exp.get("index") in skill_indexes
        ]

        # ─── Generate CV PDF ─────────────────────────────────────
        cv_filename = os.path.join(pdf_output_dir, f"CV_{safe_name}.pdf")
        generate_cv_pdf(
            output_path=cv_filename,
            cv_data=cv_data,
            selected_experiences=selected_experiences,
            is_supply_chain=is_supply_chain,
            photo_path=photo_path
        )
        print(f"    ✅ CV  → {cv_filename}")

        # ─── Generate Cover Letter PDF ───────────────────────────
        cl_filename = os.path.join(pdf_output_dir, f"LM_{safe_name}.pdf")
        generate_cover_letter_pdf(
            output_path=cl_filename,
            cv_data=cv_data,
            match=match,
            is_supply_chain=is_supply_chain,
            date=date
        )
        print(f"    ✅ LM  → {cl_filename}")
        print()

    print("=" * 60)
    print(f"[D_PDF] Generated {len(matches) * 2} PDFs ({len(matches)} CVs + {len(matches)} cover letters)")
    print("=" * 60)


def _sanitize_filename(name: str) -> str:
    """Remove characters that are not safe for filenames."""
    keepchars = (" ", "-", "_")
    name = "".join(c for c in name if c.isalnum() or c in keepchars).rstrip()
    # Truncate to avoid overly long filenames
    return name[:80]