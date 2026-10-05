import os
import re
import uuid
import shutil
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, Callable, List, Dict, Any
import requests
import gdown
from config import SUPPORTED_AUDIO_EXTS, SUPPORTED_NOTES_EXTS, UPLOAD_DIR

GDRIVE_FILE_PATTERNS = [
    r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
    r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
    r"drive\.google\.com/uc\?id=([a-zA-Z0-9_-]+)",
    r"drive\.google\.com/uc\?export=download&id=([a-zA-Z0-9_-]+)",
]

GDRIVE_FOLDER_PATTERNS = [
    r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)",
    r"drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)",
    r"drive\.google\.com/folderview\?id=([a-zA-Z0-9_-]+)",
]

# Optional override: set LECTUREAI_COURSES_DIR in .env to point at your own semester/courses folder.
_CUSTOM_COURSES_DIR = os.environ.get("LECTUREAI_COURSES_DIR", "").strip()

FALL_DRIVE_CANDIDATE_ROOTS = ([Path(_CUSTOM_COURSES_DIR)] if _CUSTOM_COURSES_DIR else []) + [
    Path(r"G:\My Drive\fall 2026"),
    Path(r"G:\My Drive\Fall 2026"),
    Path.home() / "Google Drive" / "fall 2026",
    Path.home() / "Google Drive" / "Fall 2026",
    Path.home() / "OneDrive" / "fall 2026",
]


def get_drive_fall_root() -> Optional[Path]:
    """Returns the detected fall 2026 directory in Google Drive or local storage."""
    for root in FALL_DRIVE_CANDIDATE_ROOTS:
        if root.exists() and root.is_dir():
            return root
    return None


def is_drive_target(target_dir: Optional[Path]) -> bool:
    """Returns True if target_dir is located inside Google Drive or the local fall 2026 directory."""
    if not target_dir:
        return False
    root = get_drive_fall_root()
    try:
        p = Path(target_dir).resolve()
        if root and (root.resolve() in p.parents or root.resolve() == p):
            return True
        p_str = str(p).lower()
        return "my drive" in p_str or "google drive" in p_str
    except Exception:
        return False


