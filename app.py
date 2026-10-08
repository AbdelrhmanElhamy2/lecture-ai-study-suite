import os
import sys
import uuid
import threading
import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Union, Dict, Any, Tuple, Callable
from fastapi import FastAPI, Request, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from config import UPLOAD_DIR, OUTPUT_DIR, ASSETS_DIR, SUPPORTED_AUDIO_EXTS, SUPPORTED_NOTES_EXTS, get_gemini_api_key, set_gemini_api_key
from pipeline import process_lecture
from pedagogy_engine import slice_pdf_pages
import shutil
from link_downloader import (
    download_from_link,
    download_from_folder_link,
    download_multiple_links,
    detect_local_fall_courses,
    search_session_in_folder,
    download_selected_folder_items,
    resolve_drive_destination,
    is_drive_target,
    save_summary_to_drive,
    validate_course_folder_path,
)

app = FastAPI(title="LectureAI Study Suite", version="1.0.0")

# The dashboard and API are served from the same local origin. Do not enable
# cross-origin access; require browser mutations to come from that dashboard.
ALLOWED_BROWSER_ORIGINS = {
    "http://127.0.0.1:8000",
    "http://localhost:8000",
}


def is_test_environment() -> bool:
    """Returns True only when explicitly running under an automated test runner."""
    return os.environ.get("LECTUREAI_TESTING", "").lower() in ("1", "true")


@app.middleware("http")
async def protect_local_mutations(request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        host = request.headers.get("host")
        allow_testserver = is_test_environment()
        is_allowed = (
            origin in ALLOWED_BROWSER_ORIGINS
            or (allow_testserver and (origin in {"http://testserver", "testserver"} or host == "testserver"))
            or (origin is None and host in {"127.0.0.1:8000", "localhost:8000"})
            or (allow_testserver and origin is None and host == "testserver")
        )
        if not is_allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": "Requests must come from the local LectureAI dashboard."},
            )
    return await call_next(request)

# Mount generated assets for inline image viewing
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# In-memory job tracker and cancellation signals
jobs: Dict[str, Any] = {}
cancel_events: Dict[str, threading.Event] = {}
HISTORY_FILE = Path(__file__).parent / "lecture_history.json"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB, suitable for long personal lectures.


class JobCancelledException(Exception):
    """Raised when a running background job has been cancelled."""
    pass


def is_job_cancelled(job_id: str) -> bool:
    job = jobs.get(job_id)
    if not job:
        return True
    if job.get("cancelled", False) or job.get("status") == "cancelled":
        return True
    ev = cancel_events.get(job_id)
    if ev and ev.is_set():
        return True
    return False


def load_history():
    """Return local history without failing the app when an older file is malformed."""
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []
    except (OSError, json.JSONDecodeError):
        return []


def sanitize_display_name(name: Optional[str]) -> str:
    """Removes URLs, link query tokens, and absolute folder paths from user-facing names."""
    if not name:
        return "Lecture Item"
    cleaned = str(name).strip()
    if cleaned.startswith(("http://", "https://")) or "drive.google.com" in cleaned:
        try:
            parsed = urllib.parse.urlparse(cleaned)
            p = parsed.path.strip("/")
            cleaned = p.split("/")[-1] if p else "Drive Link"
        except Exception:
            cleaned = "Drive Link"
    cleaned = Path(cleaned).name
    if "?" in cleaned:
        cleaned = cleaned.split("?")[0]
    return cleaned or "Lecture Item"


def format_sources_summary(audio_items: List[Dict[str, Any]], notes_items: List[Dict[str, Any]]) -> str:
    """Creates privacy-safe source kinds summary e.g. '2 recordings (computer + link), 1 notes (course folder)'."""
    parts = []
    kind_display_map = {
        "upload": "computer",
        "link": "link",
        "folder": "course folder"
    }
    if audio_items:
        rec_kinds = []
        for k in ["upload", "link", "folder"]:
            if any(item.get("kind") == k for item in audio_items):
                rec_kinds.append(kind_display_map[k])
        kinds_str = " + ".join(rec_kinds) if rec_kinds else "mixed"
        rec_count = len(audio_items)
        rec_word = "recording" if rec_count == 1 else "recordings"
        parts.append(f"{rec_count} {rec_word} ({kinds_str})")

    if notes_items:
        notes_kinds = []
        for k in ["upload", "link", "folder"]:
            if any(item.get("kind") == k for item in notes_items):
                notes_kinds.append(kind_display_map[k])
        kinds_str = " + ".join(notes_kinds) if notes_kinds else "mixed"
        notes_count = len(notes_items)
        parts.append(f"{notes_count} notes ({kinds_str})")

    return ", ".join(parts) if parts else "Unknown sources"


