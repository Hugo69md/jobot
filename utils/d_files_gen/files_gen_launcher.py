import os
import json
import glob
import shutil
import datetime
from utils.d_files_gen.pdf_generator import generate_cv_pdf, generate_cover_letter_pdf


def run_pdf_generation(date: str):
    """
    Main entry point for PDF generation.
    Reads match.json + cv.json.
    For each offer in match.json:
      - reads offer_type, skills_section, tailored descriptions directly from the match entry
      - creates a subfolder: outputs/data[{date}]/pdf/{offer_name}_{generation_datetime}/
      - generates CV.pdf + LM.pdf inside that folder
    """

    print("=" * 60)
    print("[D_PDF] Starting PDF generation...")
    print("=" * 60)

    # ─── Paths ��──────────────────────────────────────────────────
    cv_path        = os.path.join("inputs", "cv.json")
    photo_path     = os.path.join("inputs", "photo.jpeg")
    match_path     = os.path.join("outputs", f"data[{date}]", "match.json")
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

    # ─── Build match list ────────────────────────────────────────
    raw_match = match_data.get("match", [])
    if isinstance(raw_match, dict):
        matches = [raw_match]
    elif isinstance(raw_match, list):
        matches = raw_match
    else:
        matches = []

    print(f"  [INFO] Found {len(matches)} matched offer(s)\n")

    # ─── Generation timestamp (same for all PDFs in this run) ────
    gen_dt       = datetime.datetime.now()
    gen_dt_str   = gen_dt.strftime("%Y-%m-%d_%Hh%m%S%f")   # to ensure unique folder names

    # ─── Generate one PDF pair per match ─────────────────────────
    for i, match in enumerate(matches):
        offer_name = match.get("name", f"offer_{i+1}")
        company    = match.get("company", "Unknown")
        score      = match.get("score", "?")

        print(f"  [{i+1}/{len(matches)}] {company} — {offer_name}")
        print(f"    Score : {score}/100")

        # ── offer_type comes directly from the match entry (set in ia_launcher STEP 0) ──
        offer_type      = match.get("offer_type", "")
        is_supply_chain = (offer_type == "supply_chain")
        print(f"    Type  : {'Supply Chain' if is_supply_chain else 'Data'} "
              f"({'from match.json ✅' if offer_type else 'default → data'})")

        # ── skills_section comes directly from the match entry (set in ia_launcher STEP 4) ──
        cv_skills_section = match.get("skills_section", [])
        print(f"    Skills section: {cv_skills_section}")

        # ── tailored descriptions from match entry ────────────────
        tailored_descriptions = {
            entry["index"]: entry["description_tailored"]
            for entry in match.get("resume", [])
            if "index" in entry and "description_tailored" in entry
        }

        # ── selected experience indexes ───────────────────────────
        skill_indexes = match.get("selected_indexes", [])
        selected_experiences = [
            exp for exp in cv_data.get("experiences", [])
            if exp.get("index") in skill_indexes
        ]
        print(f"    Exp indexes: {skill_indexes}")

        # ── Create subfolder: pdf/{offer_name}_{gen_datetime}/ ────
        safe_offer  = _sanitize_filename(offer_name)
        folder_name = f"{safe_offer}_{gen_dt_str}"
        offer_dir   = os.path.join(pdf_output_dir, folder_name)
        os.makedirs(offer_dir, exist_ok=True)

        # ── Generate CV PDF ───────────────────────────────────────
        cv_filename = os.path.join(offer_dir, "CV.pdf")
        generate_cv_pdf(
            output_path=cv_filename,
            cv_data=cv_data,
            selected_experiences=selected_experiences,
            is_supply_chain=is_supply_chain,
            photo_path=photo_path,
            tailored_descriptions=tailored_descriptions,
            cv_skills_section=cv_skills_section,
        )
        print(f"    ✅ CV  → {cv_filename}")

        # ── Generate Cover Letter PDF ─────────────────────────────
        cl_filename = os.path.join(offer_dir, "LM.pdf")
        generate_cover_letter_pdf(
            output_path=cl_filename,
            cv_data=cv_data,
            match=match,
            date=date,
        )
        print(f"    ✅ LM  → {cl_filename}")

        # ── Move resume JSON into the offer subfolder ─────────────
        data_dir = os.path.dirname(pdf_output_dir)
        for json_path in glob.glob(os.path.join(data_dir, "resume_*.json")):
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    jdata = json.load(jf)
                if jdata.get("offer_name") == offer_name:
                    dest = os.path.join(offer_dir, os.path.basename(json_path))
                    shutil.move(json_path, dest)
                    print(f"    ✅ JSON → {dest}")
                    break
            except Exception as exc:
                print(f"    [WARN] Could not process {json_path}: {exc}")

        print()

    print("=" * 60)
    print(f"[D_PDF] Generated {len(matches) * 2} PDFs in {len(matches)} folder(s)")
    print(f"  Root: {pdf_output_dir}")
    print("=" * 60)


def _sanitize_filename(name: str) -> str:
    keepchars = (" ", "-", "_")
    name = "".join(c for c in name if c.isalnum() or c in keepchars).rstrip()
    return name[:50]