def resolve_drive_destination(
    course_name_or_folder: Optional[str] = None,
    expected_type: str = "audio",  # 'audio', 'notes', or 'summary'
    session_query: Optional[str] = None,
    fallback_dir: Optional[Path] = None,
    create_if_missing: bool = True
) -> Path:
    r"""
    Resolves the exact target folder inside Google Drive (e.g. G:\My Drive\fall 2026\<Course>\...).
    - Audio recordings (lecture): <Course>\record (<Course>)\lectures\
    - Audio recordings (section): <Course>\record (<Course>)\sections\
    - Lecture slides / notes: <Course>\lectures\
    - Sheets / assignments: <Course>\sheets\
    - Study Guide summaries: <Course>\lectures\summaries\
    If no course or Drive folder is available, falls back to fallback_dir or UPLOAD_DIR.
    """
    default_dir = Path(fallback_dir or UPLOAD_DIR)
    root = get_drive_fall_root()
    if not root:
        return default_dir

    course_dir: Optional[Path] = None
    raw_candidate = str(course_name_or_folder or "").strip()
    # Remote links (e.g. a shared Drive folder URL) are not course names; never turn them into folders.
    if raw_candidate.lower().startswith(("http://", "https://")) or "drive.google.com" in raw_candidate.lower():
        course_name_or_folder = None
    if course_name_or_folder:
        raw_target = str(course_name_or_folder).strip()
        p = Path(raw_target)
        if p.exists() and p.is_dir():
            course_dir = p
        else:
            clean = raw_target.lower()
            clean_alnum = re.sub(r"[\s_-]+", "", clean)
            for sub in root.iterdir():
                if sub.is_dir() and not sub.name.startswith("."):
                    sub_clean = sub.name.lower()
                    sub_alnum = re.sub(r"[\s_-]+", "", sub_clean)
                    if sub_clean == clean or sub_alnum == clean_alnum:
                        course_dir = sub
                        break
                    if clean in sub_clean or sub_clean in clean:
                        course_dir = sub
                        break
            if not course_dir:
                acronyms = {
                    "ai": "Artificial Intelligence And Expert Systems",
                    "pe": "Power Electronics",
                    "ev": "Electronic Vision",
                    "bio": "Bio Informatics",
                    "physio": "Physiotherapy Equipment",
                    "feasibility": "Feasibility Study"
                }
                if clean in acronyms:
                    cand = root / acronyms[clean]
                    if cand.exists():
                        course_dir = cand

            # If still not found and a course name was entered, create a new course folder in fall 2026
            if not course_dir and create_if_missing and len(raw_target) > 1:
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', raw_target).strip()
                course_dir = root / safe_name
                course_dir.mkdir(parents=True, exist_ok=True)

    if not course_dir or not course_dir.exists():
        return default_dir

    sq = (session_query or "").lower()
    is_section = "sec" in sq
    is_sheet = "sheet" in sq

    if expected_type == "audio":
        rec_dir = course_dir / f"record ({course_dir.name})"
        if not rec_dir.exists():
            for s in course_dir.iterdir():
                if s.is_dir() and s.name.lower().startswith("record"):
                    rec_dir = s
                    break
        if not rec_dir.exists() and create_if_missing:
            rec_dir.mkdir(parents=True, exist_ok=True)

        sub_folder = "sections" if is_section else "lectures"
        target = rec_dir / sub_folder

    elif expected_type == "notes":
        sub_folder = "sheets" if is_sheet else "lectures"
        target = course_dir / sub_folder

    elif expected_type == "summary":
        target = course_dir / "lectures" / "summaries"

    else:
        target = course_dir

    if create_if_missing:
        target.mkdir(parents=True, exist_ok=True)

    return target


def save_summary_to_drive(pdf_path: Path, course_name_or_folder: Optional[str] = None) -> Optional[Path]:
    """
    Saves a copy of the generated PDF study guide directly to the course's summaries folder in Google Drive.
    """
    if not pdf_path or not Path(pdf_path).exists():
        return None
    try:
        drive_target = resolve_drive_destination(course_name_or_folder, expected_type="summary", create_if_missing=True)
        if is_drive_target(drive_target):
            dest_pdf = drive_target / Path(pdf_path).name
            shutil.copy2(str(pdf_path), str(dest_pdf))
            return dest_pdf
    except Exception as e:
        print(f"[-] Could not copy summary PDF to Drive: {e}")
    return None


def is_google_drive_folder(url: str) -> bool:
    """Return True if url matches a Google Drive folder pattern."""
    if not url:
        return False
    return any(re.search(p, url) for p in GDRIVE_FOLDER_PATTERNS)


def is_google_drive_file(url: str) -> bool:
    """Return True if url matches a Google Drive single file pattern."""
    if not url:
        return False
    return any(re.search(p, url) for p in GDRIVE_FILE_PATTERNS)


def extract_gdrive_id(url: str) -> Optional[str]:
    """Extract file or folder ID from Google Drive URL."""
    for p in GDRIVE_FILE_PATTERNS + GDRIVE_FOLDER_PATTERNS:
        match = re.search(p, url)
        if match:
            return match.group(1)
    return None


def detect_local_fall_courses() -> List[Dict[str, str]]:
    r"""
    Detects course folders located in the local Google Drive or laptop storage (e.g. G:\My Drive\fall 2026).
    Returns list of {'name': course_name, 'path': course_path}.
    """
    root = get_drive_fall_root()
    detected = []
    if root and root.exists() and root.is_dir():
        for sub in sorted(root.iterdir()):
            if sub.is_dir() and not sub.name.startswith("."):
                notes_count = 0
                record_count = 0
                try:
                    for f in sub.rglob("*"):
                        if f.is_file():
                            ext = f.suffix.lower()
                            if ext in SUPPORTED_NOTES_EXTS:
                                notes_count += 1
                            elif ext in SUPPORTED_AUDIO_EXTS:
                                record_count += 1
                except Exception:
                    pass
                detected.append({
                    "name": sub.name,
                    "path": str(sub.resolve()),
                    "lecture_count": notes_count,
                    "record_count": record_count
                })
    return detected