def save_history_entry(
    result: dict,
    source_name: str,
    study_mode: str,
    notes_source: Optional[str] = None,
    sources_summary: Optional[str] = None
) -> None:
    history = load_history()
    clean_source_name = sanitize_display_name(source_name)
    clean_notes_source = sanitize_display_name(notes_source) if notes_source else None
    history.insert(0, {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_name": clean_source_name,
        "notes_source": clean_notes_source,
        "sources_summary": sources_summary or clean_source_name,
        "notes_reference": result.get("notes_reference"),
        "study_mode": study_mode,
        "result": result,
    })
    HISTORY_FILE.write_text(json.dumps(history[:50], ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_mixed_sources(
    sources: List[Dict[str, Any]],
    staged_upload_map: Dict[str, Path],
    drive_audio_dir: Path,
    drive_notes_dir: Path,
    update_progress: Callable[[str, int], None],
    check_cancellation: Callable[[], None]
) -> Tuple[List[Path], List[Path], List[str], List[str], List[Tuple[Optional[int], Optional[int]]], List[Path]]:
    """
    Resolves an ordered list of mixed sources (computer upload, link, course folder)
    into concrete local file paths strictly preserving the user's defined order.
    Returns:
      (final_audio_paths, final_notes_paths, audio_names, notes_names, slide_ranges, newly_staged_paths)
    On any item failure, raises a descriptive Exception with the item name and reason.
    """
    audio_items = sorted([s for s in sources if s.get("role") == "audio"], key=lambda x: x.get("order", 0))
    notes_items = sorted([s for s in sources if s.get("role") == "notes"], key=lambda x: x.get("order", 0))

    final_audio_paths: List[Path] = []
    final_notes_paths: List[Path] = []
    audio_names: List[str] = []
    notes_names: List[str] = []
    slide_ranges: List[Tuple[Optional[int], Optional[int]]] = []
    newly_staged_paths: List[Path] = []

    try:
        # 1. Resolve Audio Items in Order
        total_audio = len(audio_items)
        for idx, item in enumerate(audio_items):
            check_cancellation()
            item_id = item.get("id", str(idx))
            display_name = sanitize_display_name(item.get("display_name") or f"Recording {idx+1}")
            kind = item.get("kind", "upload")
            pct = 5 + int(15 * (idx + 1) / max(1, total_audio))

            if kind == "upload":
                update_progress(f"Verifying computer audio ({idx+1}/{total_audio}: {display_name})...", pct)
                staged_p = staged_upload_map.get(item_id)
                if not staged_p or not staged_p.exists():
                    raise FileNotFoundError(f"Uploaded audio file '{display_name}' was not found in staging area.")
                suffix = staged_p.suffix.lower()
                if suffix not in SUPPORTED_AUDIO_EXTS:
                    raise ValueError(f"Unsupported audio format '{suffix}' in {display_name}. Use: {', '.join(sorted(SUPPORTED_AUDIO_EXTS))}.")
                final_audio_paths.append(staged_p)
                audio_names.append(display_name)

            elif kind == "link":
                link_url = item.get("link")
                if not link_url:
                    raise ValueError(f"Missing URL link for audio item '{display_name}'.")
                update_progress(f"Downloading audio from link ({idx+1}/{total_audio}: {display_name})...", pct)
                try:
                    dl_p, orig_name = download_from_link(
                        url=link_url,
                        target_dir=drive_audio_dir,
                        expected_type="audio",
                        progress_callback=update_progress
                    )
                except Exception as dl_err:
                    raise RuntimeError(f"Failed to download audio link '{display_name}': {dl_err}")
                newly_staged_paths.append(dl_p)
                final_audio_paths.append(dl_p)
                audio_names.append(sanitize_display_name(orig_name or display_name))

            elif kind == "folder":
                update_progress(f"Resolving course folder audio ({idx+1}/{total_audio}: {display_name})...", pct)
                local_path = item.get("local_path")
                if local_path:
                    try:
                        folder_p = validate_course_folder_path(local_path)
                    except Exception as val_err:
                        raise RuntimeError(f"Course folder audio '{display_name}' rejected: {val_err}")
                    suffix = folder_p.suffix.lower()
                    if suffix not in SUPPORTED_AUDIO_EXTS:
                        raise ValueError(f"Unsupported audio format '{suffix}' in course folder item {display_name}.")
                    final_audio_paths.append(folder_p)
                    audio_names.append(display_name)
                else:
                    remote_id = item.get("id") or item.get("link")
                    if not remote_id:
                        raise FileNotFoundError(f"Course folder audio '{display_name}' has neither local path nor remote ID.")
                    remote_url = f"https://drive.google.com/uc?id={remote_id}" if not str(remote_id).startswith("http") else str(remote_id)
                    try:
                        dl_p, orig_name = download_from_link(
                            url=remote_url,
                            target_dir=drive_audio_dir,
                            expected_type="audio",
                            progress_callback=update_progress
                        )
                    except Exception as dl_err:
                        raise RuntimeError(f"Failed to download course folder audio '{display_name}': {dl_err}")
                    newly_staged_paths.append(dl_p)
                    final_audio_paths.append(dl_p)
                    audio_names.append(sanitize_display_name(orig_name or display_name))

            else:
                raise ValueError(f"Unknown source kind '{kind}' for audio item '{display_name}'.")

        # 2. Resolve Notes Items in Order
        total_notes = len(notes_items)
        for idx, item in enumerate(notes_items):
            check_cancellation()
            item_id = item.get("id", str(idx))
            display_name = sanitize_display_name(item.get("display_name") or f"Notes {idx+1}")
            kind = item.get("kind", "upload")
            pct = 20 + int(10 * (idx + 1) / max(1, total_notes))

            if kind == "upload":
                update_progress(f"Verifying computer notes ({idx+1}/{total_notes}: {display_name})...", pct)
                staged_p = staged_upload_map.get(item_id)
                if not staged_p or not staged_p.exists():
                    raise FileNotFoundError(f"Uploaded notes file '{display_name}' was not found in staging area.")
                suffix = staged_p.suffix.lower()
                if suffix not in SUPPORTED_NOTES_EXTS:
                    raise ValueError(f"Unsupported lecture notes format '{suffix}' in {display_name}. Use: {', '.join(sorted(SUPPORTED_NOTES_EXTS))}.")
                notes_p = staged_p

            elif kind == "link":
                link_url = item.get("link")
                if not link_url:
                    raise ValueError(f"Missing URL link for notes item '{display_name}'.")
                update_progress(f"Downloading notes from link ({idx+1}/{total_notes}: {display_name})...", pct)
                try:
                    dl_p, orig_name = download_from_link(
                        url=link_url,
                        target_dir=drive_notes_dir,
                        expected_type="notes",
                        progress_callback=update_progress
                    )
                except Exception as dl_err:
                    raise RuntimeError(f"Failed to download notes link '{display_name}': {dl_err}")
                newly_staged_paths.append(dl_p)
                notes_p = dl_p
                display_name = sanitize_display_name(orig_name or display_name)

            elif kind == "folder":
                update_progress(f"Resolving course folder notes ({idx+1}/{total_notes}: {display_name})...", pct)
                local_path = item.get("local_path")
                if local_path:
                    try:
                        folder_p = validate_course_folder_path(local_path)
                    except Exception as val_err:
                        raise RuntimeError(f"Course folder notes '{display_name}' rejected: {val_err}")
                    suffix = folder_p.suffix.lower()
                    if suffix not in SUPPORTED_NOTES_EXTS:
                        raise ValueError(f"Unsupported lecture notes format '{suffix}' in course folder item {display_name}.")
                    notes_p = folder_p
                else:
                    remote_id = item.get("id") or item.get("link")
                    if not remote_id:
                        raise FileNotFoundError(f"Course folder notes '{display_name}' has neither local path nor remote ID.")
                    remote_url = f"https://drive.google.com/uc?id={remote_id}" if not str(remote_id).startswith("http") else str(remote_id)
                    try:
                        dl_p, orig_name = download_from_link(
                            url=remote_url,
                            target_dir=drive_notes_dir,
                            expected_type="notes",
                            progress_callback=update_progress
                        )
                    except Exception as dl_err:
                        raise RuntimeError(f"Failed to download course folder notes '{display_name}': {dl_err}")
                    newly_staged_paths.append(dl_p)
                    notes_p = dl_p
                    display_name = sanitize_display_name(orig_name or display_name)

            else:
                raise ValueError(f"Unknown source kind '{kind}' for notes item '{display_name}'.")

            # Slide range handling per notes deck
            s_slide = item.get("start_slide")
            e_slide = item.get("end_slide")
            if not s_slide and not e_slide and item.get("slide_range"):
                raw_rng = str(item["slide_range"]).strip()
                m = re.match(r"(\d+)\s*[-–—to]+\s*(\d+)", raw_rng)
                if m:
                    s_slide, e_slide = int(m.group(1)), int(m.group(2))
                elif raw_rng.isdigit():
                    s_slide, e_slide = 1, int(raw_rng)

            slide_ranges.append((s_slide, e_slide))
            final_notes_paths.append(notes_p)
            notes_names.append(display_name)

        return final_audio_paths, final_notes_paths, audio_names, notes_names, slide_ranges, newly_staged_paths
    except Exception:
        for p in newly_staged_paths:
            try:
                resolved = Path(p).resolve()
                if resolved.exists():
                    resolved.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def background_process(
    job_id: str,
    sources: Optional[list] = None,
    staged_upload_map: Optional[dict] = None,
    audio_paths: Optional[list] = None,
    notes_paths: Optional[list] = None,
    start_slide: Optional[int] = None,
    end_slide: Optional[int] = None,
    slide_ranges: Optional[list] = None,
    api_key: Optional[str] = None,
    is_demo: bool = False,
    model: Optional[str] = None,
    course_hint: Optional[str] = None,
    lecturer_hint: Optional[str] = None,
    study_mode: str = "detailed",
    pdf_options: Optional[dict] = None,
    source_name: str = "Instant Demo",
    notes_source: Optional[str] = None,
    audio_urls: Optional[list] = None,
    notes_urls: Optional[list] = None,
    folder_url: Optional[str] = None,
    session_query: Optional[str] = None,
    folder_selection_mode: Optional[str] = None,
    selected_items: Optional[str] = None,
    save_media_to_drive: bool = False,
):
    if job_id not in cancel_events:
        cancel_events[job_id] = threading.Event()
    if is_job_cancelled(job_id):
        return

    def update_progress(message: str, percent: int):
        if is_job_cancelled(job_id):
            raise JobCancelledException(f"Job {job_id} was cancelled.")
        jobs[job_id]["progress"] = percent
        jobs[job_id]["status_message"] = message

    def check_cancellation():
        if is_job_cancelled(job_id):
            raise JobCancelledException(f"Job {job_id} was cancelled.")

    all_staged_paths: List[Path] = list(staged_upload_map.values()) if staged_upload_map else []
    if audio_paths:
        all_staged_paths.extend([Path(p) for p in audio_paths])
    if notes_paths:
        all_staged_paths.extend([Path(p) for p in notes_paths])

    def cleanup_staged_files():
        for p in all_staged_paths:
            try:
                resolved = Path(p).resolve()
                if resolved.exists() and (UPLOAD_DIR.resolve() in resolved.parents or resolved.parent == UPLOAD_DIR.resolve()):
                    resolved.unlink(missing_ok=True)
            except OSError:
                pass

    try:
        check_cancellation()
        jobs[job_id]["status"] = "processing"
        final_audio_paths = list(audio_paths or [])
        final_notes_paths = list(notes_paths or [])
        audio_names = [p.name for p in final_audio_paths]
        notes_names = [p.name for p in final_notes_paths]
        sources_summary: Optional[str] = None

        # Determine target Google Drive folders based on course hint, folder url, and session query
        effective_course = course_hint or folder_url
        if save_media_to_drive:
            drive_audio_dir = resolve_drive_destination(effective_course, "audio", session_query, UPLOAD_DIR)
            drive_notes_dir = resolve_drive_destination(effective_course, "notes", session_query, UPLOAD_DIR)
        else:
            drive_audio_dir = UPLOAD_DIR
            drive_notes_dir = UPLOAD_DIR

        # --- A. Structured Mixed Sources Mode ---
        if sources is not None:
            if not is_demo:
                update_progress("Resolving lecture sources in user order...", 5)
                resolved_a, resolved_n, a_names, n_names, comp_ranges, newly_staged = resolve_mixed_sources(
                    sources=sources,
                    staged_upload_map=staged_upload_map or {},
                    drive_audio_dir=drive_audio_dir,
                    drive_notes_dir=drive_notes_dir,
                    update_progress=update_progress,
                    check_cancellation=check_cancellation,
                )
                all_staged_paths.extend(newly_staged)
                final_audio_paths = resolved_a
                final_notes_paths = resolved_n
                audio_names = a_names
                notes_names = n_names
                if comp_ranges and any(sr[0] or sr[1] for sr in comp_ranges):
                    slide_ranges = comp_ranges

            audio_items = [s for s in sources if s.get("role") == "audio"]
            notes_items = [s for s in sources if s.get("role") == "notes"]
            sources_summary = format_sources_summary(audio_items, notes_items) if not is_demo else None
            if not is_demo:
                source_name = ", ".join(audio_names) if audio_names else "Lecture Recording"
                notes_source = ", ".join(notes_names) if notes_names else None
            else:
                source_name = "Instant Demo"

        # --- B. Legacy Single-Mode Inputs Fallback ---
        else:
            if selected_items:
                update_progress("Resolving selected course folder materials...", 5)
                try:
                    items_data = json.loads(selected_items)
                except Exception:
                    items_data = {}
                rec_items = items_data.get("records", [])
                note_items = items_data.get("notes", []) if folder_selection_mode != "record_only" else []

                if rec_items:
                    res_recs = download_selected_folder_items(rec_items, drive_audio_dir, "audio", update_progress)
                    for rp, rn in res_recs:
                        final_audio_paths.append(rp)
                        audio_names.append(rn)
                if note_items:
                    res_notes = download_selected_folder_items(note_items, drive_notes_dir, "notes", update_progress)
                    for np, nn in res_notes:
                        final_notes_paths.append(np)
                        notes_names.append(nn)

            elif folder_url:
                if session_query:
                    update_progress(f"Searching course folder for '{session_query}'...", 5)
                    search_res = search_session_in_folder(folder_url, session_query, update_progress)
                    if not search_res.get("records"):
                        raise FileNotFoundError(
                            f"No audio recording found for '{session_query}' in the course folder. "
                            f"{search_res.get('message', '')}"
                        )
                    course_hint = course_hint or search_res.get("course_hint")
                    if not effective_course and course_hint:
                        effective_course = course_hint
                        if save_media_to_drive:
                            drive_audio_dir = resolve_drive_destination(effective_course, "audio", session_query, UPLOAD_DIR)
                            drive_notes_dir = resolve_drive_destination(effective_course, "notes", session_query, UPLOAD_DIR)

                    rec_items = search_res["records"]
                    note_items = search_res["notes"] if folder_selection_mode != "record_only" else []

                    res_recs = download_selected_folder_items(rec_items, drive_audio_dir, "audio", update_progress)
                    for rp, rn in res_recs:
                        final_audio_paths.append(rp)
                        audio_names.append(rn)

                    if note_items:
                        res_notes = download_selected_folder_items(note_items, drive_notes_dir, "notes", update_progress)
                        for np, nn in res_notes:
                            final_notes_paths.append(np)
                            notes_names.append(nn)
                else:
                    update_progress("Connecting to Google Drive folder...", 5)
                    f_audio, f_notes, f_audio_name, f_notes_name = download_from_folder_link(
                        folder_url=folder_url,
                        target_dir=drive_audio_dir,
                        progress_callback=update_progress
                    )
                    final_audio_paths.append(f_audio)
                    audio_names.append(f_audio_name)
                    if f_notes:
                        final_notes_paths.append(f_notes)
                        notes_names.append(f_notes_name)

            if audio_urls:
                drive_label = f" directly into Google Drive ({drive_audio_dir.parent.name})" if is_drive_target(drive_audio_dir) else ""
                update_progress(f"Connecting to Google Drive to download {len(audio_urls)} recording part(s){drive_label}...", 5)
                dl_recs = download_multiple_links(audio_urls, drive_audio_dir, "audio", update_progress)
                for rp, rn in dl_recs:
                    final_audio_paths.append(rp)
                    audio_names.append(rn)

            if notes_urls:
                drive_label = f" directly into Google Drive ({drive_notes_dir.parent.name})" if is_drive_target(drive_notes_dir) else ""
                update_progress(f"Connecting to Google Drive to download {len(notes_urls)} notes deck(s){drive_label}...", 10)
                dl_notes = download_multiple_links(notes_urls, drive_notes_dir, "notes", update_progress)
                for np, nn in dl_notes:
                    final_notes_paths.append(np)
                    notes_names.append(nn)

        # Copy to Drive if requested
        if save_media_to_drive and is_drive_target(drive_audio_dir) and audio_paths:
            for p in audio_paths:
                dest = drive_audio_dir / p.name
                if not dest.exists():
                    try:
                        shutil.copy2(str(p), str(dest))
                    except Exception:
                        pass

        if save_media_to_drive and is_drive_target(drive_notes_dir) and notes_paths:
            for p in notes_paths:
                dest = drive_notes_dir / p.name
                if not dest.exists():
                    try:
                        shutil.copy2(str(p), str(dest))
                    except Exception:
                        pass

        if audio_names:
            source_name = ", ".join(audio_names)
        if notes_names:
            notes_source = ", ".join(notes_names)

        if not is_demo:
            if not final_audio_paths:
                raise FileNotFoundError("Audio file was not found or could not be downloaded.")
            for ap in final_audio_paths:
                if not ap.exists():
                    raise FileNotFoundError(f"Audio file not found: {ap.name}")
                suffix = ap.suffix.lower()
                if suffix not in SUPPORTED_AUDIO_EXTS:
                    raise ValueError(
                        f"Unsupported audio format '{suffix or 'unknown'}' in {ap.name}. "
                        f"Use: {', '.join(sorted(SUPPORTED_AUDIO_EXTS))}."
                    )
            for np in final_notes_paths:
                if np.exists():
                    notes_suffix = np.suffix.lower()
                    if notes_suffix not in SUPPORTED_NOTES_EXTS:
                        raise ValueError(
                            f"Unsupported lecture notes format '{notes_suffix or 'unknown'}' in {np.name}. "
                            f"Use: {', '.join(sorted(SUPPORTED_NOTES_EXTS))}."
                        )

        check_cancellation()
        result = process_lecture(
            audio_path=final_audio_paths if final_audio_paths else None,
            notes_path=final_notes_paths if final_notes_paths else None,
            start_slide=start_slide,
            end_slide=end_slide,
            slide_ranges=slide_ranges,
            api_key=api_key,
            model=model,
            course_hint=course_hint,
            lecturer_hint=lecturer_hint,
            study_mode=study_mode,
            pdf_options=pdf_options,
            use_sample_demo=is_demo,
            progress_callback=update_progress
        )
        check_cancellation()

        # Save PDF to Google Drive if applicable
        drive_pdf = save_summary_to_drive(Path(result["pdf_path"]), effective_course)
        if drive_pdf:
            result["drive_pdf_path"] = str(drive_pdf)
            result["drive_pdf_filename"] = drive_pdf.name
            result["drive_folder_path"] = str(drive_pdf.parent)

        check_cancellation()

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = result
        try:
            save_history_entry(
                result=result,
                source_name=source_name,
                study_mode=study_mode,
                notes_source=notes_source,
                sources_summary=sources_summary
            )
        except OSError:
            pass
        jobs[job_id]["progress"] = 100
        if drive_pdf:
            jobs[job_id]["status_message"] = f"Complete! Saved directly to Google Drive: {drive_pdf.name}"
        else:
            jobs[job_id]["status_message"] = "Processing complete! Your study guide is ready."
    except JobCancelledException:
        cleanup_staged_files()
        jobs[job_id]["status"] = "cancelled"
        jobs[job_id]["cancelled"] = True
        jobs[job_id]["error"] = "Generation was cancelled by the user."
        jobs[job_id]["status_message"] = "Job cancelled by user."
    except Exception as e:
        cleanup_staged_files()
        if is_job_cancelled(job_id):
            jobs[job_id]["status"] = "cancelled"
            jobs[job_id]["cancelled"] = True
            jobs[job_id]["error"] = "Generation was cancelled by the user."
            jobs[job_id]["status_message"] = "Job cancelled by user."
            return
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["status_message"] = f"Error: {e}"


@app.get("/api/detected_courses")
async def get_detected_courses():
    r"""Returns detected courses found locally in G:\My Drive\fall 2026 or PC storage."""
    try:
        from link_downloader import get_drive_fall_root
        courses = detect_local_fall_courses()
        root = get_drive_fall_root()
        sem_name = root.name if root else None
        return {"success": True, "courses": courses, "semester_name": sem_name}
    except Exception as e:
        return {"success": False, "courses": [], "semester_name": None, "error": str(e)}


@app.post("/api/search_course_folder")
async def search_course_folder_endpoint(
    folder_url: str = Form(...),
    query: str = Form(...)
):
    """
    Scans a course folder (local or Google Drive link) and searches for lecture/section materials.
    """
    try:
        res = search_session_in_folder(folder_url, query)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/config")
async def get_config():
    from config import DEFAULT_MODEL
    key = get_gemini_api_key()
    has_key = bool(key and len(key) > 5)
    return {"has_key": has_key, "model": DEFAULT_MODEL}


@app.post("/api/set_key")
async def set_key(key: str = Form(...)):
    if key.strip():
        set_gemini_api_key(key.strip())
        return {"success": True, "message": "API key saved successfully"}
    return {"success": False, "message": "Key cannot be empty"}


@app.post("/api/process_audio")
async def process_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    audio: Optional[List[UploadFile]] = File(None),
    notes: Optional[List[UploadFile]] = File(None),
    sources: Optional[str] = Form(None),
    audio_url: Optional[str] = Form(None),
    audio_urls: Optional[str] = Form(None),
    notes_url: Optional[str] = Form(None),
    notes_urls: Optional[str] = Form(None),
    folder_url: Optional[str] = Form(None),
    session_query: Optional[str] = Form(None),
    folder_selection_mode: Optional[str] = Form(None),
    selected_items: Optional[str] = Form(None),
    start_slide: Optional[int] = Form(None),
    end_slide: Optional[int] = Form(None),
    api_key: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    course_hint: Optional[str] = Form(None),
    lecturer_hint: Optional[str] = None,
    study_mode: str = Form("detailed"),
    include_diagrams: bool = Form(True),
    include_exam_questions: bool = Form(True),
    include_transcript: bool = Form(True),
    demo_mode: bool = Form(False),
    save_media_to_drive: bool = Form(False)
):
    if study_mode not in {"detailed", "revision", "exam"}:
        raise HTTPException(status_code=400, detail="Study mode must be detailed, revision, or exam.")

    job_id = str(uuid.uuid4())

    def register_job() -> None:
        cancel_events[job_id] = threading.Event()
        jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 5,
            "status_message": "Initializing task...",
            "result": None,
            "error": None,
            "cancelled": False
        }

    pdf_options = {
        "include_diagrams": include_diagrams,
        "include_exam_questions": include_exam_questions,
        "include_transcript": include_transcript,
    }

    form = await request.form()
    sources_str = sources or form.get("sources")

    # =========================================================================
    # PATH A: Structured Mixed Sources Intake
    # =========================================================================
    if sources_str and str(sources_str).strip():
        try:
            sources_list = json.loads(sources_str)
            if not isinstance(sources_list, list):
                raise ValueError("Sources must be a JSON array.")
        except Exception as json_err:
            raise HTTPException(status_code=400, detail=f"Invalid sources payload: {json_err}")

        # If demo mode
        if demo_mode:
            register_job()
            background_tasks.add_task(
                background_process,
                job_id=job_id,
                sources=sources_list,
                staged_upload_map={},
                api_key=None,
                is_demo=True,
                model=model,
                course_hint=course_hint,
                lecturer_hint=lecturer_hint,
                study_mode=study_mode,
                pdf_options=pdf_options,
                source_name="Instant Demo",
                save_media_to_drive=save_media_to_drive
            )
            return {"success": True, "job_id": job_id}

        audio_items = [s for s in sources_list if s.get("role") == "audio"]
        notes_items = [s for s in sources_list if s.get("role") == "notes"]

        if not audio_items:
            raise HTTPException(
                status_code=400,
                detail="No lecture recording provided. Please add at least one audio recording from your computer, a link, or a course folder."
            )

        # Validate extensions on all items upfront
        for item in sources_list:
            d_name = item.get("display_name") or item.get("link") or item.get("local_path") or ""
            # Extract suffix
            try:
                parsed_path = urllib.parse.urlparse(d_name).path
                suffix = Path(parsed_path).suffix.lower()
            except Exception:
                suffix = Path(d_name).suffix.lower()

            if item.get("role") == "audio":
                if suffix and suffix not in SUPPORTED_AUDIO_EXTS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported audio format '{suffix}' in {item.get('display_name', d_name)}. Use: {', '.join(sorted(SUPPORTED_AUDIO_EXTS))}."
                    )
            elif item.get("role") == "notes":
                if suffix and suffix not in SUPPORTED_NOTES_EXTS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported lecture notes format '{suffix}' in {item.get('display_name', d_name)}. Use: {', '.join(sorted(SUPPORTED_NOTES_EXTS))}."
                    )

        # Validate course folder paths containment upfront
        for item in sources_list:
            if item.get("kind") == "folder" and item.get("local_path"):
                try:
                    validate_course_folder_path(item["local_path"])
                except (ValueError, FileNotFoundError) as ve:
                    raise HTTPException(status_code=400, detail=str(ve))

        # Validate API key
        resolved_key = api_key or get_gemini_api_key()
        if not resolved_key:
            raise HTTPException(
                status_code=400,
                detail="Gemini API Key is required to process real audio files. Please click 'Configure Key' at the top right to add your key, or click 'Instant Demo' to test without a key."
            )

        # Stage uploaded files with error rollback
        staged_upload_map: Dict[str, Path] = {}
        upload_items = [s for s in sources_list if s.get("kind") == "upload"]
        try:
            for u_item in upload_items:
                u_id = str(u_item.get("id", ""))
                # Match uploaded file
                u_file = (
                    form.get(f"file_{u_id}")
                    or form.get(f"upload_{u_id}")
                    or form.get(u_id)
                )
                if not u_file or not hasattr(u_file, "filename"):
                    # Check for matching filename in form
                    for k, v in form.multi_items():
                        if hasattr(v, "filename") and v.filename and v.filename == u_item.get("display_name"):
                            u_file = v
                            break
                if not u_file or not hasattr(u_file, "filename"):
                    # Check in audio / notes lists
                    matching_role_files = [v for k, v in form.multi_items() if k == u_item.get("role") and hasattr(v, "filename")]
                    if len(matching_role_files) == 1:
                        u_file = matching_role_files[0]
                    elif len(matching_role_files) > 1 and "order" in u_item:
                        order_idx = u_item["order"]
                        if order_idx < len(matching_role_files):
                            u_file = matching_role_files[order_idx]

                if not u_file or not hasattr(u_file, "filename"):
                    raise HTTPException(status_code=400, detail=f"Uploaded file missing for '{u_item.get('display_name', u_id)}'.")

                orig_name = Path(u_file.filename).name
                suffix = Path(orig_name).suffix.lower()
                if u_item.get("role") == "audio" and suffix not in SUPPORTED_AUDIO_EXTS:
                    raise HTTPException(status_code=400, detail=f"Unsupported audio format '{suffix}' in {orig_name}. Use: {', '.join(sorted(SUPPORTED_AUDIO_EXTS))}.")
                if u_item.get("role") == "notes" and suffix not in SUPPORTED_NOTES_EXTS:
                    raise HTTPException(status_code=400, detail=f"Unsupported lecture notes format '{suffix}' in {orig_name}. Use: {', '.join(sorted(SUPPORTED_NOTES_EXTS))}.")

                clean_upload_name = f"{uuid.uuid4().hex[:8]}_{orig_name}"
                save_p = UPLOAD_DIR / clean_upload_name
                staged_upload_map[u_id] = save_p

                with open(save_p, "wb") as f_out:
                    written = 0
                    while chunk := await u_file.read(1024 * 1024):
                        written += len(chunk)
                        if written > MAX_UPLOAD_BYTES:
                            raise HTTPException(status_code=413, detail=f"File '{orig_name}' exceeds 2 GB local limit.")
                        f_out.write(chunk)
        except Exception:
            for sp in staged_upload_map.values():
                try:
                    sp.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

        register_job()
        background_tasks.add_task(
            background_process,
            job_id=job_id,
            sources=sources_list,
            staged_upload_map=staged_upload_map,
            api_key=resolved_key,
            is_demo=False,
            model=model,
            course_hint=course_hint,
            lecturer_hint=lecturer_hint,
            study_mode=study_mode,
            pdf_options=pdf_options,
            source_name="Lecture Recording",
            save_media_to_drive=save_media_to_drive
        )
        return {"success": True, "job_id": job_id}

    # =========================================================================
    # PATH B: Legacy Single-Mode Inputs (Backward Compatibility)
    # =========================================================================
    if demo_mode:
        register_job()
        background_tasks.add_task(
            background_process,
            job_id=job_id,
            audio_paths=None,
            notes_paths=None,
            start_slide=start_slide,
            end_slide=end_slide,
            api_key=None,
            is_demo=True,
            model=model,
            course_hint=course_hint,
            lecturer_hint=lecturer_hint,
            study_mode=study_mode,
            pdf_options=pdf_options,
            source_name="Instant Demo",
            notes_source=f"Slides {start_slide or 1}–{end_slide or 25}" if (start_slide or end_slide) else None
        )
        return {"success": True, "job_id": job_id}

    # Clean URL inputs & parse multi-url lists
    parsed_audio_urls = []
    if audio_urls and audio_urls.strip():
        try:
            u_list = json.loads(audio_urls)
            if isinstance(u_list, list):
                parsed_audio_urls.extend([str(x).strip() for x in u_list if str(x).strip()])
        except json.JSONDecodeError:
            parsed_audio_urls.extend([x.strip() for x in audio_urls.splitlines() if x.strip()])
    if audio_url and audio_url.strip():
        clean_u = audio_url.strip()
        if clean_u not in parsed_audio_urls:
            parsed_audio_urls.append(clean_u)

    parsed_notes_urls = []
    if notes_urls and notes_urls.strip():
        try:
            u_list = json.loads(notes_urls)
            if isinstance(u_list, list):
                parsed_notes_urls.extend([str(x).strip() for x in u_list if str(x).strip()])
        except json.JSONDecodeError:
            parsed_notes_urls.extend([x.strip() for x in notes_urls.splitlines() if x.strip()])
    if notes_url and notes_url.strip():
        clean_u = notes_url.strip()
        if clean_u not in parsed_notes_urls:
            parsed_notes_urls.append(clean_u)

    clean_folder_url = folder_url.strip() if folder_url and folder_url.strip() else None
    clean_session_query = session_query.strip() if session_query and session_query.strip() else None

    audio_save_paths = []
    original_names = []
    notes_save_paths = []
    notes_original_names = []

    def discard_saved_uploads() -> None:
        for saved in [*audio_save_paths, *notes_save_paths]:
            try:
                saved.unlink(missing_ok=True)
            except OSError:
                pass

    # Validate all file extensions first before saving any files to disk
    raw_audio_list = audio if isinstance(audio, list) else ([audio] if audio else [])
    valid_audio_files = [a for a in raw_audio_list if a and a.filename and a.filename.strip()]
    for a_file in valid_audio_files:
        orig_name = Path(a_file.filename).name
        suffix = Path(orig_name).suffix.lower()
        if suffix not in SUPPORTED_AUDIO_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format '{suffix or 'unknown'}' in {orig_name}. Use: {', '.join(sorted(SUPPORTED_AUDIO_EXTS))}."
            )

    raw_notes_list = notes if isinstance(notes, list) else ([notes] if notes else [])
    valid_notes_files = [n for n in raw_notes_list if n and n.filename and n.filename.strip()]
    for n_file in valid_notes_files:
        notes_orig_name = Path(n_file.filename).name
        notes_suffix = Path(notes_orig_name).suffix.lower()
        if notes_suffix not in SUPPORTED_NOTES_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported lecture notes format '{notes_suffix or 'unknown'}' in {notes_orig_name}. Use: {', '.join(sorted(SUPPORTED_NOTES_EXTS))}."
            )

    # Save audio and lecture notes files to disk with error rollback
    try:
        for a_file in valid_audio_files:
            orig_name = Path(a_file.filename).name
            clean_audio_name = f"{str(uuid.uuid4())[:8]}_{orig_name}"
            save_p = UPLOAD_DIR / clean_audio_name
            audio_save_paths.append(save_p)
            original_names.append(orig_name)
            with open(save_p, "wb") as f_out:
                written = 0
                while chunk := await a_file.read(1024 * 1024):
                    written += len(chunk)
                    if written > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail=f"Audio file '{orig_name}' exceeds 2 GB local limit.")
                    f_out.write(chunk)

        for n_file in valid_notes_files:
            notes_orig_name = Path(n_file.filename).name
            clean_notes_name = f"{str(uuid.uuid4())[:8]}_{notes_orig_name}"
            notes_save_p = UPLOAD_DIR / clean_notes_name
            notes_save_paths.append(notes_save_p)
            notes_original_names.append(notes_orig_name)
            with open(notes_save_p, "wb") as fn:
                written_notes = 0
                while chunk := await n_file.read(1024 * 1024):
                    written_notes += len(chunk)
                    if written_notes > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail=f"Lecture notes file '{notes_orig_name}' exceeds local limit.")
                    fn.write(chunk)
    except Exception:
        discard_saved_uploads()
        raise

    # Note: Previously, folder mode locked and discarded manual uploads here.
    # In the mixed-source architecture, manual uploads are preserved and combined!

    # Must provide either an uploaded audio file, audio links, a folder search item, or a folder link
    has_audio_input = bool(audio_save_paths or parsed_audio_urls or clean_folder_url or selected_items)
    if not has_audio_input:
        discard_saved_uploads()
        raise HTTPException(
            status_code=400,
            detail="No lecture recording provided. Please upload an audio file, paste Google Drive links, or search a course folder."
        )

    # Validate API key before processing
    resolved_key = api_key or get_gemini_api_key()
    if not resolved_key:
        discard_saved_uploads()
        raise HTTPException(
            status_code=400, 
            detail="Gemini API Key is required to process real audio files. Please click 'Configure Key' at the top right to add your key, or click 'Instant Demo' to test without a key."
        )

    source_label = ", ".join(original_names) if original_names else "Lecture Recording"
    notes_label = ", ".join(notes_original_names) if notes_original_names else None

    register_job()
    background_tasks.add_task(
        background_process,
        job_id=job_id,
        audio_paths=audio_save_paths if audio_save_paths else None,
        notes_paths=notes_save_paths if notes_save_paths else None,
        start_slide=start_slide,
        end_slide=end_slide,
        api_key=resolved_key,
        is_demo=False,
        model=model,
        course_hint=course_hint,
        lecturer_hint=lecturer_hint,
        study_mode=study_mode,
        pdf_options=pdf_options,
        source_name=source_label,
        notes_source=notes_label,
        audio_urls=parsed_audio_urls if parsed_audio_urls else None,
        notes_urls=parsed_notes_urls if parsed_notes_urls else None,
        folder_url=clean_folder_url,
        session_query=clean_session_query,
        folder_selection_mode=folder_selection_mode,
        selected_items=selected_items,
        save_media_to_drive=save_media_to_drive
    )
    return {"success": True, "job_id": job_id}


