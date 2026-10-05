from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class DoctorAlert(BaseModel):
    """Represents a point explicitly highlighted by the lecturer as important or exam-bound."""
    alert_type: str = Field(
        ...,
        description="Type of alert: 'EXAM_PREDICTION', 'CRITICAL_CONCEPT', 'COMMON_PITFALL', or 'PROFESSOR_EMPHASIS'"
    )
    highlight_title: str = Field(
        ...,
        description="A punchy title summarizing the alert in English (e.g. 'Exam Focus: Memory Leaks in Garbage Collection')"
    )
    cue_detected: str = Field(
        ...,
        description="The doctor's spoken cue translated 100% into English (e.g. 'Doctor noted: Pay close attention to this, it will be on the final exam!'). STRICTLY ENGLISH ONLY. DO NOT INCLUDE ARABIC SCRIPT."
    )
    alert_content: str = Field(
        ...,
        description="Detailed English explanation of the point the doctor stressed and why it matters."
    )
    exam_impact: str = Field(
        ...,
        description="Specific advice on how this topic appears in exams and what mistakes students make."
    )

class TableDefinition(BaseModel):
    """Represents a structured comparison or summary table to be rendered in the notes."""
    title: str = Field(..., description="Title of the table (e.g. 'Comparison Between TCP and UDP Protocols')")
    columns: List[str] = Field(..., description="Column header labels")
    rows: List[List[str]] = Field(..., description="Rows of table data (list of cells)")
    notes: Optional[str] = Field(None, description="Optional caption or footnote explaining the table")

class DiagramElement(BaseModel):
    """An element in a diagram (step, node, bar category, or concept)."""
    label: str = Field(..., description="Short name or label of the node/step/bar")
    value: Optional[float] = Field(None, description="Numeric value if chart is quantitative (e.g. 85.0)")
    description: Optional[str] = Field(None, description="Detailed explanatory text or subtitle")

class DiagramDefinition(BaseModel):
    """Instruction for generating a visual chart, flowchart, or concept drawing."""
    diagram_id: str = Field(..., description="Unique alphanumeric identifier (e.g. 'diag_pipeline_flow')")
    title: str = Field(..., description="Title of the diagram")
    diagram_type: str = Field(
        ...,
        description="Type of visual: 'FLOWCHART', 'PROCESS_CYCLE', 'COMPARISON_BAR', or 'CONCEPT_MAP'"
    )
    elements: List[DiagramElement] = Field(..., description="List of nodes/steps/bars to draw")
    caption: str = Field(..., description="Clear caption explaining how this visual reflects the lecture")

class KeyFormula(BaseModel):
    """A governing mathematical equation or formula explained in the lecture."""
    formula_name: str = Field(..., description="Name of the formula, e.g. 'Root Mean Square (RMS) Voltage' or 'Average DC Voltage'")
    latex_expression: str = Field(..., description="Standard LaTeX math equation, e.g. 'V_{rms} = \\frac{V_m}{\\sqrt{2}}'")
    plain_text_expression: str = Field(..., description="Clean text representation with units, e.g. 'V_rms = V_m / sqrt(2)'")
    variables_explanation: List[str] = Field(default_factory=list, description="Definitions of terms, e.g. ['V_m: Peak voltage (V)', 'V_rms: Effective voltage (V)']")
    exam_application: str = Field(default="", description="How this formula is used in exam calculations and common mistakes to watch out for.")

class LectureSection(BaseModel):
    """A comprehensive topical section of the lecture."""
    section_number: int = Field(..., description="1-indexed section order")
    topic_title: str = Field(..., description="Clear, academic topic title")
    source_reference: str = Field(
        default="",
        description="Approximate audio timestamp or span for this section, such as '00:12:30–00:24:10'. Leave blank only when it cannot be determined."
    )
    detailed_explanation: str = Field(
        ...,
        description="Exhaustive, in-depth academic explanation in 100% English covering everything the doctor explained."
    )
    key_bullet_points: List[str] = Field(
        ...,
        description="Concise takeaways and core rules"
    )
    doctor_alerts: List[DoctorAlert] = Field(
        default_factory=list,
        description="Any specific points in this section where the doctor emphasized importance or exam relevance"
    )
    formulas: List[KeyFormula] = Field(
        default_factory=list,
        description="Governing mathematical formulas, derivations, and equations for this section"
    )
    tables: List[TableDefinition] = Field(
        default_factory=list,
        description="Structured comparison or reference tables for this section"
    )
    diagrams: List[DiagramDefinition] = Field(
        default_factory=list,
        description="Diagrams, drawings or flowcharts illustrating this section"
    )

