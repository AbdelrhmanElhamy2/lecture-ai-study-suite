import os
import re
from pathlib import Path
from typing import List, Optional, Dict
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether, HRFlowable, PageBreak
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

from models import (
    LectureStudyGuide, LectureSection, DoctorAlert, TableDefinition,
    DiagramDefinition, ExamQuestion, KeyFormula
)
from visualizer import generate_diagram, render_formula_image
from config import OUTPUT_DIR, ASSETS_DIR

def format_math_in_text(text: str) -> str:
    """
    Cleans up inline math and converts common LaTeX tokens into crisp, beautiful
    HTML typography and entities for ReportLab paragraphs without raw LaTeX clutter.
    Includes auto-healing for corrupted pseudo-unicode characters (e.g. ∆ rac -> \\frac, ∂∆∁ -> sin).
    """
    if not text:
        return ""
    
    # First sanitize raw Arabic characters
    text = sanitize_pdf_text(text)
    
    # 0. Convert display math delimiters $$ to $
    text = text.replace('$$', '$')
    
    # 1. Clean JSON artifacts where \t, \f, \b were decoded as control chars
    text = text.replace('\x09ext', r'\text').replace('\x09imes', r'\times')
    text = text.replace('\x09heta', r'\theta').replace('\x09hickapprox', r'\approx')
    text = text.replace('\x09o', r'\to').replace('\x09au', r'\tau')
    text = text.replace('\x0c', 'f').replace('\x08', 'b')

    # 2. Auto-heal deformed/corrupted pseudo-unicode tokens
    # Fractions: \u2206 rac{, ∆ rac{, &Delta; rac{, \Delta rac{, or orphan rac{
    text = re.sub(r'(?:\u2206|\u0394|∆)\s*rac\{', r'\\frac{', text)
    text = re.sub(r'(?:&Delta;|\\Delta)\s*rac\{', r'\\frac{', text)
    text = re.sub(r'(?<![a-zA-Z\\])rac\{', r'\\frac{', text)

    # Trig functions auto-healing: \u2202\u2206\u2201 (∂∆∁) -> \sin, \u2202\u2201\u2202 (∂∁∂) -> \cos
    text = re.sub(r'(?:\u2202|∂)(?:\u2206|∆|\u0394)(?:\u2201|∁)?', r'\\sin ', text)
    text = re.sub(r'(?:\u2202|∂)\s*\\?sin', r'\\sin', text)
    text = re.sub(r'(?:\u2202|∂)(?:\u2201|∁)(?:\u2202|∂)', r'\\cos ', text)
    text = re.sub(r'(?:\u2202|∂)\s*\\?cos', r'\\cos', text)

    # Remove tofu box glyphs: \u2201 (∁ - complement which has no standard glyph)
    text = text.replace('\u2201', '').replace('∁', '')

    # Clean stray partial symbols before brackets or negative signs: ∁[- ∂ or [- ∂
    text = re.sub(r'\[-\s*(?:\u2202|∂)', '[- ', text)
    text = re.sub(r'(?:\u2202|∂)\s*\[', '[', text)

    # 3. Unicode mathematical symbols to standard LaTeX
    text = text.replace('\u222b', r'\int ').replace('∫', r'\int ')
    text = text.replace('\u03c0', r'\pi ').replace('π', r'\pi ')
    text = text.replace('\u03c9', r'\omega ').replace('ω', r'\omega ')
    text = text.replace('\u03b8', r'\theta ').replace('θ', r'\theta ')
    text = text.replace('\u03b1', r'\alpha ').replace('α', r'\alpha ')
    text = text.replace('\u03b2', r'\beta ').replace('β', r'\beta ')
    text = text.replace('\u03bb', r'\lambda ').replace('λ', r'\lambda ')
    text = text.replace('\u03bc', r'\mu ').replace('μ', r'\mu ')
    text = text.replace('\u03a9', r'\Omega ').replace('Ω', r'\Omega ')
    text = text.replace('\u2264', r'\le ').replace('≤', r'\le ')
    text = text.replace('\u2265', r'\ge ').replace('≥', r'\ge ')
    text = text.replace('\u2248', r'\approx ').replace('≈', r'\approx ')
    text = text.replace('\u2260', r'\ne ').replace('≠', r'\ne ')
    text = text.replace('\u00d7', r'\times ').replace('×', r'\times ')
    text = text.replace('\u00b1', r'\pm ').replace('±', r'\pm ')

    # Ensure \text{, \frac{, \sqrt{ have leading backslash
    text = re.sub(r'(?<!\\)frac\{', r'\\frac{', text)
    text = re.sub(r'(?<!\\)text\{', r'\\text{', text)
    text = re.sub(r'(?<!\\)sqrt\{', r'\\sqrt{', text)
    
    # 4. \left and \right delimiters (MUST be before \le)
    text = re.sub(r'\\left\s*\(', '(', text)
    text = re.sub(r'\\right\s*\)', ')', text)
    text = re.sub(r'\\left\s*\[', '[', text)
    text = re.sub(r'\\right\s*\]', ']', text)
    text = re.sub(r'\\left\s*\\?\{', '{', text)
    text = re.sub(r'\\right\s*\\?\}', '}', text)
    text = re.sub(r'\\left\s*\|', '|', text)
    text = re.sub(r'\\right\s*\|', '|', text)
    text = re.sub(r'\\left\.', '', text)
    text = re.sub(r'\\right\.', '', text)
    text = re.sub(r'\\left(?![a-zA-Z])', '', text)
    text = re.sub(r'\\right(?![a-zA-Z])', '', text)

    # 5. Text and style wrappers: convert \text{...} to plain text
    text = re.sub(r'\\?text\{([^{}]+)\}', r' \1 ', text)
    text = re.sub(r'\\?mathrm\{([^{}]+)\}', r'\1', text)
    text = re.sub(r'\\?mathbf\{([^{}]+)\}', r'<b>\1</b>', text)

    # 6. Temperatures & Degrees (^\circ\text{C}, ^\circ C, \degree, \circ)
    text = re.sub(r'\^\{\\?circ\}\s*([cCfFkK])', r'&deg;\1', text)
    text = re.sub(r'\^\\?circ\s*([cCfFkK])', r'&deg;\1', text)
    text = re.sub(r'\^\{\\?circ\}', '&deg;', text)
    text = re.sub(r'\^\\?circ', '&deg;', text)
    text = re.sub(r'\\degree', '&deg;', text)
    text = re.sub(r'\\circ', '&deg;', text)
    text = text.replace('^&deg;', '&deg;')

    # 7. Fractions (nested support)
    for _ in range(4):
        text = re.sub(r'\\?frac\{([^{}]+)\}\{([^{}]+)\}', r'(\1 / \2)', text)

    # 8. Square roots and Integrals with limit formatting
    text = re.sub(r'\\?sqrt\{([^{}]+)\}', r'&radic;(\1)', text)
    
    def format_integral(m):
        sub = m.group(1) or ''
        sup = m.group(2) or ''
        res = '&int;'
        if sub:
            sub = sub.strip('_{}')
            res += f'<sub>{sub}</sub>'
        if sup:
            sup = sup.strip('^{}')
            res += f'<sup>{sup}</sup>'
        return res
    text = re.sub(r'\\int(?![a-zA-Z])(?:_(\{?[^{}\s]*\}?))?(?:\^(\{?[^{}\s]*\}?))?', format_integral, text)
    text = re.sub(r'\\int(?![a-zA-Z])', '&int;', text)

    # Evaluation bracket limits: ]_0^\pi -> ]<sub>0</sub><sup>&pi;</sup>
    text = re.sub(r'\]_(\{?[^{}\s]*\}?)\^(\{?[^{}\s]*\}?)', r']<sub>\1</sub><sup>\2</sup>', text)

    # 9. Math & Greek symbols with word-boundary
    symbols = [
        (r'\\times(?![a-zA-Z])', '&times;'),
        (r'\\approx(?![a-zA-Z])', '&asymp;'),
        (r'\\thickapprox(?![a-zA-Z])', '&asymp;'),
        (r'(?<![a-zA-Z])hickapprox(?![a-zA-Z])', '&asymp;'),
        (r'\\pm(?![a-zA-Z])', '&plusmn;'),
        (r'\\mp(?![a-zA-Z])', '&minus;&plus;'),
        (r'\\le(?![a-zA-Z])', '&le;'),
        (r'\\leq(?![a-zA-Z])', '&le;'),
        (r'\\ge(?![a-zA-Z])', '&ge;'),
        (r'\\geq(?![a-zA-Z])', '&ge;'),
        (r'\\ne(?![a-zA-Z])', '&ne;'),
        (r'\\neq(?![a-zA-Z])', '&ne;'),
        (r'\\sin(?![a-zA-Z])', 'sin'),
        (r'\\cos(?![a-zA-Z])', 'cos'),
        (r'\\tan(?![a-zA-Z])', 'tan'),
        (r'\\exp(?![a-zA-Z])', 'exp'),
        (r'\\ln(?![a-zA-Z])', 'ln'),
        (r'\\log(?![a-zA-Z])', 'log'),
        (r'\\cdot(?![a-zA-Z])', '&sdot;'),
        (r'\\Delta(?![a-zA-Z])', '&Delta;'),
        (r'\\Omega(?![a-zA-Z])', '&Omega;'),
        (r'\\alpha(?![a-zA-Z])', '&alpha;'),
        (r'\\beta(?![a-zA-Z])', '&beta;'),
        (r'\\gamma(?![a-zA-Z])', '&gamma;'),
        (r'\\theta(?![a-zA-Z])', '&theta;'),
        (r'\\omega(?![a-zA-Z])', '&omega;'),
        (r'\\pi(?![a-zA-Z])', '&pi;'),
        (r'\\eta(?![a-zA-Z])', '&eta;'),
        (r'\\mu(?![a-zA-Z])', '&mu;'),
        (r'\\lambda(?![a-zA-Z])', '&lambda;'),
        (r'\\sigma(?![a-zA-Z])', '&sigma;'),
        (r'\\infty(?![a-zA-Z])', '&infin;'),
        (r'\\infin(?![a-zA-Z])', '&infin;'),
        (r'\\to(?![a-zA-Z])', '&rarr;'),
        (r'\\rightarrow(?![a-zA-Z])', '&rarr;'),
    ]
    for pat, repl in symbols:
        text = re.sub(pat, repl, text)

    # 10. Escape mathematical inequalities (<, >) inside $...$ BEFORE sub/sup tags are created
    def escape_inequalities(match):
        m = match.group(1)
        m = m.replace('<', '&lt;').replace('>', '&gt;')
        return f"${m}$"

    text = re.sub(r'\$([^\$]+)\$', escape_inequalities, text)

    # Also escape standalone inequalities outside $...$
    text = re.sub(r'(?<=\s)<(?=\s|[\-0-9a-zA-Z])', '&lt;', text)
    text = re.sub(r'(?<=\s)>(?=\s|[\-0-9a-zA-Z])', '&gt;', text)

    # 11. Subscripts
    text = re.sub(r'\_\{([^{}]+)\}', r'<sub>\1</sub>', text)
    text = re.sub(r'\_([a-zA-Z0-9])', r'<sub>\1</sub>', text)

    # 12. Superscripts (including ^+, ^-, ^2, ^{...})
    text = re.sub(r'\^\{([^{}]+)\}', r'<sup>\1</sup>', text)
    text = re.sub(r'\^([\+\-]?[0-9a-zA-Z]|\+|\-)', r'<sup>\1</sup>', text)

    # 13. Format variables and expressions inside $...$
    def format_math_block(match):
        expr = match.group(1).strip()
        # Single variable before <sub>: e.g. I<sub>D</sub> -> <i>I</i><sub>D</sub>
        expr = re.sub(r'(?<![a-zA-Z0-9<i>])([IVTkqePRLvi])<sub>', r'<i>\1</i><sub>', expr)
        # Standalone variable letter: $T$, $k$, $q$, $e$ (excluding C to avoid Coulomb/Celsius clash)
        expr = re.sub(r'(?<![0-9\.\s][0-9])(?<![a-zA-Z0-9<i>])([IVTkqePRL])(?![a-zA-Z0-9_</i>])', r'<i>\1</i>', expr)
        return expr

    text = re.sub(r'\$([^\$]+)\$', format_math_block, text)

    # 14. Strip all $ delimiters
    text = text.replace('$', '')

    # Clean sub/sup curly braces if any remained
    text = text.replace('<sub>{', '<sub>').replace('}</sub>', '</sub>')
    text = text.replace('<sup>{', '<sup>').replace('}</sup>', '</sup>')

    # Clean redundant spaces and punctuation spacing
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = text.replace(' ( ', ' (').replace(' ) ', ') ')
    text = text.replace('( ', '(').replace(' )', ')')
    text = text.replace(' / ', ' / ')
    return text.strip()


