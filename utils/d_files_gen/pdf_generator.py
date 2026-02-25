import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, Frame, PageTemplate, BaseDocTemplate
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ─── Color palette ────────────────────────────────────────────
COLOR_PRIMARY = HexColor("#2C3E50")     # Dark blue-gray
COLOR_ACCENT = HexColor("#2980B9")      # Blue
COLOR_TEXT = HexColor("#333333")        # Near-black
COLOR_LIGHT = HexColor("#7F8C8D")       # Gray
COLOR_BG_SECTION = HexColor("#ECF0F1")  # Light gray background
COLOR_WHITE = HexColor("#FFFFFF")


# ═══════════════════════════════════════════════════════════════
#  CV PDF GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_cv_pdf(
    output_path: str,
    cv_data: dict,
    selected_experiences: list,
    is_supply_chain: bool,
    photo_path: str | None
):
    """Generate a clean, professional one-page CV as PDF."""

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )

    styles = _get_cv_styles()
    elements = []

    perso = cv_data.get("Perso", [{}])[0]
    all_experiences = cv_data.get("experiences", [])
    skills_data = cv_data.get("skills", [{}])[0] if cv_data.get("skills") else {}

    nom = perso.get("nom", "Hugo MANIPOUD")
    numero = perso.get("numero", "")
    mail = perso.get("mail", "")
    phrase_intro = perso.get("phrase_intro", {})
    intro = phrase_intro.get("supply_chain", "") if is_supply_chain else phrase_intro.get("data", "")

    # ─── HEADER: Photo + Name + Contact ──────────────────────────
    header_elements = []

    # Name and contact info (right side)
    name_block = []
    name_block.append(Paragraph(nom, styles["name"]))
    name_block.append(Spacer(1, 2 * mm))
    name_block.append(Paragraph(f"📧 {mail}  |  📱 {numero}", styles["contact"]))
    name_block.append(Spacer(1, 3 * mm))
    name_block.append(Paragraph(intro, styles["intro"]))

    if photo_path and os.path.exists(photo_path):
        # Table with photo on the left, info on the right
        photo = Image(photo_path, width=30 * mm, height=30 * mm)
        photo.hAlign = "LEFT"

        header_table = Table(
            [[photo, name_block]],
            colWidths=[35 * mm, 145 * mm],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
    else:
        for block in name_block:
            elements.append(block)

    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(
        width="100%", thickness=1, color=COLOR_ACCENT,
        spaceAfter=4 * mm, spaceBefore=0
    ))

    # ─── EXPERIENCES SECTION ─────────────────────────────────────
    # Group selected experiences by categorization
    categories_order = [
        ("experiences_pro", "Expériences Professionnelles"),
        ("etudes", "Formation"),
        ("certifications", "Certifications & Formations"),
        ("projets_perso", "Projets Personnels"),
        ("benevolat", "Bénévolat & Associations"),
    ]

    selected_indexes = {exp["index"] for exp in selected_experiences}

    for cat_key, cat_title in categories_order:
        cat_experiences = [
            exp for exp in all_experiences
            if exp.get("categorization") == cat_key and exp.get("index") in selected_indexes
        ]
        if not cat_experiences:
            continue

        # Section title
        elements.append(Paragraph(cat_title.upper(), styles["section_title"]))
        elements.append(Spacer(1, 2 * mm))

        for exp in cat_experiences:
            # Experience name + period
            exp_name = exp.get("name", "")
            exp_period = exp.get("period", "")
            exp_desc = exp.get("description", "")
            exp_skills = exp.get("skills", [])
            exp_link = exp.get("link", "")

            # Title line: name on left, period on right
            title_table = Table(
                [[
                    Paragraph(f"<b>{exp_name}</b>", styles["exp_title"]),
                    Paragraph(exp_period, styles["exp_period"]),
                ]],
                colWidths=[130 * mm, 50 * mm],
            )
            title_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            elements.append(title_table)

            # Description
            if exp_desc:
                elements.append(Paragraph(exp_desc, styles["exp_desc"]))

            # Skills as bullet points
            if exp_skills:
                for skill in exp_skills:
                    elements.append(Paragraph(f"• {skill}", styles["exp_skill"]))

            # Link
            if exp_link:
                elements.append(Paragraph(
                    f'🔗 <a href="{exp_link}" color="#2980B9">{exp_link}</a>',
                    styles["exp_link"]
                ))

            elements.append(Spacer(1, 3 * mm))

    # ─── SKILLS SECTION ──────────────────────────────────────────
    elements.append(Paragraph("COMPÉTENCES", styles["section_title"]))
    elements.append(Spacer(1, 2 * mm))

    # Choose which skill set to display based on offer type
    if is_supply_chain and "supply_chain" in skills_data:
        skill_set = skills_data["supply_chain"]
        skill_label = "Supply Chain"
    elif "data" in skills_data:
        skill_set = skills_data["data"]
        skill_label = "Data"
    else:
        skill_set = {}
        skill_label = ""

    if skill_set:
        # Top priority skills
        t_prio = skill_set.get("t_prio", [])
        prio = skill_set.get("prio", [])
        bonus = skill_set.get("bonus", [])

        if t_prio:
            skills_text = " · ".join(t_prio[:12])  # Limit to avoid overflow
            elements.append(Paragraph(
                f"<b>{skill_label} :</b> {skills_text}",
                styles["skill_line"]
            ))

        if prio:
            skills_text = " · ".join(prio[:8])
            elements.append(Paragraph(
                f"<b>Complémentaires :</b> {skills_text}",
                styles["skill_line"]
            ))

        if bonus:
            skills_text = " · ".join(bonus[:8])
            elements.append(Paragraph(
                f"<b>Bonus :</b> {skills_text}",
                styles["skill_line"]
            ))

    # ─── BUILD PDF ───────────────────────────────────────────────
    doc.build(elements)