class ExamQuestion(BaseModel):
    """Simulated exam question modeling how the doctor will test this lecture."""
    question_number: int = Field(..., description="Question number")
    question_type: str = Field(
        ...,
        description="'MCQ', 'SHORT_ANSWER', 'PROBLEM_SOLVING', or 'ESSAY'"
    )
    question_prompt: str = Field(..., description="The exam question text in English")
    options: Optional[List[str]] = Field(
        None,
        description="Multiple-choice options if type is MCQ (e.g. ['A) Option 1', 'B) Option 2', ...])"
    )
    correct_answer: str = Field(..., description="The definitive correct answer or model solution")
    model_explanation: str = Field(
        ...,
        description="Grading rubric reasoning: why this answer is correct and what exam graders look for"
    )
    doctor_hint: str = Field(
        ...,
        description="How the doctor hinted at or prepared students for this question in the lecture"
    )
    probability: str = Field(
        default="High Probability Exam Question",
        description="'High Probability Exam Question', 'Definite (Doctor Stated)', or 'Conceptual Check'"
    )

class ContradictionItem(BaseModel):
    """Details of a contradiction or factual discrepancy detected between the guide and audio."""
    section_title: str = Field(..., description="Topic or section where discrepancy occurred")
    guide_statement: str = Field(..., description="What the draft guide claimed or stated")
    audio_truth: str = Field(..., description="What the professor actually said in the audio recording (with timestamp if known)")
    correction_applied: str = Field(..., description="The exact modification made to fix the guide and harmonize with the audio")

class VerificationAuditReport(BaseModel):
    """Audit report of the fact-check comparison against the original lecture recording."""
    audit_passed: bool = Field(default=True, description="True if verification succeeded and contradictions were reconciled")
    contradictions_detected: int = Field(default=0, description="Total count of contradictions identified")
    contradictions: List[ContradictionItem] = Field(default_factory=list, description="List of resolved contradictions")
    overall_fidelity_summary: str = Field(default="100% verified against original lecture recording.", description="Summary of fidelity check")
    verified_at: Optional[str] = Field(default=None, description="ISO timestamp or date of verification")
    notes_audited: bool = Field(default=False, description="True if lecture slides or notes were audited alongside audio")
    notes_reference: Optional[str] = Field(default=None, description="Details of lecture slides or notes audited (e.g. 'Slides 1–25')")
    scope_discrepancies_resolved: int = Field(default=0, description="Count of unmentioned slide topics stripped during audit")

class LectureStudyGuide(BaseModel):
    """Complete structured guide produced from the lecture recording."""
    course_name: str = Field(..., description="Name of the course or subject (e.g. 'Operating Systems CS301')")
    lecture_title: str = Field(..., description="Main topic or title of this specific lecture")
    lecturer_name: str = Field(default="Course Professor", description="Lecturer's name if identified")
    lecture_date: str = Field(default="", description="Date or academic term")
    notes_reference: Optional[str] = Field(default=None, description="Reference to lecture notes or slide range if provided (e.g. 'Slides 1–25')")
    executive_summary: str = Field(
        ...,
        description="High-level overview of everything covered in this lecture and key themes"
    )
    sections: List[LectureSection] = Field(
        ...,
        description="Detailed chronological or topical sections covering all spoken lecture content in English"
    )
    exam_readiness_section: List[ExamQuestion] = Field(
        ...,
        description="Curated bank of predicted exam questions directly inspired by the doctor's cues and focus areas"
    )
    full_transcript_english: str = Field(
        ...,
        description="The full verbatim or high-fidelity transcript translated completely into clean, readable English"
    )
    verification_report: Optional[VerificationAuditReport] = Field(
        default=None,
        description="Verification audit comparing the guide against the original lecture recording"
    )

class VerificationResult(BaseModel):
    """Output schema for Gemini when performing the audio-vs-guide verification pass."""
    contradictions_detected: int = Field(..., description="Number of contradictions found between guide and audio recording")
    contradictions: List[ContradictionItem] = Field(default_factory=list, description="List of detected contradictions")
    fidelity_score: int = Field(default=100, description="Fidelity score out of 100")
    audit_summary: str = Field(..., description="Summary explanation of the cross-check against the audio recording")
    corrected_guide: LectureStudyGuide = Field(..., description="The complete reconciled LectureStudyGuide with all contradictions resolved")