# --- TrueType Unicode Font Setup for Windows ---
FONT_REG = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITAL = "Helvetica-Oblique"

try:
    win_fonts = Path("C:/Windows/Fonts")
    if (win_fonts / "arial.ttf").exists():
        pdfmetrics.registerFont(TTFont("CustomArial", str(win_fonts / "arial.ttf")))
        pdfmetrics.registerFont(TTFont("CustomArial-Bold", str(win_fonts / "arialbd.ttf")))
        pdfmetrics.registerFont(TTFont("CustomArial-Italic", str(win_fonts / "ariali.ttf")))
        pdfmetrics.registerFont(TTFont("CustomArial-BoldItalic", str(win_fonts / "arialbi.ttf")))
        registerFontFamily(
            "CustomArial",
            normal="CustomArial",
            bold="CustomArial-Bold",
            italic="CustomArial-Italic",
            boldItalic="CustomArial-BoldItalic"
        )
        FONT_REG = "CustomArial"
        FONT_BOLD = "CustomArial-Bold"
        FONT_ITAL = "CustomArial-Italic"
except Exception:
    pass

# Arabic characters pattern
ARABIC_REGEX = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')

def sanitize_pdf_text(text: str) -> str:
    """Removes raw Arabic characters to ensure no tofu/black boxes render in English PDF."""
    if not text:
        return ""
    if ARABIC_REGEX.search(text):
        text = ARABIC_REGEX.sub('', text)
        text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def clean_cue_text(cue: str, topic_title: str, content: str = "") -> str:
    """Ensures the spoken cue displays in clean English without broken Arabic glyphs, duplicated prefixes, or stray quotes."""
    if not cue:
        return f"Focus on core principles of {topic_title}" if topic_title else "Pay close attention to this topic."
    if ARABIC_REGEX.search(cue):
        cue = ARABIC_REGEX.sub('', cue).strip()
    
    # Strip nested or repeated prefixes like 'The doctor warned:', 'Doctor stated:', 'Doctor emphasized:'
    cleaned = re.sub(r'^(?:The\s+doctor|Doctor)\s+(?:noted|emphasized|warned|stated|stressed|mentioned)\s*[:\-]?\s*', '', cue, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'^(?:The\s+doctor|Doctor)\s+(?:noted|emphasized|warned|stated|stressed|mentioned)\s*[:\-]?\s*', '', cleaned, flags=re.IGNORECASE).strip()
    
    # Strip stray outer quotes and symbols
    cleaned = cleaned.strip(' "\'“”)(\'[]:-.,')
    if len(cleaned) > 8:
        return cleaned
    elif topic_title:
        return f"Pay close attention to: {topic_title}"
    return cue.strip(' "\'“”)(\'[]:-.,')