@app.post("/api/cancel/{job_id}")
async def cancel_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    jobs[job_id]["status"] = "cancelled"
    jobs[job_id]["cancelled"] = True
    jobs[job_id]["error"] = "Generation was cancelled by the user."
    jobs[job_id]["status_message"] = "Job cancelled by user."
    if job_id not in cancel_events:
        cancel_events[job_id] = threading.Event()
    cancel_events[job_id].set()
    return {"success": True, "message": "Job cancelled successfully", "job_id": job_id}


@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/api/download/{filename}")
async def download_pdf(filename: str):
    file_path = (OUTPUT_DIR / Path(filename).name).resolve()
    if OUTPUT_DIR.resolve() not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        str(file_path),
        media_type="application/pdf",
        filename=filename
    )


@app.get("/api/history")
async def get_history():
    """Recent locally generated guides; full content remains available per entry."""
    return load_history()


@app.get("/api/history/{history_id}")
async def get_history_entry(history_id: str):
    for item in load_history():
        if item.get("id") == history_id:
            return item
    raise HTTPException(status_code=404, detail="History entry not found")


@app.delete("/api/history/{history_id}")
@app.post("/api/history/{history_id}/delete")
async def delete_history_entry(history_id: str):
    """Permanently deletes a study guide from local history and removes its generated PDF from disk."""
    history = load_history()
    target_entry = None
    target_idx = -1
    for i, item in enumerate(history):
        if item.get("id") == history_id:
            target_entry = item
            target_idx = i
            break

    if target_idx == -1:
        raise HTTPException(status_code=404, detail="History entry not found")

    # Cleanly remove the generated PDF from local disk if it exists
    pdf_filename = target_entry.get("result", {}).get("pdf_filename")
    deleted_file = False
    if pdf_filename:
        pdf_path = (OUTPUT_DIR / Path(pdf_filename).name).resolve()
        if pdf_path.is_file() and OUTPUT_DIR.resolve() in pdf_path.parents:
            try:
                pdf_path.unlink(missing_ok=True)
                deleted_file = True
            except OSError:
                pass

    history.pop(target_idx)
    try:
        HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to update history file: {e}")

    return {
        "success": True,
        "message": "Study guide deleted successfully from records.",
        "id": history_id,
        "pdf_deleted": deleted_file
    }


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open(Path(__file__).parent / "templates" / "index.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    print("[*] Starting LectureAI Web Dashboard at http://127.0.0.1:8000 ...")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
