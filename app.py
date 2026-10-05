import os
import uuid
import threading
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Union, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from config import UPLOAD_DIR, OUTPUT_DIR, ASSETS_DIR, SUPPORTED_AUDIO_EXTS, SUPPORTED_NOTES_EXTS, get_gemini_api_key, set_gemini_api_key
from pipeline import process_lecture
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
)

app = FastAPI(title="LectureAI Study Suite", version="1.0.0")

# The dashboard and API are served from the same local origin. Do not enable
# cross-origin access; require browser mutations to come from that dashboard.
ALLOWED_BROWSER_ORIGINS = {
    "http://127.0.0.1:8000",
    "http://localhost:8000",
}


@app.middleware("http")
async def protect_local_mutations(request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin not in ALLOWED_BROWSER_ORIGINS:
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

# In-memory job tracker
jobs = {}
HISTORY_FILE = Path(__file__).parent / "lecture_history.json"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB, suitable for long personal lectures.


def load_history():
    """Return local history without failing the app when an older file is malformed."""
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []
    except (OSError, json.JSONDecodeError):
        return []


def save_history_entry(result: dict, source_name: str, study_mode: str, notes_source: Optional[str] = None) -> None:
    history = load_history()
    history.insert(0, {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_name": source_name,
        "notes_source": notes_source,
        "notes_reference": result.get("notes_reference"),
        "study_mode": study_mode,
        "result": result,
    })
    HISTORY_FILE.write_text(json.dumps(history[:50], ensure_ascii=False, indent=2), encoding="utf-8")


def background_process(
    job_id: str,
    audio_paths: Optional[list] = None,
    notes_paths: Optional[list] = None,
    start_slide: Optional[int] = None,
    end_slide: Optional[int] = None,
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
    def update_progress(message: str, percent: int):
        jobs[job_id]["progress"] = percent
        jobs[job_id]["status_message"] = message

    try:
        jobs[job_id]["status"] = "processing"
        final_audio_paths = list(audio_paths or [])
        final_notes_paths = list(notes_paths or [])
        audio_names = [p.name for p in final_audio_paths]
        notes_names = [p.name for p in final_notes_paths]

        # Determine target Google Drive folders based on course hint, folder url, and session query
        effective_course = course_hint or folder_url
        if save_media_to_drive:
            drive_audio_dir = resolve_drive_destination(effective_course, "audio", session_query, UPLOAD_DIR)
            drive_notes_dir = resolve_drive_destination(effective_course, "notes", session_query, UPLOAD_DIR)
        else:
            # Keep uploaded/downloaded media in local scratch UPLOAD_DIR to prevent redundant cloud re-sync
            drive_audio_dir = UPLOAD_DIR
            drive_notes_dir = UPLOAD_DIR

        # 1. Resolve folder items if selected from folder search or provided as folder URL
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

        # 2. Download from Google Drive / Cloud links if provided directly into their respective Drive folders
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

        # 3. If files were uploaded through web browser, optionally copy to Drive folder if explicitly requested
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

        result = process_lecture(
            audio_path=final_audio_paths if final_audio_paths else None,
            notes_path=final_notes_paths if final_notes_paths else None,
            start_slide=start_slide,
            end_slide=end_slide,
            api_key=api_key,
            model=model,
            course_hint=course_hint,
            lecturer_hint=lecturer_hint,
            study_mode=study_mode,
            pdf_options=pdf_options,
            use_sample_demo=is_demo,
            progress_callback=update_progress
        )

        # 4. Save generated PDF study guide directly to Google Drive summaries folder
        drive_pdf = save_summary_to_drive(Path(result["pdf_path"]), effective_course)
        if drive_pdf:
            result["drive_pdf_path"] = str(drive_pdf)
            result["drive_pdf_filename"] = drive_pdf.name
            result["drive_folder_path"] = str(drive_pdf.parent)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = result
        try:
            save_history_entry(result, source_name, study_mode, notes_source=notes_source)
        except OSError:
            pass
        jobs[job_id]["progress"] = 100
        if drive_pdf:
            jobs[job_id]["status_message"] = f"Complete! Saved directly to Google Drive: {drive_pdf.name}"
        else:
            jobs[job_id]["status_message"] = "Processing complete! Your study guide is ready."
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["status_message"] = f"Error: {e}"


@app.get("/api/detected_courses")
async def get_detected_courses():
    r"""Returns detected courses found locally in G:\My Drive\fall 2026 or PC storage."""
    try:
        courses = detect_local_fall_courses()
        return {"success": True, "courses": courses}
    except Exception as e:
        return {"success": False, "courses": [], "error": str(e)}


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
    masked = f"{key[:4]}...{key[-4:]}" if has_key else ""
    return {"has_key": has_key, "masked_key": masked, "model": DEFAULT_MODEL}


@app.post("/api/set_key")
async def set_key(key: str = Form(...)):
    if key.strip():
        set_gemini_api_key(key.strip())
        return {"success": True, "message": "API key saved successfully"}
    return {"success": False, "message": "Key cannot be empty"}


@app.post("/api/process_audio")
async def process_audio(
    background_tasks: BackgroundTasks,
    audio: Optional[List[UploadFile]] = File(None),
    notes: Optional[List[UploadFile]] = File(None),
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
    lecturer_hint: Optional[str] = Form(None),
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
        # Only register once the request is fully validated so rejected requests leave no orphan jobs.
        jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 5,
            "status_message": "Initializing task...",
            "result": None,
            "error": None
        }

    pdf_options = {
        "include_diagrams": include_diagrams,
        "include_exam_questions": include_exam_questions,
        "include_transcript": include_transcript,
    }

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
        return {"job_id": job_id}

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

    # Save audio files if uploaded directly (supports single or multi-part audio)
    audio_save_paths = []
    original_names = []
    raw_audio_list = audio if isinstance(audio, list) else ([audio] if audio else [])
    for a_file in raw_audio_list:
        if not a_file or not a_file.filename or not a_file.filename.strip():
            continue
        orig_name = Path(a_file.filename).name
        suffix = Path(orig_name).suffix.lower()
        if suffix not in SUPPORTED_AUDIO_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format '{suffix or 'unknown'}' in {orig_name}. Use: {', '.join(sorted(SUPPORTED_AUDIO_EXTS))}."
            )
        clean_audio_name = f"{str(uuid.uuid4())[:8]}_{orig_name}"
        save_p = UPLOAD_DIR / clean_audio_name
        with open(save_p, "wb") as f_out:
            written = 0
            while chunk := await a_file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    f_out.close()
                    save_p.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail=f"Audio file '{orig_name}' exceeds 2 GB local limit.")
                f_out.write(chunk)
        audio_save_paths.append(save_p)
        original_names.append(orig_name)

    # Save optional lecture notes files if uploaded directly (supports multiple decks)
    notes_save_paths = []
    notes_original_names = []
    raw_notes_list = notes if isinstance(notes, list) else ([notes] if notes else [])
    for n_file in raw_notes_list:
        if not n_file or not n_file.filename or not n_file.filename.strip():
            continue
        notes_orig_name = Path(n_file.filename).name
        notes_suffix = Path(notes_orig_name).suffix.lower()
        if notes_suffix not in SUPPORTED_NOTES_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported lecture notes format '{notes_suffix or 'unknown'}' in {notes_orig_name}. Use: {', '.join(sorted(SUPPORTED_NOTES_EXTS))}."
            )
        clean_notes_name = f"{str(uuid.uuid4())[:8]}_{notes_orig_name}"
        notes_save_p = UPLOAD_DIR / clean_notes_name
        with open(notes_save_p, "wb") as fn:
            written_notes = 0
            while chunk := await n_file.read(1024 * 1024):
                written_notes += len(chunk)
                if written_notes > MAX_UPLOAD_BYTES:
                    fn.close()
                    notes_save_p.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail=f"Lecture notes file '{notes_orig_name}' exceeds local limit.")
                fn.write(chunk)
        notes_save_paths.append(notes_save_p)
        notes_original_names.append(notes_orig_name)

    def discard_saved_uploads() -> None:
        for saved in [*audio_save_paths, *notes_save_paths]:
            try:
                saved.unlink(missing_ok=True)
            except OSError:
                pass

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
    return {"job_id": job_id}


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
