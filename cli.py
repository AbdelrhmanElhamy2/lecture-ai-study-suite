import argparse
import sys
from pathlib import Path
from pipeline import process_lecture
from config import get_gemini_api_key, set_gemini_api_key, UPLOAD_DIR
from link_downloader import (
    download_from_link,
    download_multiple_links,
    download_from_folder_link,
    detect_local_fall_courses,
    scan_course_folder,
    search_session_in_folder,
    download_selected_folder_items,
    resolve_drive_destination,
    is_drive_target,
    save_summary_to_drive,
)

def split_items(arg_list):
    """Normalize list of inputs that may contain comma-separated or space-separated items."""
    if not arg_list:
        return []
    items = []
    for item in arg_list:
        if isinstance(item, str):
            for part in item.split(","):
                part = part.strip()
                if part:
                    items.append(part)
        else:
            items.append(str(item))
    return items

def main():
    parser = argparse.ArgumentParser(
        description="LectureAI: Transform voice recordings into complete English study guides with diagrams & exam alerts."
    )
    parser.add_argument(
        "--audio", "-a",
        nargs="*",
        help="Path(s) or URL(s) to lecture audio recording(s) (can provide multiple parts for multi-part lectures)"
    )
    parser.add_argument(
        "--key", "-k",
        type=str,
        help="Gemini API Key (optional if already set in environment or .env)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Custom output PDF filename"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run simulation demo using a realistic bilingual lecture without calling external APIs"
    )
    parser.add_argument(
        "--mode",
        choices=["detailed", "revision", "exam"],
        default="detailed",
        help="Guide focus: detailed notes, compact revision, or exam-first prep"
    )
    parser.add_argument(
        "--notes", "-n",
        nargs="*",
        help="Optional path(s) or URL(s) to lecture notes or slide deck(s) (can provide multiple decks)"
    )
    parser.add_argument(
        "--start-slide",
        type=int,
        default=None,
        help="Optional start slide/page number taught in this lecture"
    )
    parser.add_argument(
        "--end-slide",
        type=int,
        default=None,
        help="Optional end slide/page number taught in this lecture"
    )
    parser.add_argument(
        "--folder", "-f",
        type=str,
        help="Google Drive course folder link or local course directory path"
    )
    parser.add_argument(
        "--session", "-s",
        type=str,
        help="Target session to search in course folder (e.g. 'Lecture 1', 'Section 1')"
    )
    parser.add_argument(
        "--course", "-c",
        type=str,
        help="Course or subject name (e.g. 'Bio Informatics', 'Power Electronics') to save downloads directly to its Drive folder"
    )
    parser.add_argument(
        "--record-only",
        action="store_true",
        help="When searching folder by session, process audio recording only (skip matching notes)"
    )
    parser.add_argument(
        "--list-courses",
        action="store_true",
        help="List detected Fall 2026 courses on Google Drive / local storage"
    )
    parser.add_argument(
        "--save-media-to-drive",
        action="store_true",
        default=False,
        help="Also copy/download audio and slide files into Google Drive course folder (default: False, keeps media local to save bandwidth)"
    )
    parser.add_argument("--no-diagrams", action="store_true", help="Omit diagrams from the PDF")
    parser.add_argument("--no-exam-questions", action="store_true", help="Omit exam questions from the PDF")
    parser.add_argument("--no-transcript", action="store_true", help="Omit the transcript appendix from the PDF")

    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("\n" + "="*70)
    print(" [*] LectureAI: Bilingual Lecture-to-Study-Guide & Exam Prep System")
    print("="*70 + "\n")

    if args.list_courses:
        courses = detect_local_fall_courses()
        if not courses:
            print("[!] No local Fall 2026 courses detected.")
        else:
            print(f"[+] Found {len(courses)} Fall 2026 Course Directories:\n")
            for idx, c in enumerate(courses, 1):
                print(f"  {idx}. {c['name']}")
                print(f"     Path: {c['path']}")
                print(f"     Items: {c.get('lecture_count', 0)} lectures, {c.get('record_count', 0)} audio recordings")
        return

    if args.key:
        set_gemini_api_key(args.key)
        print("[+] Gemini API key saved.")

    def cli_progress(message: str, percent: int):
        bar_len = 30
        filled = int(bar_len * percent / 100)
        bar = "#" * filled + "-" * (bar_len - filled)
        sys.stdout.write(f"\r[{bar}] {percent:3d}% - {message}")
        sys.stdout.flush()
        if percent >= 100:
            sys.stdout.write("\n")

    audio_paths = []
    notes_paths = []

    effective_course = args.course or args.folder
    if args.save_media_to_drive:
        drive_audio_dir = resolve_drive_destination(effective_course, "audio", args.session, UPLOAD_DIR)
        drive_notes_dir = resolve_drive_destination(effective_course, "notes", args.session, UPLOAD_DIR)
    else:
        drive_audio_dir = UPLOAD_DIR
        drive_notes_dir = UPLOAD_DIR

    # 1. Folder workflow
    if args.folder:
        folder_target = args.folder
        # Check if folder matches a detected course name
        detected = detect_local_fall_courses()
        for d in detected:
            if d["name"].lower() == folder_target.lower() or d["name"].lower().startswith(folder_target.lower()):
                folder_target = d["path"]
                effective_course = d["name"]
                if args.save_media_to_drive:
                    drive_audio_dir = resolve_drive_destination(effective_course, "audio", args.session, UPLOAD_DIR)
                    drive_notes_dir = resolve_drive_destination(effective_course, "notes", args.session, UPLOAD_DIR)
                print(f"[+] Resolved course '{args.folder}' to: {folder_target}")
                break

        if args.session:
            print(f"[*] Scanning course folder for '{args.session}'...")
            scanned = scan_course_folder(folder_target, cli_progress)
            search_res = search_session_in_folder(scanned, args.session)
            status = search_res.get("status")

            if status == "not_found":
                print(f"\n[!] Session '{args.session}' was not found in folder.")
                avail = search_res.get("available_sessions", [])
                if avail:
                    print(f"    Available sessions detected: {', '.join(str(s) for s in avail)}")
                sys.exit(1)

            if status == "no_record":
                print(f"\n[!] Found notes for '{args.session}' but NO audio recording!")
                print("    Audio is the absolute ground truth for lecture scope. Cannot proceed without recording.")
                sys.exit(1)

            selection_mode = "both"
            if status == "no_notes":
                print(f"\n[*] Note: No slide notes found for '{args.session}'. Proceeding with record-only (Audio only).")
                selection_mode = "record_only"
            elif args.record_only:
                print("\n[*] --record-only specified. Proceeding with audio recording only.")
                selection_mode = "record_only"
            else:
                records_list = search_res.get("records", [])
                notes_list = search_res.get("notes", [])
                print(f"\n[+] Found {len(records_list)} recording(s) and {len(notes_list)} slide deck(s) for '{args.session}':")
                for r in records_list:
                    print(f"    - Audio: {r.get('name', 'Unknown')}")
                for n in notes_list:
                    print(f"    - Slides: {n.get('name', 'Unknown')}")

                if sys.stdin.isatty():
                    print("\nWould you like to:")
                    print("  [1] Add Full Lecture (Notes + Record) [Default]")
                    print("  [2] Just the Record (Audio Only)")
                    choice = input("Enter choice (1/2, default 1): ").strip()
                    if choice == "2":
                        selection_mode = "record_only"

            rec_items = search_res.get("records", [])
            note_items = search_res.get("notes", []) if selection_mode != "record_only" else []

            if rec_items:
                res_recs = download_selected_folder_items(rec_items, drive_audio_dir, "audio", cli_progress)
                for rp, _ in res_recs:
                    audio_paths.append(rp)

            if note_items:
                res_notes = download_selected_folder_items(note_items, drive_notes_dir, "notes", cli_progress)
                for np, _ in res_notes:
                    notes_paths.append(np)
        else:
            # Entire folder download fallback
            f_audio, f_notes, _, _ = download_from_folder_link(folder_target, drive_audio_dir, cli_progress)
            if f_audio:
                audio_paths = [f_audio]
            if f_notes:
                notes_paths = [f_notes]

    # 2. Direct audio inputs
    raw_audio = split_items(args.audio)
    if raw_audio:
        for idx, item in enumerate(raw_audio):
            if item.startswith("http://") or item.startswith("https://"):
                drive_label = f" into Drive ({drive_audio_dir.parent.name})" if is_drive_target(drive_audio_dir) else ""
                print(f"[*] Downloading audio recording link ({idx+1}/{len(raw_audio)}){drive_label}...")
                downloaded = download_multiple_links([item], drive_audio_dir, "audio", cli_progress)
                for p, _ in downloaded:
                    audio_paths.append(p)
            else:
                audio_paths.append(Path(item))

    # 3. Direct notes inputs
    raw_notes = split_items(args.notes)
    if raw_notes:
        for idx, item in enumerate(raw_notes):
            if item.startswith("http://") or item.startswith("https://"):
                drive_label = f" into Drive ({drive_notes_dir.parent.name})" if is_drive_target(drive_notes_dir) else ""
                print(f"[*] Downloading slide deck link ({idx+1}/{len(raw_notes)}){drive_label}...")
                downloaded = download_multiple_links([item], drive_notes_dir, "notes", cli_progress)
                for p, _ in downloaded:
                    notes_paths.append(p)
            else:
                notes_paths.append(Path(item))

    if not args.demo and not audio_paths:
        print("Error: Please provide audio recording(s) with --audio <path/url...>, or a course folder with --folder <path/url> --session <query>, or use --demo to test.")
        sys.exit(1)

    try:
        result = process_lecture(
            audio_path=audio_paths,
            notes_path=notes_paths if notes_paths else None,
            start_slide=args.start_slide,
            end_slide=args.end_slide,
            api_key=args.key,
            use_sample_demo=args.demo,
            custom_output_filename=args.output,
            study_mode=args.mode,
            pdf_options={
                "include_diagrams": not args.no_diagrams,
                "include_exam_questions": not args.no_exam_questions,
                "include_transcript": not args.no_transcript,
            },
            progress_callback=cli_progress
        )

        drive_pdf = save_summary_to_drive(Path(result["pdf_path"]), effective_course)

        print("\n" + "-"*70)
        print("SUCCESS! Study Guide Generated:")
        print(f"   * Course:         {result['course_name']}")
        print(f"   * Lecture:        {result['lecture_title']}")
        if result.get("notes_reference"):
            print(f"   * Lecture Notes:  {result['notes_reference']}")
        print(f"   * Sections:       {result['sections_count']} in-depth chapters")
        print(f"   * Exam Alerts:    {result['alerts_count']} doctor-highlighted points")
        print(f"   * Diagrams:       {result['diagrams_count']} visual figures embedded")
        print(f"   * Exam Prep Bank: {result['exam_questions_count']} predicted questions with answers")
        if "contradictions_detected" in result:
            audit_label = "Audio & Slides Fidelity" if result.get("notes_audited") else "Audio Fidelity"
            print(f"   * {audit_label}: {result['contradictions_detected']} discrepancy/scope issue(s) reconciled")
        print(f"   * Output PDF:     {result['pdf_path']}")
        if drive_pdf:
            print(f"   * Google Drive:   Saved directly to {drive_pdf}")
        print("-"*70 + "\n")

    except Exception as e:
        print(f"\n[!] Error during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