def download_from_link(
    url: str,
    target_dir: Path,
    expected_type: str = "audio",  # 'audio' or 'notes'
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Tuple[Path, str]:
    """
    Downloads a single file from a Google Drive link or direct HTTP/HTTPS link.
    If target_dir is inside Google Drive, preserves clean original filename without random prefixes.
    Returns (downloaded_file_path, original_or_inferred_filename).
    """
    callback = progress_callback or (lambda msg, pct: None)
    url = url.strip()
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    is_drive = is_drive_target(target_dir)

    if not url.startswith("http://") and not url.startswith("https://"):
        raise ValueError(f"Invalid URL: '{url}'. Link must begin with http:// or https://")

    # 1. Google Drive single file download via gdown
    if is_google_drive_file(url) or "drive.google.com" in url:
        file_id = extract_gdrive_id(url)
        clean_prefix = str(uuid.uuid4())[:8]
        temp_subfolder = target_dir / f"download_{clean_prefix}"
        temp_subfolder.mkdir(parents=True, exist_ok=True)

        drive_dest_label = f" directly into Drive ({target_dir.name})" if is_drive else ""
        callback(f"Connecting to Google Drive to download {expected_type}{drive_dest_label}...", 7)

        try:
            download_url = f"https://drive.google.com/uc?id={file_id}" if file_id else url
            downloaded = gdown.download(
                url=download_url,
                output=str(temp_subfolder) + os.sep,
                quiet=True
            )
        except Exception as e:
            err_str = str(e)
            if "Cannot retrieve the public link" in err_str or "permission" in err_str.lower():
                raise PermissionError(
                    "Google Drive access denied. Please ensure the file sharing setting is set to "
                    "'Anyone with the link' (Viewer) in Google Drive, then try again."
                )
            raise RuntimeError(f"Failed to download {expected_type} from Google Drive: {e}")

        if not downloaded or not Path(downloaded).exists():
            found_files = list(temp_subfolder.iterdir())
            if not found_files:
                raise FileNotFoundError(
                    f"No file could be downloaded from Google Drive link for {expected_type}. "
                    "Please verify the link and permissions ('Anyone with the link')."
                )
            downloaded_path = found_files[0]
        else:
            downloaded_path = Path(downloaded)

        original_filename = downloaded_path.name
        
        # In Google Drive, keep clean original filename; outside Drive, add unique prefix
        if is_drive:
            final_filename = original_filename
        else:
            final_filename = f"{clean_prefix}_{original_filename}"
            
        final_path = target_dir / final_filename
        shutil.move(str(downloaded_path), str(final_path))
        try:
            temp_subfolder.rmdir()
        except OSError:
            pass

        return final_path, original_filename

    # 2. Direct HTTP/HTTPS download (e.g. Dropbox dl=1, OneDrive direct, S3, web link)
    callback(f"Downloading {expected_type} from direct web link...", 7)
    
    if "dropbox.com" in url and "dl=0" in url:
        url = url.replace("dl=0", "dl=1")

    session = requests.Session()
    try:
        with session.get(url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            
            cd = resp.headers.get("content-disposition", "")
            orig_filename = None
            if "filename=" in cd:
                match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^";\r\n]+)["\']?', cd)
                if match:
                    orig_filename = urllib.parse.unquote(match.group(1).strip())
            
            if not orig_filename:
                parsed_path = urllib.parse.urlparse(url).path
                inferred = Path(parsed_path).name
                if inferred and "." in inferred:
                    orig_filename = inferred
                else:
                    default_ext = ".mp3" if expected_type == "audio" else ".pdf"
                    orig_filename = f"downloaded_{expected_type}{default_ext}"

            if is_drive:
                final_path = target_dir / orig_filename
            else:
                clean_prefix = str(uuid.uuid4())[:8]
                final_path = target_dir / f"{clean_prefix}_{orig_filename}"

            with open(final_path, "wb") as f_out:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f_out.write(chunk)

            return final_path, orig_filename
    except Exception as e:
        raise RuntimeError(f"Failed to download {expected_type} from link: {e}")


def download_multiple_links(
    urls: List[str],
    target_dir: Path,
    expected_type: str = "audio",
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> List[Tuple[Path, str]]:
    """
    Downloads multiple files from a list of URLs (supporting multi-part recordings or multiple slide decks).
    Returns list of (Path, original_filename).
    """
    callback = progress_callback or (lambda msg, pct: None)
    clean_urls = [u.strip() for u in urls if u and u.strip()]
    results = []
    total = len(clean_urls)

    for idx, u in enumerate(clean_urls):
        part_num = idx + 1
        callback(f"Downloading {expected_type} item {part_num} of {total}...", 5 + int(15 * (idx / max(total, 1))))
        path, fname = download_from_link(
            url=u,
            target_dir=target_dir,
            expected_type=expected_type,
            progress_callback=callback
        )
        results.append((path, fname))

    return results


def parse_session_query(query: str) -> Dict[str, Any]:
    """
    Parses a search query like 'Lecture 1', 'Section 1', 'Lec 2', 'Sec 1', 'Diode', etc.
    """
    q = query.strip().lower()
    is_section = bool(re.search(r'\b(sec|section|tutorial|sheet|lab)\b', q))
    num_match = re.search(r'\b(?:lec|lecture|lecuture|sec|section|tutorial|sheet|lab|part|#)?\s*(\d+)\b', q)
    num = int(num_match.group(1)) if num_match else None
    
    stop_words = {'lecture', 'lecuture', 'lec', 'section', 'sec', 'tutorial', 'sheet', 'lab', 'the', 'for', 'part', 'and', 'in'}
    words = [w for w in re.findall(r'[a-zA-Z]+', q) if w not in stop_words]
    
    return {
        'is_section': is_section,
        'session_type': 'section' if is_section else 'lecture',
        'number': num,
        'keywords': words,
        'raw_query': query.strip()
    }


def scan_course_folder(
    folder_url_or_path: str,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Dict[str, Any]:
    """
    Scans a course folder (either a local directory path or a Google Drive folder link).
    Returns metadata of all contained audio and notes files, and inferred course name.
    """
    callback = progress_callback or (lambda msg, pct: None)
    raw = folder_url_or_path.strip().strip('"').strip("'")
    
    # 1. Local Directory Check
    p_local = Path(raw)
    if p_local.exists() and p_local.is_dir():
        callback("Scanning local course folder structure...", 10)
        items = []
        for file_p in p_local.rglob("*"):
            if not file_p.is_file():
                continue
            name_l = file_p.name.lower()
            if name_l in {'desktop.ini', '.ds_store', '.gitkeep'}:
                continue
            rel_p = str(file_p.relative_to(p_local))
            rel_l = rel_p.lower()
            if 'summaries' in rel_l:
                continue

            ext = file_p.suffix.lower()
            is_audio = ext in SUPPORTED_AUDIO_EXTS
            is_notes = ext in SUPPORTED_NOTES_EXTS

            if is_audio or is_notes:
                items.append({
                    "name": file_p.name,
                    "rel_path": rel_p,
                    "is_audio": is_audio,
                    "is_notes": is_notes,
                    "is_local": True,
                    "local_path": str(file_p.resolve()),
                    "id": None,
                    "size": file_p.stat().st_size
                })

        course_hint = p_local.name
        return {
            "course_hint": course_hint,
            "is_local": True,
            "folder_path": str(p_local.resolve()),
            "files": items
        }

    # 2. Remote Google Drive Folder
    callback("Accessing Google Drive course folder index...", 10)
    folder_id = extract_gdrive_id(raw)
    if not folder_id and not is_google_drive_folder(raw):
        raise ValueError(
            f"Invalid folder specification: '{raw}'. Must be an existing local folder path "
            f"or a valid Google Drive folder link."
        )

    try:
        download_url = f"https://drive.google.com/drive/folders/{folder_id}" if folder_id else raw
        raw_items = gdown.download_folder(
            url=download_url,
            skip_download=True,
            quiet=True,
            use_cookies=False
        )
    except Exception as e:
        err_str = str(e)
        if "Cannot retrieve the public link" in err_str or "permission" in err_str.lower():
            raise PermissionError(
                "Google Drive folder access denied. Please ensure the course folder sharing setting is "
                "set to 'Anyone with the link' (Viewer) in Google Drive, then try again."
            )
        raise RuntimeError(f"Failed to scan Google Drive course folder: {e}")

    items = []
    course_hint = "College Course"
    for g_item in raw_items:
        rel_path = g_item.path
        name = Path(rel_path).name
        name_l = name.lower()
        if name_l in {'desktop.ini', '.ds_store', '.gitkeep'}:
            continue
        rel_l = rel_path.lower()
        if 'summaries' in rel_l:
            continue

        ext = Path(name).suffix.lower()
        is_audio = ext in SUPPORTED_AUDIO_EXTS
        is_notes = ext in SUPPORTED_NOTES_EXTS

        if is_audio or is_notes:
            items.append({
                "name": name,
                "rel_path": rel_path,
                "is_audio": is_audio,
                "is_notes": is_notes,
                "is_local": False,
                "local_path": None,
                "id": g_item.id,
                "size": None
            })

    return {
        "course_hint": course_hint,
        "is_local": False,
        "folder_path": raw,
        "files": items
    }


def search_session_in_folder(
    folder_url_or_path: str,
    query: str,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Dict[str, Any]:
    """
    Searches within a course folder for the specified lecture or section materials.
    Returns:
      - 'status': 'found_both' | 'no_notes' | 'no_record' | 'not_found'
      - 'records': list of audio files matching the session (sorted in part order)
      - 'notes': list of notes files matching the session
      - 'message': clear English explanation
      - 'available_sessions': list of all sessions detected in the folder
      - 'course_hint': detected course name
    """
    callback = progress_callback or (lambda msg, pct: None)
    parsed = parse_session_query(query)
    if isinstance(folder_url_or_path, dict) and "files" in folder_url_or_path:
        scan_res = folder_url_or_path
    else:
        scan_res = scan_course_folder(folder_url_or_path, callback)
    all_files = scan_res["files"]
    course_hint = scan_res["course_hint"]

    # If scan was on root semester directory (like fall 2026), filter by course keywords if provided
    q_lower = query.lower()
    if course_hint and course_hint.lower() in {"fall 2026", "spring 2026", "my drive", "google drive"}:
        for sub_name in ["Power Electronics", "Bio Informatics", "Electronic Vision", "Physiotherapy Equipment", "Artificial Intelligence And Expert Systems", "Feasibility Study"]:
            sub_clean = sub_name.lower()
            if any(term in q_lower for term in sub_clean.split()) or sub_clean in q_lower:
                all_files = [f for f in all_files if sub_clean in f.get('rel_path', '').lower()]
                course_hint = sub_name
                break

    is_sec = parsed['is_section']
    num = parsed['number']
    kws = parsed['keywords']

    # Gather all notes found in this course for continued lecture additions or section reviews
    all_course_notes = []
    seen_all_notes = set()
    for f in all_files:
        if f.get('is_notes'):
            key = f.get('local_path') or f.get('id') or f.get('rel_path') or f.get('name')
            if key not in seen_all_notes:
                seen_all_notes.add(key)
                f_copy = dict(f)
                f_name_l = f['name'].lower()
                f_rel_l = f.get('rel_path', '').lower()
                f_copy['category'] = 'sheet' if ('sheet' in f_name_l or 'sheets' in f_rel_l) else 'lecture_slide'
                all_course_notes.append(f_copy)

    audio_matches = []
    notes_matches = []
    detected_sessions_set = set()

    for f in all_files:
        name = f['name']
        name_l = name.lower()
        rel_l = f.get('rel_path', '').lower()

        # Track all available sessions in this folder for helpful user suggestions
        s_nums = re.findall(r'\b(?:lec|lecture|lecuture|sec|section|ai)?\s*(\d+)\b', name_l)
        is_item_sec = ('section' in rel_l or 'sections' in rel_l or 'sec ' in name_l)
        for s_n in s_nums:
            n_val = int(s_n)
            # Only include reasonable lecture or section numbers (1 to 30)
            if 1 <= n_val <= 30:
                prefix = "Section" if is_item_sec else "Lecture"
                detected_sessions_set.add(f"{prefix} {n_val}")

        part_match = re.search(r'\bpart\s*(\d+)\b', name_l)
        part_num = int(part_match.group(1)) if part_match else 1

        name_without_part = re.sub(r'\bpart\s*\d+\b', '', name_l)
        nums_found = [int(n) for n in re.findall(r'\b(?:lec|lecture|lecuture|sec|section|sheet|ai|bio|power)?\s*(\d+)\b', name_without_part)]

        has_num = (num in nums_found) if num is not None else False
        has_kw = any(k in name_l or k in rel_l for k in kws) if kws else False

        if f['is_audio']:
            in_sec_folder = ('sections' in rel_l or 'section' in name_l or 'sec ' in name_l)
            if is_sec != in_sec_folder and num is not None:
                continue

            if has_num or has_kw or (num is None and not kws):
                audio_matches.append((f, part_num, name_l))

        elif f['is_notes']:
            in_sheets_folder = ('sheets' in rel_l or 'sheet' in name_l)
            f_copy = dict(f)
            if is_sec:
                # User requirement: add all lectures and notes to sections part because maybe the AT taught the lecture or talked about part of it
                if (in_sheets_folder or 'section' in name_l) and (has_num or has_kw):
                    f_copy['category'] = 'sheet'
                    notes_matches.append((f_copy, 1, name_l))
                elif has_num:
                    f_copy['category'] = 'lecture_slide'
                    notes_matches.append((f_copy, 2, name_l))
                else:
                    f_copy['category'] = 'lecture_slide'
                    notes_matches.append((f_copy, 3, name_l))
            else:
                if in_sheets_folder:
                    continue
                f_copy['category'] = 'lecture_slide'
                if has_num or has_kw:
                    notes_matches.append((f_copy, 1, name_l))
                elif num == 1 and ('lectures' in rel_l or Path(f.get('rel_path', '')).parent == Path('.')):
                    notes_matches.append((f_copy, 2, name_l))

    # Sort audio parts: part 1 before part 2
    audio_matches.sort(key=lambda x: (x[1], x[2]))
    notes_matches.sort(key=lambda x: (x[1], x[2]))

    records = [x[0] for x in audio_matches]

    # Deduplicate notes while preserving priority order
    seen_notes_keys = set()
    notes = []
    for item in notes_matches:
        n_obj = item[0]
        n_key = n_obj.get('local_path') or n_obj.get('id') or n_obj.get('name')
        if n_key not in seen_notes_keys:
            seen_notes_keys.add(n_key)
            notes.append(n_obj)

    # Available sessions sorted naturally
    def session_sort_key(s: str):
        m = re.search(r'(\d+)', s)
        n = int(m.group(1)) if m else 0
        return (0 if 'Lecture' in s else 1, n)

    available_sessions = sorted(list(detected_sessions_set), key=session_sort_key)

    session_title = f"{parsed['session_type'].capitalize()} {num}" if num else query

    if records and notes:
        status = "found_both"
        rec_desc = f"{len(records)} recording part(s)" if len(records) > 1 else "audio recording"
        if is_sec:
            message = f"Found {rec_desc} and {len(notes)} course lecture note(s) & sheet(s) for {session_title}. Select which slides the AT covered."
        else:
            message = f"Found {rec_desc} and {len(notes)} lecture notes document(s) for {session_title}."
    elif records and not notes:
        status = "no_notes"
        rec_desc = f"{len(records)} recording part(s)" if len(records) > 1 else "audio recording"
        message = f"Found {rec_desc} for {session_title}, but no lecture notes/slides were found in this folder."
    elif not records and notes:
        status = "no_record"
        message = f"Found lecture notes for {session_title}, but no audio recording was found in this folder."
    else:
        status = "not_found"
        message = f"No audio recording or lecture notes found matching '{query}' in this course folder."

    return {
        "success": True,
        "query": query,
        "session_title": session_title,
        "course_hint": course_hint,
        "status": status,
        "records": records,
        "notes": notes,
        "all_course_notes": all_course_notes,
        "is_section_query": is_sec,
        "message": message,
        "available_sessions": available_sessions,
        "is_local": scan_res["is_local"]
    }


def download_selected_folder_items(
    items: List[Dict[str, Any]],
    target_dir: Path,
    expected_type: str = "audio",
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> List[Tuple[Path, str]]:
    """
    Downloads or resolves selected items from a folder search.
    If the item is local, resolves directly on disk without copying or downloading.
    If remote (Google Drive), downloads via gdown using the file's ID.
    Returns list of (Path, original_filename).
    """
    callback = progress_callback or (lambda msg, pct: None)
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for idx, item in enumerate(items):
        item_name = item.get("name", f"{expected_type}_{idx+1}")
        callback(f"Resolving {expected_type} item ({idx+1}/{len(items)}: {item_name})...", 10 + int(20 * (idx+1)/len(items)))

        if item.get("is_local") and item.get("local_path"):
            local_p = Path(item["local_path"])
            if local_p.exists():
                results.append((local_p, item_name))
                continue

        # Remote file from Google Drive or direct link
        file_id = item.get("id")
        if file_id:
            url = f"https://drive.google.com/uc?id={file_id}"
            path, orig_name = download_from_link(
                url=url,
                target_dir=target_dir,
                expected_type=expected_type,
                progress_callback=callback
            )
            results.append((path, orig_name))
        elif item.get("url"):
            path, orig_name = download_from_link(
                url=item["url"],
                target_dir=target_dir,
                expected_type=expected_type,
                progress_callback=callback
            )
            results.append((path, orig_name))
        else:
            raise FileNotFoundError(f"Cannot resolve item '{item_name}': missing local path and file ID.")

    return results


def download_from_folder_link(
    folder_url: str,
    target_dir: Path,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Tuple[Path, Optional[Path], str, Optional[str]]:
    """
    Legacy convenience function: downloads first audio and notes found in folder.
    """
    search_res = search_session_in_folder(folder_url, "Lecture 1", progress_callback)
    if search_res["records"]:
        recs = download_selected_folder_items([search_res["records"][0]], target_dir, "audio", progress_callback)
        audio_path, audio_name = recs[0]
    else:
        raise FileNotFoundError("No supported audio file found in the Google Drive folder.")

    notes_path, notes_name = None, None
    if search_res["notes"]:
        nts = download_selected_folder_items([search_res["notes"][0]], target_dir, "notes", progress_callback)
        notes_path, notes_name = nts[0]

    return audio_path, notes_path, audio_name, notes_name
