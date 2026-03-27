import copy
import os
import datetime
from io import BytesIO
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
COLOR_PRIMARY    = HexColor("#2C3E50")
COLOR_ACCENT     = HexColor("#2980B9")
COLOR_TEXT       = HexColor("#333333")
COLOR_LIGHT      = HexColor("#7F8C8D")
COLOR_BG_SECTION = HexColor("#ECF0F1")
COLOR_WHITE      = HexColor("#FFFFFF")


# ═══════════════════════════════════════════════════════════════
#  CV AUTO-FIT SPACING CONFIG
# ═══════════════════════════════════════════════════════════════

# Priority order for reduction: reduce first (index 0) before last (index -1).
_SHRINK_ORDER = [
    "exp_spacer",           # Spacer after each experience entry
    "section_spacer",       # Spacer after section title
    "section_space_before", # spaceBefore on section_title style
    "hr_space_after",       # HRFlowable spaceAfter
    "after_header",         # Spacer between header block and HR
    "header_intro_gap",     # Spacer between contact line and intro paragraph
    "header_name_gap",      # Spacer between name and contact line
    "top_margin",           # last resort
    "bottom_margin",        # last resort
]

# Keys that are page margins and must not be increased during the inflate pass.
_MARGIN_KEYS = frozenset(("top_margin", "bottom_margin"))

# Auto-shrink parameters for the cover letter single-page fit.
_CL_SHRINK_RATE           = 0.95   # multiply factor by this each iteration (5 % reduction)
_CL_MAX_SHRINK_ITERATIONS = 15     # 0.95^15 ≈ 0.46 — well beyond any realistic overflow


def _default_spacings():
    """Return a fresh dict of spacing parameters: {name: [current_mm, min_mm, step_mm]}."""
    return {
        "exp_spacer":           [3,  1, 1],
        "section_spacer":       [2,  0, 1],
        "section_space_before": [4,  1, 1],
        "hr_space_after":       [4,  1, 1],
        "after_header":         [4,  1, 1],
        "header_intro_gap":     [3,  1, 1],
        "header_name_gap":      [2,  0, 1],
        "top_margin":           [15, 10, 1],
        "bottom_margin":        [15, 8,  1],
    }


