"""
Standalone Audio-vs-Guide Verification & Contradiction Resolver Tool.

Allows students and professors to take an existing lecture audio recording and
a generated study guide JSON, cross-examine them for any contradictions or discrepancies,
and compile an updated, reconciled publication PDF with an Audio Fidelity Certificate.
"""

import sys
import json
import argparse
from pathlib import Path
from google import genai

from config import get_gemini_api_key, DEFAULT_MODEL, OUTPUT_DIR, UPLOAD_DIR, resolve_gemini_model
from models import LectureStudyGuide
from pedagogy_engine import verify_and_reconcile_study_guide, slice_pdf_pages
from pdf_builder import PDFStudyGuideBuilder
from transcription import transcribe_audio_sources, format_transcript


def main():
    parser = argparse.ArgumentParser(description="Verify a study guide against a local transcript and optional lecture notes.")
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to lecture audio; it is transcribed locally and never uploaded to Gemini."
    )
    parser.add_argument(
        "--notes",
        default=None,
        help="Optional path to the lecture notes or slides (PDF, TXT, MD)"
    )
    parser.add_argument(
        "--start-slide",
        type=int,
        default=None,
        help="Optional start slide number covered in this lecture"
    )
    parser.add_argument(
        "--end-slide",
        type=int,
        default=None,
        help="Optional end slide number covered in this lecture"
    )
    parser.add_argument(
        "--guide",
        default="cached_last_guide.json",
        help="Path to the study guide JSON to audit (default: cached_last_guide.json)"
    )
    parser.add_argument(
        "--output",
        default="Reconciled_Verified_Study_Guide.pdf",
        help="Output filename for the corrected PDF (saved in output_pdfs/)"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=["gemini-3.8-flash", "gemini-3.6-flash"],
        help="Gemini model to use for the transcript audit."
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API Key (optional, defaults to environment or .env)"
    )

    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print("Error: Audio file not found.", file=sys.stderr)
        sys.exit(1)

    notes_path = Path(args.notes) if args.notes else None
    if notes_path and not notes_path.exists():
        print("Error: Lecture notes file not found.", file=sys.stderr)
        sys.exit(1)

    guide_path = Path(args.guide)
    if not guide_path.exists():
        print("Error: Study guide JSON not found.", file=sys.stderr)
        sys.exit(1)

    key = args.api_key or get_gemini_api_key()
    if not key:
        print("Error: Gemini API key is required. Set GEMINI_API_KEY in .env or provide --api-key.", file=sys.stderr)
        sys.exit(1)
    try:
        model = resolve_gemini_model(args.model)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print("🎓 LECTUREAI: LOCAL TRANSCRIPT & SLIDES AUDITOR")
    print("=" * 70)
    print(f"• Audio Recording: {audio_path.name}")
    if notes_path:
        print(f"• Lecture Slides:  {notes_path.name}")
    print(f"• Guide Input:     {guide_path.name}")
    print(f"• Auditor Model:   {model}")
    print("=" * 70)

    # 1. Load guide
    print("\n[1/4] Loading study guide JSON...")
    guide_data = json.loads(guide_path.read_text(encoding="utf-8"))
    draft_guide = LectureStudyGuide.model_validate(guide_data)
    print(f"Loaded: \"{draft_guide.lecture_title}\" ({len(draft_guide.sections)} sections)")

    print("\n[2/4] Transcribing audio locally with faster-whisper...")
    transcripts = transcribe_audio_sources([audio_path])
    transcript_text = format_transcript(transcripts)

    client = genai.Client(api_key=key)
    notes_file = None
    try:
        notes_ref_label = None
        if notes_path:
            processed_notes, notes_ref_label = slice_pdf_pages(
                notes_path, start_page=args.start_slide, end_page=args.end_slide, output_dir=UPLOAD_DIR
            )
            notes_file = client.files.upload(file=str(processed_notes))

        print("\n[3/4] Checking the guide against the transcript and optional slides...")
        reconciled_guide, report = verify_and_reconcile_study_guide(
            client=client,
            transcript_text=transcript_text,
            notes_file=notes_file,
            notes_reference=notes_ref_label,
            guide=draft_guide,
            model=model,
            progress_callback=lambda msg, pct: print(f"  [{pct}%] {msg}")
        )

        print("\n" + "-" * 70)
        print("📊 TRANSCRIPT VERIFICATION REPORT:")
        print("-" * 70)
        print(f"• Discrepancies Detected: {report.contradictions_detected}")
        if report.notes_audited:
            print(f"• Lecture Notes Audited: {report.notes_reference}")
            print(f"• Scope Issues Resolved: {report.scope_discrepancies_resolved}")
        print(f"• Summary: {report.overall_fidelity_summary}")
        print("• Audio-to-transcript accuracy was not independently verified.")

        print("\n[4/4] Compiling reconciled study guide...")
        builder = PDFStudyGuideBuilder(reconciled_guide, output_filename=args.output)
        pdf_path = builder.build()
        reconciled_json_path = guide_path.parent / f"reconciled_{guide_path.name}"
        reconciled_json_path.write_text(reconciled_guide.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nReconciled PDF saved: {pdf_path}")
        print(f"Reconciled JSON saved: {reconciled_json_path}")
    finally:
        if notes_file is not None:
            try:
                client.files.delete(name=notes_file.name)
            except Exception:
                pass


if __name__ == "__main__":
    main()
