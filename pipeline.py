import os
import shutil
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from config import UPLOAD_DIR, OUTPUT_DIR, get_gemini_api_key, resolve_gemini_model
from models import LectureStudyGuide
from pedagogy_engine import analyze_lecture_transcript
from pdf_builder import PDFStudyGuideBuilder
from mock_generator import get_sample_bilingual_lecture_guide
from transcription import transcribe_audio_sources, format_transcript

from typing import Optional, Callable, Dict, Any, List, Union, Tuple


def process_lecture(
    audio_path: Optional[Union[Path, List[Path]]] = None,
    notes_path: Optional[Union[Path, List[Path]]] = None,
    start_slide: Optional[int] = None,
    end_slide: Optional[int] = None,
    slide_ranges: Optional[List[Tuple[Optional[int], Optional[int]]]] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    course_hint: Optional[str] = None,
    lecturer_hint: Optional[str] = None,
    study_mode: str = "detailed",
    pdf_options: Optional[Dict[str, bool]] = None,
    use_sample_demo: bool = False,
    custom_output_filename: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    cancellation_check: Optional[Callable[[], None]] = None
) -> Dict[str, Any]:
    """
    Complete end-to-end universal pipeline:
    1. Audio (and optional lecture notes/slides) ingestion (single or multi-part/multi-deck)
    2. Multi-subject transcription & Arabic-to-English translation & pedagogical breakdown
    3. Discipline-tailored diagram generation (flowchart, block diagram, timeline, concept map, etc.)
    4. Publication-quality PDF generation
    """
    callback = progress_callback or (lambda msg, pct: None)
    
    # Normalize paths
    if isinstance(audio_path, (list, tuple)):
        audio_paths = [Path(p) for p in audio_path if p]
    elif audio_path:
        audio_paths = [Path(audio_path)]
    else:
        audio_paths = []

    if isinstance(notes_path, (list, tuple)):
        notes_paths = [Path(p) for p in notes_path if p]
    elif notes_path:
        notes_paths = [Path(notes_path)]
    else:
        notes_paths = []

    demo_run = bool(use_sample_demo or not audio_paths)
    if demo_run:
        callback("Loading comprehensive bilingual lecture simulation...", 20)
        guide = get_sample_bilingual_lecture_guide()
        guide.is_demo = True
        notes_demo_label = None
        if notes_paths or start_slide or end_slide or slide_ranges:
            if slide_ranges and any(sr[0] or sr[1] for sr in slide_ranges):
                labels = []
                for s_r in slide_ranges:
                    s_n = s_r[0] or 1
                    e_n = s_r[1] or 25
                    labels.append(f"Slides {s_n}–{e_n} of 25")
                notes_demo_label = f"{'; '.join(labels)} (Simulation Deck)"
            else:
                s_num = start_slide or 1
                e_num = end_slide or 25
                notes_demo_label = f"Slides {s_num}–{e_num} of 25 (Simulation Deck)"
            guide.notes_reference = notes_demo_label

        if not guide.verification_report:
            from models import VerificationAuditReport
            guide.verification_report = VerificationAuditReport(
                audit_passed=True,
                contradictions_detected=0,
                contradictions=[],
                is_simulation=True,
                overall_fidelity_summary=(
                    "Simulated transcript-to-guide verification; no real recording was processed or checked."
                    if notes_demo_label else
                    "Simulated guide verification; no real lecture material was processed or checked."
                ),
                verified_at="2026-09-22T01:50:00+03:00",
                notes_audited=bool(notes_demo_label),
                notes_reference=notes_demo_label,
                scope_discrepancies_resolved=0
            )
        else:
            guide.verification_report.is_simulation = True
    else:
        for ap in audio_paths:
            if not ap.exists():
                raise FileNotFoundError("Audio recording could not be found.")
            
        key = api_key or get_gemini_api_key()
        if not key:
            raise ValueError(
                "Gemini API key is required for study-guide generation from a live lecture. "
                "Please provide it in the Web UI or configure GEMINI_API_KEY."
            )
        selected_model = resolve_gemini_model(model)
            
        callback("Loading the local Whisper model and transcribing lecture audio...", 12)
        transcripts = transcribe_audio_sources(
            audio_paths,
            progress_callback=callback,
            cancellation_check=cancellation_check,
        )
        transcript_text = format_transcript(transcripts)
        if not transcript_text.strip():
            raise ValueError("Local transcription returned no usable text.")
        callback("Preparing transcript and lecture notes for Gemini...", 48)
        guide = analyze_lecture_transcript(
            transcript_text=transcript_text,
            notes_path=notes_paths if notes_paths else None,
            start_slide=start_slide,
            end_slide=end_slide,
            slide_ranges=slide_ranges,
            api_key=key,
            model=selected_model,
            course_hint=course_hint,
            lecturer_hint=lecturer_hint,
            study_mode=study_mode,
            progress_callback=callback
        )

    callback("Generating visual diagrams, flowcharts, and comparison charts...", 85)
    
    callback("Compiling publication-quality PDF with highlights, tables, and exam prep...", 92)
    builder = PDFStudyGuideBuilder(guide, output_filename=custom_output_filename, options=pdf_options)
    pdf_path = builder.build()
    
    callback("Study guide complete!", 100)
    
    return {
        "success": True,
        "is_demo": demo_run,
        "pdf_path": str(pdf_path),
        "pdf_filename": pdf_path.name,
        "course_name": guide.course_name,
        "lecture_title": guide.lecture_title,
        "lecturer_name": guide.lecturer_name,
        "executive_summary": guide.executive_summary,
        "sections_count": len(guide.sections),
        "exam_questions_count": len(guide.exam_readiness_section),
        "alerts_count": sum(len(s.doctor_alerts) for s in guide.sections),
        "diagrams_count": sum(len(s.diagrams) for s in guide.sections),
        "notes_reference": getattr(guide, "notes_reference", None),
        "notes_audited": guide.verification_report.notes_audited if guide.verification_report else False,
        "scope_discrepancies_resolved": guide.verification_report.scope_discrepancies_resolved if guide.verification_report else 0,
        "verification_passed": guide.verification_report.audit_passed if guide.verification_report else True,
        "contradictions_detected": guide.verification_report.contradictions_detected if guide.verification_report else 0,
        "verification_report": guide.verification_report.model_dump() if guide.verification_report else None,
        "guide": guide.model_dump()
    }