def _build_cv_elements(
    cv_data: dict,
    selected_experiences: list,
    is_supply_chain: bool,
    photo_path,
    tailored_descriptions: dict,
    cv_skills_section: list,
    spacings: dict,
) -> list:
    """Build and return the list of ReportLab flowables for the CV body."""

    styles = _get_cv_styles(spacings["section_space_before"][0])
    elements = []

    perso           = cv_data.get("Perso", [{}])[0]
    all_experiences = cv_data.get("experiences", [])

    nom          = perso.get("nom", "Hugo MANIPOUD")
    numero       = perso.get("numero", "")
    mail         = perso.get("mail", "")
    phrase_intro = perso.get("phrase_intro", {})
    intro        = phrase_intro.get("supply_chain", "") if is_supply_chain else phrase_intro.get("data", "")

    # ─── HEADER: Photo + Name + Contact ──────────────────────────
    name_block = []
    name_block.append(Paragraph(nom, styles["name"]))
    if spacings["header_name_gap"][0] > 0:
        name_block.append(Spacer(1, spacings["header_name_gap"][0] * mm))
    name_block.append(Paragraph(f"📧 {mail}  |  📱 {numero}", styles["contact"]))
    name_block.append(Spacer(1, spacings["header_intro_gap"][0] * mm))
    name_block.append(Paragraph(intro, styles["intro"]))

    if photo_path and os.path.exists(photo_path):
        photo = Image(photo_path, width=22.7 * mm, height=30 * mm)
        photo.hAlign = "LEFT"
        header_table = Table(
            [[photo, name_block]],
            colWidths=[35 * mm, 145 * mm],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
    else:
        for block in name_block:
            elements.append(block)

    elements.append(Spacer(1, spacings["after_header"][0] * mm))
    elements.append(HRFlowable(
        width="100%", thickness=1, color=COLOR_ACCENT,
        spaceAfter=spacings["hr_space_after"][0] * mm, spaceBefore=0
    ))

    # ─── EXPERIENCES SECTION ─────────────────────────────────────
    categories_order = [
        ("etudes",           "Formation"),
        ("certifications",   "Certifications & Formations"),
        ("experiences_pro",  "Expériences Professionnelles"),
        ("projets_perso",    "Projets Personnels"),
        ("benevolat",        "Bénévolat & Associations"),
    ]

    selected_indexes = {exp["index"] for exp in selected_experiences}

    for cat_key, cat_title in categories_order:
        cat_experiences = [
            exp for exp in all_experiences
            if exp.get("categorization") == cat_key and exp.get("index") in selected_indexes
        ]
        if not cat_experiences:
            continue

        elements.append(Paragraph(cat_title.upper(), styles["section_title"]))
        if spacings["section_spacer"][0] > 0:
            elements.append(Spacer(1, spacings["section_spacer"][0] * mm))

        for exp in cat_experiences:
            exp_index  = exp.get("index")
            exp_name   = exp.get("name", "")
            exp_period = exp.get("period", "")
            exp_skills = exp.get("specific_skills", [])
            exp_link   = exp.get("link", "")

            # ── Use tailored description if available, else original ──
            if exp_index in tailored_descriptions and tailored_descriptions[exp_index]:
                exp_desc = tailored_descriptions[exp_index]
            else:
                exp_desc = exp.get("description", "")

            # Title line: name on left, period on right
            title_table = Table(
                [[
                    Paragraph(f"<b>{exp_name}</b>", styles["exp_title"]),
                    Paragraph(exp_period, styles["exp_period"]),
                ]],
                colWidths=[130 * mm, 50 * mm],
            )
            title_table.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            elements.append(title_table)

            if exp_desc:
                elements.append(Paragraph(exp_desc, styles["exp_desc"]))

            if exp_skills:
                for skill in exp_skills:
                    elements.append(Paragraph(f"• {skill}", styles["exp_skill"]))

            if exp_link:
                elements.append(Paragraph(
                    f'🔗 <a href="{exp_link}" color="#2980B9">{exp_link}</a>',
                    styles["exp_link"]
                ))

            elements.append(Spacer(1, spacings["exp_spacer"][0] * mm))

    # ─── SKILLS SECTION ──────────────────────────────────────────
    elements.append(Paragraph("COMPÉTENCES", styles["section_title"]))
    if spacings["section_spacer"][0] > 0:
        elements.append(Spacer(1, spacings["section_spacer"][0] * mm))

    # Build the single skills line:
    # [Français : Natif · Anglais : C1 (IELTS 7,5/9) · Python · pandas · Supply Chain · ...]
    skills_parts = []

    # 1) Languages (always first, from cv.json → skills[0] → langue)
    skills_raw = cv_data.get("all_candidate_skills", [{}])[0]
    for lang in skills_raw.get("langue", []):
        skills_parts.append(f"<b>{lang['name']}</b> : {lang['level']}")

    # 2) AI-selected technical skills (from resume.json → skills_section)
    for skill in cv_skills_section:
        skills_parts.append(skill)

    if skills_parts:
        elements.append(Paragraph(
            "  ·  ".join(skills_parts),
            styles["skill_line"]
        ))

    return elements


def _try_build(elements: list, top_margin: float, bottom_margin: float) -> int:
    """
    Build *elements* into an in-memory PDF and return the number of pages produced.

    Parameters
    ----------
    elements     : ReportLab flowable list (will be consumed — pass a fresh list).
    top_margin   : top margin in mm.
    bottom_margin: bottom margin in mm.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=top_margin * mm,
        bottomMargin=bottom_margin * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )
    doc.build(elements)
    return doc.page


def _shrink_elements(elements: list, factor: float) -> list:
    """
    Return a new list of flowables with sizes scaled down by *factor*.

    - ``Spacer`` heights are multiplied by *factor*.
    - ``Paragraph`` styles get their ``fontSize``, ``leading``,
      ``spaceBefore``, and ``spaceAfter`` reduced by *factor* (fontSize
      never goes below 6 pt, leading never below 7 pt).
    - ``Table`` cells are recursed into.
    - All other flowables are returned as-is.

    Only shrinks (factor < 1.0).  If factor >= 1.0 the original list is
    returned unchanged.
    """
    if factor >= 1.0:
        return list(elements)

    shrunk = []
    for el in elements:
        if isinstance(el, Spacer):
            shrunk.append(Spacer(el.width, el.height * factor))

        elif isinstance(el, Paragraph):
            s = el.style
            new_style = ParagraphStyle(
                s.name + "_s",
                parent=s,
                fontSize=max(6, s.fontSize * factor),
                leading=max(7, s.leading * factor),
                spaceBefore=s.spaceBefore * factor,
                spaceAfter=s.spaceAfter * factor,
            )
            shrunk.append(Paragraph(el.text, new_style))

        elif isinstance(el, Table):
            # Deep-copy preserves colWidths, style, and all table attributes.
            new_table = copy.deepcopy(el)
            for i, row in enumerate(new_table._cellvalues):
                for j, cell in enumerate(row):
                    if isinstance(cell, list):
                        new_table._cellvalues[i][j] = _shrink_elements(cell, factor)
                    elif isinstance(cell, (Paragraph, Spacer)):
                        new_table._cellvalues[i][j] = _shrink_elements([cell], factor)[0]
            shrunk.append(new_table)

        else:
            shrunk.append(el)

    return shrunk


# ═══════════════════════════════════════════════════════════════
#  CV PDF GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_cv_pdf(
    output_path: str,
    cv_data: dict,
    selected_experiences: list,
    is_supply_chain: bool,
    photo_path: str | None,
    tailored_descriptions: dict = {},
    cv_skills_section: list = [],
):
    """
    Generate a clean, professional one-page CV as PDF.

    Uses a two-pass auto-fit system to guarantee single-page output:
      Pass 1 — Shrink spacers incrementally (in priority order) until the
               content fits on one page.  Font sizes are never changed.
      Pass 2 — Inflate spacers back (in reverse priority order) so that
               the page looks full and balanced rather than cramped.

    tailored_descriptions: dict mapping experience index (int) → AI-tailored
    description (str).  Falls back to the original description when absent.
    """

    spacings = _default_spacings()

    # ── Pass 1: Shrink until content fits in exactly one page ────
    while True:
        elements = _build_cv_elements(
            cv_data, selected_experiences, is_supply_chain,
            photo_path, tailored_descriptions, cv_skills_section,
            spacings,
        )
        pages = _try_build(elements, spacings["top_margin"][0], spacings["bottom_margin"][0])

        if pages <= 1:
            break

        # Reduce the highest-priority spacer that still has room to shrink
        reduced = False
        for key in _SHRINK_ORDER:
            val, min_val, step = spacings[key]
            if val - step >= min_val:
                spacings[key][0] = val - step
                reduced = True
                break

        if not reduced:
            # All spacers are already at their minimum — cannot shrink further.
            # Accept the result rather than truncating content.
            break

    # ── Pass 2: Inflate — add back slack so the page looks full ──
    # Try to restore spacing in reverse priority order (least structural first).
    defaults = _default_spacings()
    inflate_keys = [k for k in reversed(_SHRINK_ORDER) if k not in _MARGIN_KEYS]

    for key in inflate_keys:
        while True:
            val, min_val, step = spacings[key]
            new_val = val + step
            if new_val > defaults[key][0]:
                break  # never exceed the original default
            test_spacings = {k: list(v) for k, v in spacings.items()}
            test_spacings[key][0] = new_val
            test_elements = _build_cv_elements(
                cv_data, selected_experiences, is_supply_chain,
                photo_path, tailored_descriptions, cv_skills_section,
                test_spacings,
            )
            if _try_build(test_elements, test_spacings["top_margin"][0], test_spacings["bottom_margin"][0]) == 1:
                spacings[key][0] = new_val
            else:
                break

    # ── Final build to the real output file ──────────────────────
    elements = _build_cv_elements(
        cv_data, selected_experiences, is_supply_chain,
        photo_path, tailored_descriptions, cv_skills_section,
        spacings,
    )
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=spacings["top_margin"][0] * mm,
        bottomMargin=spacings["bottom_margin"][0] * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )
    doc.build(elements)


# ═══════════════════════════════════════════════════════════════
#  COVER LETTER PDF GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_cover_letter_pdf(
    output_path: str,
    cv_data: dict,
    match: dict,
    date: str,
    signature_path: str = os.path.join("inputs", "signature.png"),  # ← NEW
):
    """Generate a clean French-format cover letter as PDF.

    An auto-shrink pass ensures the letter always fits on exactly one A4
    page.  If the content overflows, Spacer heights and Paragraph
    leading/fontSize are reduced proportionally (via ``_shrink_elements``)
    until everything fits.  Nothing is ever truncated.
    """

    styles = _get_cl_styles()
    elements = []

    perso  = cv_data.get("Perso", [{}])[0]
    nom    = perso.get("nom", "Hugo MANIPOUD")
    numero = perso.get("numero", "")
    mail   = perso.get("mail", "")

    company           = match.get("company", "")
    location          = match.get("location", "")
    offer_name        = match.get("name", "")
    cover_letter_text = match.get("cover_letter", "")

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

    # ─── DATE ────────────────────────────────────────────────────
    elements.append(Paragraph(f"Le {french_date}", styles["date"]))
    elements.append(Spacer(1, 10 * mm))

    # ─── OBJECT LINE ─────────────────────────────────────────────
    elements.append(Paragraph(
        f"<b>Objet :</b> Candidature — {offer_name}",
        styles["object"]
    ))
    elements.append(Spacer(1, 8 * mm))

    # ─── LETTER BODY ─────────────────────────────────────────────
    for para_text in cover_letter_text.split("\n"):
        para_text = para_text.strip()
        if not para_text:
            elements.append(Spacer(1, 3 * mm))
        else:
            elements.append(Paragraph(para_text, styles["body"]))
            elements.append(Spacer(1, 2 * mm))

    # ─── SIGNATURE BLOCK ─────────────────────────────────────────
    elements.append(Spacer(1, 8 * mm))

    # Name + signature image aligned to the right
    if os.path.exists(signature_path):
        sig_image = Image(signature_path, width=40 * mm, height=20 * mm)
        sig_image.hAlign = "RIGHT"

        sig_table = Table(
            [[
                "",  # empty left cell to push everything right
                [
                    Paragraph(nom, styles["signature_name"]),
                    Spacer(1, 2 * mm),
                    sig_image,
                ]
            ]],
            colWidths=[95 * mm, 65 * mm],
        )
        sig_table.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(sig_table)
    else:
        # No signature image — just the name right-aligned
        print(f"  [WARN] Signature not found: {signature_path} — name only")
        elements.append(Paragraph(nom, styles["signature_name"]))

    # ─── AUTO-SHRINK: ensure everything fits on one page ─────────
    # Build to an in-memory buffer first; if more than one page is
    # produced, reduce Spacer heights and Paragraph leading/fontSize
    # by 5 % per iteration until the content fits.  Since overflow is
    # typically only 1–2 lines, convergence happens in 1–2 steps and
    # the visual difference is imperceptible.
    _cl_doc_kwargs = dict(
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
    )

    shrink_factor = 1.0
    fit_elements = elements

    for _ in range(_CL_MAX_SHRINK_ITERATIONS):
        buf = BytesIO()
        test_doc = SimpleDocTemplate(buf, **_cl_doc_kwargs)
        test_doc.build(copy.deepcopy(fit_elements))
        if test_doc.page <= 1:
            break
        shrink_factor *= _CL_SHRINK_RATE
        fit_elements = _shrink_elements(elements, shrink_factor)

    # ─── BUILD FINAL PDF ─────────────────────────────────────────
    doc = SimpleDocTemplate(output_path, **_cl_doc_kwargs)
    doc.build(fit_elements)

# ═══════════════════════════════════════════════════════════════
#  STYLES
# ═════════════════════════════════════════════���═════════════════

def _get_cv_styles(section_space_before_mm: float = 4):
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "cv_name", parent=base["Title"],
            fontSize=20, leading=24, textColor=COLOR_PRIMARY,
            alignment=TA_LEFT, spaceAfter=0,
        ),
        "contact": ParagraphStyle(
            "cv_contact", parent=base["Normal"],
            fontSize=9, leading=12, textColor=COLOR_LIGHT, alignment=TA_LEFT,
        ),
        "intro": ParagraphStyle(
            "cv_intro", parent=base["Normal"],
            fontSize=9, leading=13, textColor=COLOR_TEXT,
            alignment=TA_LEFT, fontName="Helvetica-Oblique",
        ),
        "section_title": ParagraphStyle(
            "cv_section_title", parent=base["Heading2"],
            fontSize=11, leading=14, textColor=COLOR_ACCENT,
            spaceBefore=section_space_before_mm * mm, spaceAfter=1 * mm,
            borderWidth=0, borderPadding=0,
        ),
        "exp_title": ParagraphStyle(
            "cv_exp_title", parent=base["Normal"],
            fontSize=10, leading=13, textColor=COLOR_PRIMARY,
        ),
        "exp_period": ParagraphStyle(
            "cv_exp_period", parent=base["Normal"],
            fontSize=8, leading=13, textColor=COLOR_LIGHT,
            alignment=TA_LEFT, fontName="Helvetica-Oblique",
        ),
        "exp_desc": ParagraphStyle(
            "cv_exp_desc", parent=base["Normal"],
            fontSize=8, leading=11, textColor=COLOR_TEXT,
            leftIndent=3 * mm, spaceBefore=1 * mm,
        ),
        "exp_skill": ParagraphStyle(
            "cv_exp_skill", parent=base["Normal"],
            fontSize=8, leading=10, textColor=COLOR_TEXT, leftIndent=6 * mm,
        ),
        "exp_link": ParagraphStyle(
            "cv_exp_link", parent=base["Normal"],
            fontSize=7, leading=10, textColor=COLOR_ACCENT, leftIndent=3 * mm,
        ),
        "skill_line": ParagraphStyle(
            "cv_skill_line", parent=base["Normal"],
            fontSize=8, leading=12, textColor=COLOR_TEXT, spaceBefore=1 * mm,
        ),
    }


def _get_cl_styles():
    base = getSampleStyleSheet()
    return {
        "sender": ParagraphStyle(
            "cl_sender", parent=base["Normal"],
            fontSize=10, leading=14, textColor=COLOR_TEXT, alignment=TA_LEFT,
        ),
        "recipient": ParagraphStyle(
            "cl_recipient", parent=base["Normal"],
            fontSize=10, leading=14, textColor=COLOR_TEXT,
            alignment=TA_LEFT, leftIndent=90 * mm,
        ),
        "date": ParagraphStyle(
            "cl_date", parent=base["Normal"],
            fontSize=9, leading=12, textColor=COLOR_LIGHT,
            alignment=TA_LEFT, leftIndent=90 * mm, fontName="Helvetica-Oblique",
        ),
        "object": ParagraphStyle(
            "cl_object", parent=base["Normal"],
            fontSize=10, leading=14, textColor=COLOR_PRIMARY,
        ),
        "body": ParagraphStyle(
            "cl_body", parent=base["Normal"],
            fontSize=10, leading=15, textColor=COLOR_TEXT,
            alignment=TA_JUSTIFY, firstLineIndent=10 * mm,
        ),
        "signature_name": ParagraphStyle(       # ← NEW
            "cl_signature_name", parent=base["Normal"],
            fontSize=10, leading=14, textColor=COLOR_TEXT,
            alignment=TA_LEFT, fontName="Helvetica-Bold",
        ),
    }


# ═══════════════════════════════════════════════════════════════
#  UTILS
# ═══════════════════════════════════════════════════════════════

def _format_french_date(dt: datetime.datetime) -> str:
    months_fr = [
        "", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    return f"{dt.day} {months_fr[dt.month]} {dt.year}"