# ═══════════════════════════════════════════════════════════════
#  COVER LETTER PDF GENERATION
# ═════════════════════════════��═════════════════════════════════

def generate_cover_letter_pdf(
    output_path: str,
    cv_data: dict,
    match: dict,
    is_supply_chain: bool,
    date: str,
):
    """Generate a clean French-format cover letter as PDF."""

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
    )

    styles = _get_cl_styles()
    elements = []

    perso = cv_data.get("Perso", [{}])[0]
    nom = perso.get("nom", "Hugo MANIPOUD")
    numero = perso.get("numero", "")
    mail = perso.get("mail", "")

    company = match.get("company", "")
    location = match.get("location", "")
    offer_name = match.get("name", "")
    cover_letter_text = match.get("cover_letter", "")

    # Parse the date string to get a nice French date
    try:
        dt = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        french_date = _format_french_date(dt)
    except ValueError:
        french_date = date

    # ─── SENDER (top-left) ───────────────────────────────────────
    elements.append(Paragraph(f"<b>{nom}</b>", styles["sender"]))
    elements.append(Paragraph(mail, styles["sender"]))
    elements.append(Paragraph(numero, styles["sender"]))

    elements.append(Spacer(1, 10 * mm))

    # ─── RECIPIENT (right-aligned) ───────────────────────────────
    elements.append(Paragraph(f"<b>{company}</b>", styles["recipient"]))
    elements.append(Paragraph(location, styles["recipient"]))

    elements.append(Spacer(1, 8 * mm))

    # ─── DATE (right-aligned) ────────────────────────────────────
    elements.append(Paragraph(f"Le {french_date}", styles["date"]))

    elements.append(Spacer(1, 10 * mm))

    # ─── OBJECT LINE ─────────────────────────────────────────────
    elements.append(Paragraph(
        f"<b>Objet :</b> Candidature — {offer_name}",
        styles["object"]
    ))

    elements.append(Spacer(1, 8 * mm))

    # ─── LETTER BODY ─────────────────────────────────────────────
    # Split the cover letter by \n and create paragraphs
    paragraphs = cover_letter_text.split("\n")
    for para_text in paragraphs:
        para_text = para_text.strip()
        if not para_text:
            elements.append(Spacer(1, 3 * mm))
        else:
            elements.append(Paragraph(para_text, styles["body"]))
            elements.append(Spacer(1, 2 * mm))

    # ─── BUILD PDF ───────────────────────────────────────────────
    doc.build(elements)


