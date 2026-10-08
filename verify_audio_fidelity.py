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

from config import get_gemini_api_key, DEFAULT_MODEL, OUTPUT_DIR, UPLOAD_DIR
from models import LectureStudyGuide
from pedagogy_engine import verify_and_reconcile_study_guide, slice_pdf_pages
from pdf_builder import PDFStudyGuideBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Verify and reconcile a Lecture Study Guide against the original audio recording and optional lecture notes."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to the original lecture audio file (MP3, M4A, WAV, etc.)"
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
        help="Gemini model to use for the audit (default: gemini-3.8-flash)"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API Key (optional, defaults to environment or .env)"
    )

    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"Error: Audio file not found at: {audio_path}", file=sys.stderr)
        sys.exit(1)

    notes_path = Path(args.notes) if args.notes else None
    if notes_path and not notes_path.exists():
        print(f"Error: Lecture notes file not found at: {notes_path}", file=sys.stderr)
        sys.exit(1)

    guide_path = Path(args.guide)
    if not guide_path.exists():
        print(f"Error: Study guide JSON not found at: {guide_path}", file=sys.stderr)
        sys.exit(1)

    key = args.api_key or get_gemini_api_key()
    if not key:
        print("Error: Gemini API key is required. Set GEMINI_API_KEY in .env or provide --api-key.", file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print("🎓 LECTUREAI: AUDIO & SLIDES FIDELITY AUDITOR")
    print("=" * 70)
    print(f"• Audio Recording: {audio_path.name}")
    if notes_path:
        print(f"• Lecture Slides:  {notes_path.name}")
    print(f"• Guide Input:     {guide_path.name}")
    print(f"• Auditor Model:   {args.model}")
    print("=" * 70)

    # 1. Load guide
    print("\n[1/4] Loading study guide JSON...")
    guide_data = json.loads(guide_path.read_text(encoding="utf-8"))
    draft_guide = LectureStudyGuide.model_validate(guide_data)
    print(f"Loaded: \"{draft_guide.lecture_title}\" ({len(draft_guide.sections)} sections)")

    client = genai.Client(api_key=key)
    uploaded_files = []

    try:
        # 2. Upload audio (and optional notes) to Gemini
        print("\n[2/4] Uploading media files to Gemini API for cross-examination...")
        audio_file = client.files.upload(file=str(audio_path))
        uploaded_files.append(audio_file)
        print(f"• Audio uploaded successfully (URI: {getattr(audio_file, 'uri', 'uploaded')})")

        notes_file = None
        notes_ref_label = None
        if notes_path:
            processed_notes, notes_ref_label = slice_pdf_pages(
                notes_path, start_page=args.start_slide, end_page=args.end_slide, output_dir=UPLOAD_DIR
            )
            notes_file = client.files.upload(file=str(processed_notes))
            uploaded_files.append(notes_file)
            print(f"• Lecture slides uploaded successfully ({notes_ref_label})")

        # 3. Cross-examine & reconcile
        print("\n[3/4] Cross-examining draft guide against spoken audio recording & slides...")
        reconciled_guide, report = verify_and_reconcile_study_guide(
            client=client,
            audio_file=audio_file,
            notes_file=notes_file,
            notes_reference=notes_ref_label,
            guide=draft_guide,
            model=args.model,
            progress_callback=lambda msg, pct: print(f"  [{pct}%] {msg}")
        )

        print("\n" + "-" * 70)
        print("📊 VERIFICATION & FIDELITY AUDIT REPORT:")
        print("-" * 70)
        print(f"• Contradictions / Scope Issues Detected: {report.contradictions_detected}")
        if report.notes_audited:
            print(f"• Lecture Notes Audited:                 {report.notes_reference}")
            print(f"• Scope Leakages Pruned:                 {report.scope_discrepancies_resolved}")
        print(f"• Summary: {report.overall_fidelity_summary}")

        if report.contradictions_detected > 0 and report.contradictions:
            print("\n📝 RESOLUTION LOG:")
            for i, c in enumerate(report.contradictions, 1):
                print(f"\n  Discrepancy #{i}:")
                print(f"  - Section:       {c.section_title}")
                print(f"  - Initial Claim: {c.guide_statement}")
                print(f"  - Audio Truth:   {c.audio_truth}")
                print(f"  - Correction:    {c.correction_applied}")
        else:
            print("\n✓ ZERO CONTRADICTIONS: The study guide is 100% faithful to the recording.")

        # 4. Compile Reconciled PDF
        print("\n[4/4] Compiling finalized, verified PDF with Audio Fidelity Certificate...")
        builder = PDFStudyGuideBuilder(reconciled_guide, output_filename=args.output)
        pdf_path = builder.build()

        # Save reconciled JSON
        reconciled_json_path = guide_path.parent / f"reconciled_{guide_path.name}"
        reconciled_json_path.write_text(
            reconciled_guide.model_dump_json(indent=2),
            encoding="utf-8"
        )

        print("\n" + "=" * 70)
        print("🎉 RECONCILIATION COMPLETE!")
        print(f"• Reconciled PDF Saved:  {pdf_path}")
        print(f"• Reconciled JSON Saved: {reconciled_json_path}")
        print("=" * 70)
    finally:
        for f in uploaded_files:
            try:
                client.files.delete(name=f.name)
            except Exception:
                pass


if __name__ == "__main__":
    main()