# --- Numbered Canvas with Header & Footer ---
class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total page count dynamically for 'Page X of Y'."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Skip running header/footer on cover page
            return
        
        self.saveState()
        self.setFont(FONT_REG, 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Running Header
        self.drawString(54, 11 * inch - 36, "Lecture Study Guide & Exam Prep")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)
        
        # Running Footer
        self.line(54, 46, 8.5 * inch - 54, 46)
        self.drawString(54, 32, "Generated by LectureAI - Comprehensive English Study Edition")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 32, page_text)
        
        self.restoreState()


class PDFStudyGuideBuilder:
    """Builds an elegant, publication-quality academic study guide PDF."""

    def __init__(self, guide: LectureStudyGuide, output_filename: Optional[str] = None, options: Optional[Dict[str, bool]] = None):
        self.guide = guide
        self.options = {
            "include_diagrams": True,
            "include_exam_questions": True,
            "include_transcript": True,
            **(options or {}),
        }
        clean_title = "".join(c for c in guide.lecture_title if c.isalnum() or c in (" ", "_", "-")).strip()
        filename = output_filename or f"Lecture_{clean_title[:30]}_Study_Guide.pdf"
        self.output_path = OUTPUT_DIR / filename
        
        self.doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configure academic styling and colors."""
        self.styles.add(ParagraphStyle(
            name="CoverBadge",
            fontName=FONT_BOLD,
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#1D4ED8"),
            alignment=0,
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name="CoverTitle",
            fontName=FONT_BOLD,
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name="CoverMeta",
            fontName=FONT_REG,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#475569"),
            spaceAfter=16
        ))
        self.styles.add(ParagraphStyle(
            name="ExecSummaryHeading",
            fontName=FONT_BOLD,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name="ExecSummaryText",
            fontName=FONT_REG,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#1E293B"),
            spaceAfter=14
        ))
        self.styles.add(ParagraphStyle(
            name="SectionHeading",
            fontName=FONT_BOLD,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1E40AF"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True
        ))
        self.styles.add(ParagraphStyle(
            name="SubSectionHeading",
            fontName=FONT_BOLD,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        ))
        self.styles.add(ParagraphStyle(
            name="LectureBody",
            fontName=FONT_REG,
            fontSize=9.5,
            leading=14.5,
            textColor=colors.HexColor("#1E293B"),
            spaceAfter=8
        ))
        self.styles.add(ParagraphStyle(
            name="BulletPoint",
            fontName=FONT_REG,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1E293B"),
            leftIndent=15,
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name="AlertBadge",
            fontName=FONT_BOLD,
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#B45309"),
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name="AlertCue",
            fontName=FONT_ITAL,
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#78350F"),
            spaceAfter=5
        ))
        self.styles.add(ParagraphStyle(
            name="AlertBody",
            fontName=FONT_REG,
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#451A03"),
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name="AlertImpact",
            fontName=FONT_BOLD,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#92400E"),
            spaceAfter=2
        ))
        self.styles.add(ParagraphStyle(
            name="CaptionText",
            fontName=FONT_ITAL,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#64748B"),
            alignment=1,
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name="TableHead",
            fontName=FONT_BOLD,
            fontSize=9,
            leading=12,
            textColor=colors.white,
            alignment=0
        ))
        self.styles.add(ParagraphStyle(
            name="TableCell",
            fontName=FONT_REG,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#0F172A")
        ))
        self.styles.add(ParagraphStyle(
            name="ExamPrompt",
            fontName=FONT_BOLD,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name="ExamAnswer",
            fontName=FONT_REG,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#065F46"),
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name="ExamRubric",
            fontName=FONT_REG,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name="TranscriptText",
            fontName=FONT_REG,
            fontSize=8.5,
            leading=12.5,
            textColor=colors.HexColor("#334155")
        ))
        self.styles.add(ParagraphStyle(
            name="FormulaTitle",
            fontName=FONT_BOLD,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name="FormulaFallback",
            fontName=FONT_BOLD,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#0F172A"),
            alignment=1,
            spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            name="FormulaVars",
            fontName=FONT_REG,
            fontSize=8.5,
            leading=12.5,
            textColor=colors.HexColor("#334155"),
            spaceAfter=2
        ))
        self.styles.add(ParagraphStyle(
            name="FormulaExam",
            fontName=FONT_ITAL,
            fontSize=8.5,
            leading=12.5,
            textColor=colors.HexColor("#1D4ED8"),
            spaceAfter=2
        ))

    def _build_cover(self) -> List:
        story = []
        is_demo = (
            getattr(self.guide, "is_demo", False)
            or getattr(getattr(self.guide, "verification_report", None), "is_simulation", False)
            or "simulation" in getattr(getattr(self.guide, "verification_report", None), "overall_fidelity_summary", "").lower()
            or bool(self.options.get("is_demo", False))
        )
        # Course badge
        course = self.guide.course_name or "ACADEMIC LECTURE"
        if is_demo:
            story.append(Paragraph(
                f"<font color='#B45309'><b>[DEMO MODE - SIMULATION]</b></font> &nbsp;&nbsp; ACADEMIC STUDY GUIDE - {course.upper()}",
                self.styles["CoverBadge"]
            ))
        else:
            story.append(Paragraph(f"ACADEMIC STUDY GUIDE - {course.upper()}", self.styles["CoverBadge"]))
        
        # Title
        story.append(Paragraph(format_math_in_text(self.guide.lecture_title), self.styles["CoverTitle"]))
        
        # Meta table
        meta_items = []
        if is_demo:
            meta_items.append("<b>Mode:</b> <font color='#B45309'><b>DEMO / SIMULATION (No live audio processed)</b></font>")
        if self.guide.lecturer_name:
            meta_items.append(f"<b>Instructor:</b> {self.guide.lecturer_name}")
        if self.guide.lecture_date:
            meta_items.append(f"<b>Date:</b> {self.guide.lecture_date}")
        if getattr(self.guide, "notes_reference", None):
            meta_items.append(f"<b>Lecture Notes / Slides:</b> {self.guide.notes_reference}")
        meta_items.append("<b>Language:</b> 100% English Academic Synthesis (from bilingual audio)")
        meta_items.append("<b>Includes:</b> Detailed Notes, Spoken Exam Alerts, Diagrams, Practice Questions")
        
        story.append(Paragraph("<br/>".join(meta_items), self.styles["CoverMeta"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=14))
        
        # Executive summary box
        story.append(Paragraph("Executive Overview & Core Lecture Themes", self.styles["ExecSummaryHeading"]))
        story.append(Paragraph(format_math_in_text(self.guide.executive_summary), self.styles["ExecSummaryText"]))
        
        # Guide Features Banner Table
        features = [
            [
                Paragraph("<b>Complete Breakdown</b><br/><font color='#64748B' size=8>Verbatim depth with zero omissions</font>", self.styles["TableCell"]),
                Paragraph("<b>Doctor's Exam Focus</b><br/><font color='#64748B' size=8>Highlighted spoken alerts & traps</font>", self.styles["TableCell"]),
                Paragraph("<b>Charts & Tables</b><br/><font color='#64748B' size=8>Auto-generated visual diagrams</font>", self.styles["TableCell"]),
                Paragraph("<b>Exam Practice Bank</b><br/><font color='#64748B' size=8>Realistic exam-style questions & answers</font>", self.styles["TableCell"])
            ]
        ]
        t = Table(features, colWidths=[126, 126, 126, 126])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)

        # Audio Verification & Contradiction Audit Certificate
        cert = self._build_verification_certificate()
        if cert:
            story.append(Spacer(1, 10))
            story.append(cert)

        story.append(Spacer(1, 15))
        story.append(PageBreak())
        return story

    def _build_verification_certificate(self) -> Optional[Table]:
        report = getattr(self.guide, "verification_report", None)
        if not report:
            if getattr(self.guide, "is_demo", False) or bool(self.options.get("is_demo", False)):
                from models import VerificationAuditReport
                notes_ref = getattr(self.guide, "notes_reference", None)
                report = VerificationAuditReport(
                    audit_passed=True,
                    contradictions_detected=0,
                    contradictions=[],
                    is_simulation=True,
                    overall_fidelity_summary="Verified in simulation: 0 contradictions detected. 100% faithful to lecture simulation.",
                    verified_at="Academic Term 2026",
                    notes_audited=bool(notes_ref),
                    notes_reference=notes_ref,
                    scope_discrepancies_resolved=0
                )
            else:
                return None

        # A report is a simulation audit if explicitly marked as simulation or summary indicates simulation,
        # or if the guide is demo and there are no real contradictions reported.
        is_demo = (
            getattr(report, "is_simulation", False)
            or "simulation" in getattr(report, "overall_fidelity_summary", "").lower()
            or bool(self.options.get("is_demo", False))
            or (getattr(self.guide, "is_demo", False) and not (report.contradictions_detected > 0 and not getattr(report, "is_simulation", False)))
        )

        has_fixes = report.contradictions_detected > 0
        has_notes = getattr(report, "notes_audited", False) or bool(getattr(self.guide, "notes_reference", None))
        notes_ref = getattr(report, "notes_reference", None) or getattr(self.guide, "notes_reference", None)
        scope_tag = " &amp; SLIDES" if has_notes else ""
        is_failed = not getattr(report, "audit_passed", True)

        if is_demo:
            card_bg = colors.HexColor("#FFFBEB")
            border_col = colors.HexColor("#F59E0B")
            title_col = "#B45309"
            if has_notes:
                title_text = f"<font color='{title_col}'><b>DEMO MODE: SIMULATED AUDIO{scope_tag} FIDELITY AUDIT (no real audio checked)</b></font>"
            else:
                title_text = f"<font color='{title_col}'><b>DEMO MODE: SIMULATED AUDIT (no real audio checked)</b></font>"
            status_text = "Verified in simulation against synthetic lecture model (no live audio recording uploaded)."
        elif is_failed:
            card_bg = colors.HexColor("#FEF2F2")
            border_col = colors.HexColor("#DC2626")
            title_col = "#B91C1C"
            title_text = f"<font color='{title_col}'><b>AUDIO{scope_tag} FIDELITY AUDIT: UNAVAILABLE / COULD NOT BE COMPLETED</b></font>"
            status_text = "Verification audit could not be completed (cross-check service unavailable)."
        else:
            card_bg = colors.HexColor("#F0FDF4") if not has_fixes else colors.HexColor("#EFF6FF")
            border_col = colors.HexColor("#059669") if not has_fixes else colors.HexColor("#2563EB")
            title_col = "#047857" if not has_fixes else "#1D4ED8"
            title_text = (
                f"<font color='{title_col}'><b>AUDIO{scope_tag} FIDELITY &amp; CONTRADICTION AUDIT: 100% VERIFIED</b></font>"
                if not has_fixes else
                f"<font color='{title_col}'><b>AUDIO{scope_tag} FIDELITY AUDIT: {report.contradictions_detected} CONTRADICTION(S) RECONCILED WITH RECORDING</b></font>"
            )
            status_text = (
                f"Audio &amp; lecture slides cross-check performed against original recording and slides ({notes_ref})."
                if has_notes and notes_ref else
                ("Audio &amp; lecture slides cross-check performed against recording and slides." if has_notes else "Audio cross-check performed against original lecture recording.")
            )

        body_lines = [
            f"<font size=8.5><b>Verification Status:</b> {status_text}</font>",
            f"<font size=8.5><b>Fidelity Summary:</b> {format_math_in_text(report.overall_fidelity_summary)}</font>"
        ]

        if has_notes and not is_failed:
            body_lines.append(
                "<font size=8.5 color='#047857'><b>Scope &amp; Fidelity Audit:</b> Strictly grounded in spoken lecture. Slide terminology and formulas integrated; unmentioned slide topics excluded.</font>"
            )

        if has_fixes and getattr(report, "contradictions", None):
            body_lines.append("<font size=8.5><b>Reconciliation Log:</b></font>")
            for idx, c in enumerate(report.contradictions[:3], 1):
                clean_sec = format_math_in_text(c.section_title)
                clean_truth = format_math_in_text(c.audio_truth)
                clean_fix = format_math_in_text(c.correction_applied)
                body_lines.append(
                    f"<font size=8 color='#334155'>- <b>{clean_sec}</b>: Reconciled with audio (<i>\"{clean_truth}\"</i>) -&gt; {clean_fix}</font>"
                )

        full_html = f"{title_text}<br/>" + "<br/>".join(body_lines)
        cell = Paragraph(full_html, self.styles["TableCell"])
        t = Table([[cell]], colWidths=[504])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), card_bg),
            ("BOX", (0, 0), (-1, -1), 1.2, border_col),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        return t


    def _build_doctor_alert(self, alert: DoctorAlert) -> Table:
        """Renders an eye-catching highlight box for points the doctor emphasized."""
        type_titles = {
            "EXAM_PREDICTION": "EXAM PREDICTION ALERT",
            "CRITICAL_CONCEPT": "CRITICAL CONCEPT - DOCTOR EMPHASIS",
            "COMMON_PITFALL": "EXAM TRAP / COMMON STUDENT MISTAKE",
            "PROFESSOR_EMPHASIS": "IMPORTANT PROFESSOR FOCUS"
        }
        title_tag = type_titles.get(alert.alert_type, "IMPORTANT DOCTOR'S NOTE")
        
        safe_title = format_math_in_text(alert.highlight_title)
        safe_cue = format_math_in_text(clean_cue_text(alert.cue_detected, alert.highlight_title, alert.alert_content))
        safe_content = format_math_in_text(alert.alert_content)
        safe_impact = format_math_in_text(alert.exam_impact)

        badge_p = Paragraph(f"<b>[!] {title_tag}: {safe_title}</b>", self.styles["AlertBadge"])
        cue_p = Paragraph(f"<b>Spoken Cue:</b> \"{safe_cue}\"", self.styles["AlertCue"])
        content_p = Paragraph(f"<b>Core Concept:</b> {safe_content}", self.styles["AlertBody"])
        impact_p = Paragraph(f"<b>How this appears in exams:</b> {safe_impact}", self.styles["AlertImpact"])
        
        box_data = [[badge_p], [cue_p], [content_p], [impact_p]]
        
        table = Table(box_data, colWidths=[504])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),  # Warm amber/light yellow
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#F59E0B")),
            ("LINELEFT", (0, 0), (0, -1), 4.0, colors.HexColor("#D97706")), # Thick amber indicator
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        return table

    def _build_formula_card(self, formula: KeyFormula, idx: int) -> Table:
        """Renders a textbook-quality formula box with rendered LaTeX equation image and variable definitions."""
        items = []
        clean_name = format_math_in_text(formula.formula_name)
        title_p = Paragraph(f"<b>Equation {idx}: {clean_name}</b>", self.styles["FormulaTitle"])
        items.append(title_p)
        
        # Try rendering high-res equation image
        img_id = re.sub(r'[^a-zA-Z0-9]', '_', formula.formula_name)[:25]
        eq_img_path = ASSETS_DIR / f"formula_{img_id}_{idx}.png"
        rendered_path = render_formula_image(formula.latex_expression, eq_img_path)
        
        if rendered_path and rendered_path.exists():
            try:
                from PIL import Image as PILImage
                with PILImage.open(rendered_path) as pim:
                    pw, ph = pim.size
                aspect = ph / max(pw, 1)
                img_w = min(470, max(160, pw * 0.35))
                img_h = max(24, img_w * aspect)
                img = Image(str(rendered_path), width=img_w, height=img_h)
                items.append(Spacer(1, 3))
                items.append(img)
                items.append(Spacer(1, 4))
            except Exception:
                safe_expr = format_math_in_text(formula.plain_text_expression)
                items.append(Paragraph(f"<b>{safe_expr}</b>", self.styles["FormulaFallback"]))
        else:
            safe_expr = format_math_in_text(formula.plain_text_expression)
            items.append(Paragraph(f"<b>{safe_expr}</b>", self.styles["FormulaFallback"]))
            
        # Variables explanation
        if formula.variables_explanation:
            cleaned_vars = [format_math_in_text(v) for v in formula.variables_explanation]
            vars_str = " - ".join(cleaned_vars)
            items.append(Paragraph(f"<b>Where:</b> {vars_str}", self.styles["FormulaVars"]))
            
        # Exam application note
        if formula.exam_application:
            safe_exam = format_math_in_text(formula.exam_application)
            items.append(Paragraph(f"<b>Exam Note:</b> {safe_exam}", self.styles["FormulaExam"]))
            
        box = Table([[item] for item in items], colWidths=[504])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")), # Light slate
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("LINELEFT", (0, 0), (0, -1), 3.5, colors.HexColor("#2563EB")), # Blue accent line
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        return box

    def _build_table(self, table_def: TableDefinition) -> List:
        """Renders a structured comparison or summary table."""
        items = []
        if table_def.title:
            clean_tbl_title = format_math_in_text(table_def.title)
            items.append(Paragraph(f"<b>Table: {clean_tbl_title}</b>", self.styles["SubSectionHeading"]))
            
        num_cols = len(table_def.columns)
        if num_cols == 0:
            return items
            
        col_width = 504 / num_cols
        
        # Build cells with Paragraphs to support auto-wrapping
        table_matrix = []
        # Header row
        header_cells = [Paragraph(f"<b>{format_math_in_text(col)}</b>", self.styles["TableHead"]) for col in table_def.columns]
        table_matrix.append(header_cells)
        
        # Data rows
        for row in table_def.rows:
            row_cells = []
            for c_idx, cell in enumerate(row):
                cell_str = format_math_in_text(str(cell))
                row_cells.append(Paragraph(cell_str, self.styles["TableCell"]))
            # Pad if shorter
            while len(row_cells) < num_cols:
                row_cells.append(Paragraph("", self.styles["TableCell"]))
            table_matrix.append(row_cells[:num_cols])
            
        t = Table(table_matrix, colWidths=[col_width] * num_cols)
        t_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
        # Alternating row background
        for r in range(1, len(table_matrix)):
            if r % 2 == 0:
                t_style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F8FAFC")))
            else:
                t_style.append(("BACKGROUND", (0, r), (-1, r), colors.white))
                
        t.setStyle(TableStyle(t_style))
        items.append(t)
        
        if table_def.notes:
            clean_notes = format_math_in_text(table_def.notes)
            items.append(Paragraph(f"<i>Note: {clean_notes}</i>", self.styles["CaptionText"]))
        else:
            items.append(Spacer(1, 8))
        return items

    def _build_diagram(self, diagram_def: DiagramDefinition) -> List:
        """Renders diagram using visualizer and embeds image into PDF with strictly preserved aspect ratio and collision-free caption spacing."""
        items = []
        try:
            img_path = generate_diagram(diagram_def, ASSETS_DIR)
            if img_path and img_path.exists():
                from PIL import Image as PILImage
                with PILImage.open(img_path) as pim:
                    pw, ph = pim.size
                    if pim.mode == "RGBA":
                        rgb_im = PILImage.new("RGB", pim.size, (255, 255, 255))
                        rgb_im.paste(pim, mask=pim.split()[3])
                        rgb_im.save(img_path, format="PNG")
                max_w = 480.0
                max_h = 360.0
                scale = min(max_w / max(pw, 1), max_h / max(ph, 1))
                render_w = pw * scale
                render_h = ph * scale
                img = Image(str(img_path), width=render_w, height=render_h)
                clean_title = format_math_in_text(diagram_def.title)
                clean_cap = format_math_in_text(diagram_def.caption)
                
                # Keep image and caption together with clean breathing room
                diag_block = [
                    Spacer(1, 8),
                    img,
                    Spacer(1, 8),
                    Paragraph(f"Figure: {clean_title} - {clean_cap}", self.styles["CaptionText"]),
                    Spacer(1, 8)
                ]
                items.append(KeepTogether(diag_block))
        except Exception as e:
            clean_title = format_math_in_text(diagram_def.title)
            items.append(Paragraph(f"<i>[Diagram: {clean_title}]</i>", self.styles["CaptionText"]))
        return items

    def _build_exam_section(self) -> List:
        """Renders the Exam Prep & Predictions chapter."""
        story = []
        story.append(PageBreak())
        story.append(Paragraph("Exam Readiness: How Questions Will Come in Exams", self.styles["SectionHeading"]))
        story.append(Paragraph(
            "The following practice questions are formulated directly from the professor's spoken cues, "
            "highlighted core concepts, and explicit exam warnings given during this lecture.",
            self.styles["LectureBody"]
        ))
        story.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#CBD5E1"), spaceAfter=12))
        
        for q in self.guide.exam_readiness_section:
            q_elements = []
            
            # Badge
            badge_color = "#DC2626" if "Definite" in q.probability else "#2563EB"
            prob_badge = f"<font color='{badge_color}'><b>[{q.probability.upper()}]</b></font> Question {q.question_number} ({q.question_type})"
            q_elements.append(Paragraph(prob_badge, self.styles["AlertBadge"]))
            
            # Question prompt
            clean_q = format_math_in_text(q.question_prompt)
            q_elements.append(Paragraph(f"<b>Q:</b> {clean_q}", self.styles["ExamPrompt"]))
            
            # MCQ options
            if q.options and len(q.options) > 0:
                opt_lines = [f"&nbsp;&nbsp;&nbsp;&nbsp;{format_math_in_text(opt)}" for opt in q.options]
                opt_text = "<br/>".join(opt_lines)
                q_elements.append(Paragraph(opt_text, self.styles["BulletPoint"]))
                q_elements.append(Spacer(1, 4))
                
            # Solution Box
            clean_ans = format_math_in_text(q.correct_answer)
            clean_rubric = format_math_in_text(q.model_explanation)
            clean_hint = format_math_in_text(clean_cue_text(q.doctor_hint, "Exam focus"))
            sol_items = [
                Paragraph(f"<b>Model Answer / Solution:</b><br/>{clean_ans}", self.styles["ExamAnswer"]),
                Paragraph(f"<b>Grading Rubric & Key Points:</b> {clean_rubric}", self.styles["ExamRubric"]),
                Paragraph(f"<b>Doctor's Spoken Exam Tip:</b> <i>\"{clean_hint}\"</i>", self.styles["AlertCue"])
            ]
            sol_table = Table([[item] for item in sol_items], colWidths=[490])
            sol_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")), # Soft mint green
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#86EFAC")),
                ("LINELEFT", (0, 0), (0, -1), 3.5, colors.HexColor("#16A34A")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            q_elements.append(sol_table)
            q_elements.append(Spacer(1, 12))
            
            story.append(KeepTogether(q_elements))
            
        return story

    def _build_transcript_appendix(self) -> List:
        """Renders the complete translated English lecture transcript."""
        story = []
        story.append(PageBreak())
        story.append(Paragraph("Appendix: Complete Verbatim English Lecture Transcript", self.styles["SectionHeading"]))
        story.append(Paragraph(
            "Below is the complete transcript translated into fluent English for comprehensive review and cross-referencing.",
            self.styles["CaptionText"]
        ))
        story.append(Spacer(1, 6))
        
        # Split into readable paragraphs and format all math expressions cleanly
        transcript_paras = self.guide.full_transcript_english.split("\n\n")
        for p_text in transcript_paras:
            clean = format_math_in_text(p_text.strip())
            if clean:
                story.append(Paragraph(clean, self.styles["TranscriptText"]))
                story.append(Spacer(1, 5))
                
        return story

    def build(self) -> Path:
        """Compiles the entire document and saves the PDF."""
        story = []
        
        # 1. Cover
        story.extend(self._build_cover())
        
        # 2. Detailed Sections
        for section in self.guide.sections:
            clean_sec_title = format_math_in_text(section.topic_title)
            sec_header = f"Chapter {section.section_number}: {clean_sec_title}"
            story.append(Paragraph(sec_header, self.styles["SectionHeading"]))
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#E2E8F0"), spaceAfter=8))
            if section.source_reference:
                story.append(Paragraph(f"<b>Lecture timestamp:</b> {format_math_in_text(section.source_reference)}", self.styles["CoverMeta"]))
            
            # Detailed explanation paragraphs
            for p in section.detailed_explanation.split("\n\n"):
                clean_p = format_math_in_text(p.strip())
                if clean_p:
                    story.append(Paragraph(clean_p, self.styles["LectureBody"]))
                    
            # Key Bullet Points
            if section.key_bullet_points:
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Key Takeaways:</b>", self.styles["SubSectionHeading"]))
                for bp in section.key_bullet_points:
                    story.append(Paragraph(f"- {format_math_in_text(bp)}", self.styles["BulletPoint"]))
                story.append(Spacer(1, 6))

            # Governing Mathematical Formulas & Derivations
            if hasattr(section, "formulas") and section.formulas:
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Governing Mathematical Formulas & Derivations:</b>", self.styles["SubSectionHeading"]))
                for f_idx, f_item in enumerate(section.formulas):
                    story.append(Spacer(1, 4))
                    story.append(KeepTogether([self._build_formula_card(f_item, f_idx + 1)]))
                    story.append(Spacer(1, 6))
                
            # Doctor Alerts (Exam Cues & Highlights)
            for alert in section.doctor_alerts:
                story.append(Spacer(1, 6))
                story.append(KeepTogether([self._build_doctor_alert(alert)]))
                story.append(Spacer(1, 8))
                
            # Diagrams / Flowcharts / Drawings
            if self.options["include_diagrams"]:
                for diag in section.diagrams:
                    story.extend(self._build_diagram(diag))
                
            # Structured Tables
            for tbl in section.tables:
                story.extend(self._build_table(tbl))
                
            story.append(Spacer(1, 10))
            
        # 3. Exam Readiness Section
        if self.options["include_exam_questions"] and self.guide.exam_readiness_section:
            story.extend(self._build_exam_section())
            
        # 4. Verbatim Transcript Appendix
        if self.options["include_transcript"] and self.guide.full_transcript_english:
            story.extend(self._build_transcript_appendix())
            
        # Compile document
        self.doc.build(story, canvasmaker=NumberedCanvas)
        return self.output_path