# ═══════════════════════════════════════════════════════════════
#  STYLES
# ═══════════════════════════════════════════════════════════════

def _get_cv_styles():
    """Return all paragraph styles used in the CV PDF."""
    base = getSampleStyleSheet()

    return {
        "name": ParagraphStyle(
            "cv_name",
            parent=base["Title"],
            fontSize=20,
            leading=24,
            textColor=COLOR_PRIMARY,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "contact": ParagraphStyle(
            "cv_contact",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=COLOR_LIGHT,
            alignment=TA_LEFT,
        ),
        "intro": ParagraphStyle(
            "cv_intro",
            parent=base["Normal"],
            fontSize=9,
            leading=13,
            textColor=COLOR_TEXT,
            alignment=TA_LEFT,
            fontName="Helvetica-Oblique",
        ),
        "section_title": ParagraphStyle(
            "cv_section_title",
            parent=base["Heading2"],
            fontSize=11,
            leading=14,
            textColor=COLOR_ACCENT,
            spaceBefore=4 * mm,
            spaceAfter=1 * mm,
            borderWidth=0,
            borderPadding=0,
        ),
        "exp_title": ParagraphStyle(
            "cv_exp_title",
            parent=base["Normal"],
            fontSize=10,
            leading=13,
            textColor=COLOR_PRIMARY,
        ),
        "exp_period": ParagraphStyle(
            "cv_exp_period",
            parent=base["Normal"],
            fontSize=8,
            leading=13,
            textColor=COLOR_LIGHT,
            alignment=TA_LEFT,
            fontName="Helvetica-Oblique",
        ),
        "exp_desc": ParagraphStyle(
            "cv_exp_desc",
            parent=base["Normal"],
            fontSize=8,
            leading=11,
            textColor=COLOR_TEXT,
            leftIndent=3 * mm,
            spaceBefore=1 * mm,
        ),
        "exp_skill": ParagraphStyle(
            "cv_exp_skill",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
            textColor=COLOR_TEXT,
            leftIndent=6 * mm,
        ),
        "exp_link": ParagraphStyle(
            "cv_exp_link",
            parent=base["Normal"],
            fontSize=7,
            leading=10,
            textColor=COLOR_ACCENT,
            leftIndent=3 * mm,
        ),
        "skill_line": ParagraphStyle(
            "cv_skill_line",
            parent=base["Normal"],
            fontSize=8,
            leading=12,
            textColor=COLOR_TEXT,
            spaceBefore=1 * mm,
        ),
    }


def _get_cl_styles():
    """Return all paragraph styles used in the Cover Letter PDF."""
    base = getSampleStyleSheet()

    return {
        "sender": ParagraphStyle(
            "cl_sender",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=COLOR_TEXT,
            alignment=TA_LEFT,
        ),
        "recipient": ParagraphStyle(
            "cl_recipient",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=COLOR_TEXT,
            alignment=TA_LEFT,  # Right-align via table instead
            leftIndent=90 * mm,
        ),
        "date": ParagraphStyle(
            "cl_date",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=COLOR_LIGHT,
            alignment=TA_LEFT,
            leftIndent=90 * mm,
            fontName="Helvetica-Oblique",
        ),
        "object": ParagraphStyle(
            "cl_object",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=COLOR_PRIMARY,
        ),
        "body": ParagraphStyle(
            "cl_body",
            parent=base["Normal"],
            fontSize=10,
            leading=15,
            textColor=COLOR_TEXT,
            alignment=TA_JUSTIFY,
            firstLineIndent=10 * mm,
        ),
    }


# ═══════════════════════════════════════════════════════════════
#  UTILS
# ═══════════════════════════════════════════════════════════════

def _format_french_date(dt: datetime.datetime) -> str:
    """Format a datetime as a French date string like '25 février 2026'."""
    months_fr = [
        "", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    day = dt.day
    month = months_fr[dt.month]
    year = dt.year
    return f"{day} {month} {year}"