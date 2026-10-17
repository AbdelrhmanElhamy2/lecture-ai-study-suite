import json
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Tuple, Any, List, Union
from google import genai
from google.genai import types
import pypdf
from models import (
    LectureStudyGuide, VerificationAuditReport, VerificationResult, ContradictionItem
)
from config import get_gemini_api_key, DEFAULT_MODEL, UPLOAD_DIR


def _is_retryable_gemini_error(exc: Exception) -> bool:
    message = str(exc).upper()
    return any(code in message for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "TOO MANY REQUESTS"))


def _gemini_error_category(exc: Exception) -> str:
    message = str(exc).upper()
    if "INVALID AUDIT RESPONSE" in message:
        return "Gemini returned an invalid transcript audit response."
    if "404" in message or "NOT_FOUND" in message or "MODEL" in message and "NOT AVAILABLE" in message:
        return "The configured Gemini model is unavailable."
    if "401" in message or "403" in message or "API_KEY" in message or "PERMISSION" in message:
        return "Gemini rejected the API key or request permissions."
    if _is_retryable_gemini_error(exc):
        return "Gemini is temporarily overloaded or rate limited."
    return "Gemini rejected the request."


def slice_pdf_pages(
    input_pdf: Path,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    output_dir: Optional[Path] = None
) -> Tuple[Path, str]:
    """
    Slices a PDF to the specified start and end page range (1-indexed, inclusive).
    If start_page or end_page are omitted, or if slicing is unnecessary/invalid,
    returns the original or bounded PDF with a descriptive label.
    """
    if not input_pdf.exists():
        raise FileNotFoundError(f"Notes file not found: {input_pdf.name}")

    if input_pdf.suffix.lower() != ".pdf":
        return input_pdf, "Attached lecture notes document"

    try:
        reader = pypdf.PdfReader(str(input_pdf))
        if getattr(reader, "is_encrypted", False):
            try:
                decrypted = reader.decrypt("")
                if decrypted == 0:
                    raise ValueError(f"The PDF '{input_pdf.name}' is password-protected. Please remove the password before uploading.")
            except Exception as dec_err:
                if "password-protected" in str(dec_err):
                    raise
                raise ValueError(f"The PDF '{input_pdf.name}' is password-protected. Please remove the password before uploading.")
        total_pages = len(reader.pages)
    except ValueError:
        raise
    except Exception as pdf_err:
        raise ValueError(f"The PDF file '{input_pdf.name}' appears to be corrupted or unreadable. Please check the file and try again.")

    if total_pages == 0:
        return input_pdf, "Attached lecture notes (empty)"

    # If neither boundary is specified, use full deck
    if start_page is None and end_page is None:
        return input_pdf, f"Full slide deck ({total_pages} slides)"

    # Normalize and clamp bounds (1-indexed)
    s = start_page if start_page is not None else 1
    s = max(1, min(s, total_pages))

    e = end_page if end_page is not None else total_pages
    e = max(s, min(e, total_pages))

    if s == 1 and e == total_pages:
        return input_pdf, f"Full slide deck ({total_pages} slides)"

    writer = pypdf.PdfWriter()
    for p_num in range(s - 1, e):
        writer.add_page(reader.pages[p_num])

    target_dir = output_dir or UPLOAD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    sliced_filename = f"sliced_{input_pdf.stem}_{s}_to_{e}.pdf"
    sliced_path = target_dir / sliced_filename

    with open(sliced_path, "wb") as f_out:
        writer.write(f_out)

    return sliced_path, f"Slides {s}–{e} of {total_pages}"


SYSTEM_INSTRUCTION = r"""
You are an elite university professor, bilingual academic translator, and exam strategist across all academic disciplines.
Your task is to analyze the provided local transcript of a university/college lecture, with optional lecture notes, and transform it into a comprehensive, publication-quality academic study guide.

CRITICAL INSTRUCTIONS:
1. UNIVERSAL & SPECIALIZED ENGINEERING EXPERTISE ACROSS ALL DISCIPLINES:
   - This platform serves university engineering students across all major disciplines and STEM branches:
     * Electrical, Electronics & Communication Engineering: Circuit analysis (KVL/KCL, Thevenin/Norton), semiconductors (diodes, BJTs, MOSFETs), operational amplifiers, analog/digital filters, power electronics (rectifiers, inverters, converters), signal processing (Fourier, Laplace, z-transform, sampling), electromagnetic fields, digital logic, communication systems (modulation, bandwidth).
     * Mechanical, Aerospace & Mechatronics Engineering: Statics, dynamics, mechanics of materials (stress-strain, Mohr's circle, torsion, bending), thermodynamics (first & second laws, heat engines, refrigeration, entropy), fluid mechanics (Navier-Stokes, Bernoulli, laminar/turbulent flow), heat transfer (conduction, convection, radiation), kinematics, vibrations, control theory.
     * Computer Science & Software Engineering: Algorithms, data structures, computer architecture (pipelining, caching, instruction sets), operating systems (processes, threads, deadlocks, semaphores, memory management), networking, database theory, embedded systems, state machines.
     * Civil, Structural & Environmental Engineering: Structural analysis (trusses, beams, shear/moment diagrams), mechanics of solids, geotechnical engineering, soil mechanics, fluid hydraulics, concrete and steel design, hydrology.
     * Chemical, Petroleum & Materials Engineering: Mass and energy balances, chemical thermodynamics, reaction kinetics, chemical reactor design, mass transfer, separation processes (distillation, absorption), material crystallography, phase diagrams.
     * Biomedical & Bioengineering: Bioinstrumentation, biosensors, biopotential electrodes, ECG/EMG/EEG signals, biomechanics, biomaterials, medical imaging systems (MRI/CT/US), physiological modeling, medical device standards (IEC 60601-1).
     * Systems, Robotics & Industrial Engineering: State-space control, kinematics & inverse kinematics, sensors & actuators, optimization, operations research, queueing theory.
     * Foundational STEM: Engineering mathematics, calculus, linear algebra, differential equations, applied physics, chemistry.
   - Automatically adapt your vocabulary, depth, and pedagogical breakdown to match the conventions and rigors of the engineering discipline represented in the transcript.

2. STRICT 100% ENGLISH OUTPUT (ZERO ARABIC SCRIPT IN OUTPUT):
   - The lecturer speaks in a mixture of Arabic (Egyptian dialect, MSA, or regional phrasing) and English.
   - THE FINAL STUDY GUIDE AND ALL JSON FIELDS MUST BE 100% IN ACADEMIC ENGLISH.
   - ABSOLUTELY DO NOT OUTPUT ANY ARABIC SCRIPT OR GLYPHS ANYWHERE.
   - Translate all Arabic spoken explanations, clinical/engineering cases, analogies, and professor's remarks into formal academic English.
   - Preserve all technical English terminology, engineering component names, and SI/standard units accurately.

3. EXHAUSTIVE COVERAGE & STRICT LECTURE FIDELITY (ZERO OUTSIDE FILLER):
   - Do NOT produce a superficial summary. Provide exhaustive, in-depth topic-by-topic coverage explaining all theories, proofs, circuit schematics, mechanisms, algorithms, or derivations the professor explained.
   - Confine the study guide, sections, and questions to what is supported by THIS lecture transcript.
   - Do NOT inject unrelated textbook chapters, unmentioned circuits/laws/devices, or external generic topics that the professor never covered.
   - Every exam question in `exam_readiness_section` MUST directly test concepts, derivations, calculations, or engineering principles supported by this transcript.

4. TRANSLATING PROFESSOR'S / DOCTOR'S EXAM ALERTS & EMPHASIZED HIGHLIGHTS:
   - Actively detect every instance where the professor/instructor emphasized importance, warned about exams, highlighted common pitfalls, or repeated a rule.
   - For `cue_detected`: TRANSLATE THE SPOKEN CUE ENTIRELY INTO ENGLISH (e.g. "Professor warned: 'Pay close attention to this circuit: calculating the transfer function and Bode plot always comes on the final exam!'").
   - For each alert, explain why it matters and how to avoid losing points on exams.

5. DISCIPLINE-AWARE VISUAL DIAGRAMS (OPTIMIZED FOR ALL ENGINEERING DISCIPLINES):
   - Choose the visual diagram type that best fits the subject:
     * WAVEFORM: Continuous time-domain signals, waveforms (voltage/current waveforms, PWM switching, bio-signals, sound waves, vibrational modes), frequency responses, Bode plots, or stress-strain curves.
     * BLOCK_DIAGRAM: Multi-stage engineering architectures (e.g. Sensor -> Op-Amp -> Filter -> ADC -> Microcontroller -> Actuator), feedback control loops, plant/controller diagrams.
     * FLOWCHART: Multi-step engineering algorithms, troubleshooting pipelines, decision trees, manufacturing/design procedures.
     * PROCESS_CYCLE: Thermodynamic cycles (Carnot, Rankine, Otto, Diesel, Brayton), iterative state machines, closed-loop feedback processes.
     * COMPARISON_BAR: Material properties (yield strength, thermal conductivity), component benchmarks, algorithmic complexity comparisons.
     * TIMELINE: Historical evolution, development milestones, protocol phases.
     * CONCEPT_MAP: Engineering taxonomies, structural classifications, system breakdowns.
   - STRICT DIAGRAM TITLE & NODE COUNT FIDELITY:
     * When a diagram title specifies a count (e.g. 'The Three Pillars of Power Electronics', 'Four Necessary Conditions'), the elements list MUST contain EXACTLY that number of elements (e.g. exactly 3 pillars: 'Power', 'Electronics', and 'Control').
     * In CONCEPT_MAP diagrams, NEVER include the central overarching topic (e.g. 'Power Electronics') as an outer element; only the surrounding sub-disciplines or pillars should be elements.
   - Provide clear, descriptive English labels and subtitles for all diagram elements.

6. MATHEMATICAL FORMULAS & GOVERNING EQUATIONS:
   - For quantitative / computational / engineering subjects:
     * Extract governing equations, derivations, and formulas in `formulas` under each section with clean LaTeX syntax.
     * List physical variables with their units (e.g. V, A, Hz, Pa, N/m², $\Omega$, W, J, rad/s) and physical meanings.
     * Provide specific exam calculation guidance and common numerical pitfalls.
     * STRICT FORMULA & TYPOGRAPHY FIDELITY: When writing mathematical equations in `detailed_explanation` or `formulas`, ALWAYS use standard, well-formed LaTeX (e.g. `\frac{a}{b}`, `\sin(\omega t)`, `\cos(\omega t)`, `\int_0^\pi`, `\partial`, `\nabla`). ABSOLUTELY NEVER use corrupted pseudo-unicode tokens (such as writing "∆ rac" or using partial derivatives/complement symbols "∂∆∁" instead of "sin" or "cos"). Always escape backslashes cleanly in JSON.
   - For qualitative topics:
     * If no mathematical formulas were taught, leave `formulas` as an empty list `[]`. Do NOT invent fake equations. Focus on rigorous conceptual definitions, physical principles, or system architectures.

7. AUTHENTIC EXAM READINESS:
   - Generate realistic, challenging exam practice questions tailored to the professor's exam style across engineering fields:
     * Quantitative Calculations & Numerical Analysis (e.g. circuit analysis, thermal efficiency, bending stress, beam deflection).
     * Derivation & Proof Questions (e.g. deriving transfer functions, Navier-Stokes simplifications, thermodynamic relations).
     * Design Scenarios & Trade-off Questions (e.g. selecting component ratings, controller stability criteria, material selection).
     * Conceptual & Diagnostic Problem Solving (e.g. debugging race conditions, failure analysis, resonance troubleshooting).
   - Include complete model answers, grading rubric criteria, and the professor's specific exam tip.

8. FULL ENGLISH TRANSCRIPT:
   - In `full_transcript_english`, provide the complete lecture translated into fluent, coherent, academic English paragraphs for cross-referencing.

9. STRICT LECTURE NOTES & SLIDES INTEGRATION RULES (WHEN SLIDES/NOTES ARE ATTACHED):
   - The local transcript is the record of spoken content available to this request; do not claim the source audio was independently checked.
   - If lecture notes or slides are provided alongside the transcript:
     * Extract exact terminology, formal definitions, governing equations, diagrams, and tables from the slides only for topics supported by the transcript.
     * Do not include slide topics or examples that the transcript does not support.
     * SCOPE FIDELITY: The study guide must contain no more content than what the professor taught in the lecture, and no less (capturing all taught material, but strictly excluding unmentioned slide contents).
"""

from typing import List, Union


def _file_state(file_obj: Any) -> str:
    """Return the Gemini File API state name, tolerating a missing/None state."""
    state = getattr(file_obj, "state", None)
    return getattr(state, "name", str(state or "")) if state is not None else ""


def _delete_remote_files(client: genai.Client, files: List[Any]) -> None:
    """Best-effort removal of uploaded lecture files from the Gemini File API after processing."""
    for f in files:
        try:
            client.files.delete(name=f.name)
        except Exception:
            pass


def analyze_lecture_transcript(
    transcript_text: str,
    notes_path: Optional[Union[Path, List[Path]]] = None,
    start_slide: Optional[int] = None,
    end_slide: Optional[int] = None,
    slide_ranges: Optional[List[Tuple[Optional[int], Optional[int]]]] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    course_hint: Optional[str] = None,
    lecturer_hint: Optional[str] = None,
    study_mode: str = "detailed",
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> LectureStudyGuide:
    """
    Sends a local transcript and optional lecture slides/notes to Gemini for guide generation.
    Original audio is never passed to Gemini.
    Works universally across STEM, Medicine, Law, Business, and Humanities.
    """
    key = api_key or get_gemini_api_key()
    if not key:
        raise ValueError(
            "Gemini API key is required. Please set GEMINI_API_KEY in your environment, "
            "provide it in the UI, or configure .env."
        )
    if not transcript_text or not transcript_text.strip():
        raise ValueError("A non-empty local transcript is required for study-guide generation.")
    client = genai.Client(api_key=key)
    uploaded_files: List[Any] = []
    try:
        return _analyze_lecture_audio_impl(
            client=client,
            uploaded_files=uploaded_files,
            transcript_text=transcript_text,
            notes_path=notes_path,
            start_slide=start_slide,
            end_slide=end_slide,
            slide_ranges=slide_ranges,
            model=model,
            course_hint=course_hint,
            lecturer_hint=lecturer_hint,
            study_mode=study_mode,
            progress_callback=progress_callback,
        )
    finally:
        _delete_remote_files(client, uploaded_files)


def _analyze_lecture_audio_impl(
    client: genai.Client,
    uploaded_files: List[Any],
    transcript_text: str,
    notes_path: Optional[Union[Path, List[Path]]] = None,
    start_slide: Optional[int] = None,
    end_slide: Optional[int] = None,
    slide_ranges: Optional[List[Tuple[Optional[int], Optional[int]]]] = None,
    model: Optional[str] = None,
    course_hint: Optional[str] = None,
    lecturer_hint: Optional[str] = None,
    study_mode: str = "detailed",
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> LectureStudyGuide:
    chosen_model = model or DEFAULT_MODEL

    # Normalize notes paths
    if isinstance(notes_path, (list, tuple)):
        notes_paths = [Path(p) for p in notes_path if p]
    elif notes_path:
        notes_paths = [Path(notes_path)]
    else:
        notes_paths = []

    # Handle optional lecture notes / slides
    notes_files = []
    notes_ref_labels = []
    for idx, np in enumerate(notes_paths):
        if not np.exists():
            continue
        if progress_callback:
            progress_callback(f"Preparing lecture notes / slides ({idx+1}/{len(notes_paths)}: {np.name})...", 50 + int(4 * (idx + 1) / max(1, len(notes_paths))))
        
        # Apply slide range to deck (per-deck or primary deck fallback)
        if slide_ranges and idx < len(slide_ranges):
            s_slide, e_slide = slide_ranges[idx]
        else:
            s_slide = start_slide if idx == 0 else None
            e_slide = end_slide if idx == 0 else None
        processed_notes_path, ref_label = slice_pdf_pages(
            np, start_page=s_slide, end_page=e_slide, output_dir=UPLOAD_DIR
        )
        notes_ref_labels.append(f"{np.name} ({ref_label})")

        if progress_callback:
            progress_callback(f"Sending selected lecture slides ({idx+1}/{len(notes_paths)}) to Gemini...", 56 + int(3 * (idx + 1) / max(1, len(notes_paths))))
        
        nf = client.files.upload(file=str(processed_notes_path))
        uploaded_files.append(nf)
        while _file_state(nf) == "PROCESSING":
            time.sleep(1)
            nf = client.files.get(name=nf.name)
        if _file_state(nf) == "FAILED":
            raise RuntimeError(f"Notes processing failed for {np.name}: {nf.error}")
        notes_files.append(nf)

    notes_ref_label = "; ".join(notes_ref_labels) if notes_ref_labels else None

    if progress_callback:
        progress_callback(f"Generating the study guide with {chosen_model} from the local transcript...", 62)

    hint_text = ""
    if course_hint or lecturer_hint:
        hints = []
        if course_hint:
            hints.append(f"Subject / Course: {course_hint}")
        if lecturer_hint:
            hints.append(f"Lecturer / Instructor: {lecturer_hint}")
        hint_text = f" User provided context: [{', '.join(hints)}]."

    mode_instructions = {
        "revision": "Create a compact revision guide: retain every taught idea, but prefer crisp explanations, 5–8 high-yield bullets per section, and only the most useful diagrams.",
        "exam": "Create an exam-first guide: prioritize professor cues, common pitfalls, calculation steps, and a substantial, varied practice-question bank. Keep explanations focused on what is testable.",
        "detailed": "Create thorough, structured notes suitable for learning the lecture from scratch.",
    }
    selected_mode = study_mode if study_mode in mode_instructions else "detailed"

    notes_instruction = ""
    if notes_files:
        multi_deck_note = ""
        if len(notes_files) > 1:
            multi_deck_note = (
                f" Notice: {len(notes_files)} slide decks are attached ({notes_ref_label}). "
                "The lecture may finish one deck and advance into the next for several slides. "
            )
        notes_instruction = (
            f" [ATTACHED LECTURE SLIDES: {notes_ref_label}].{multi_deck_note} "
            "Use the locally generated transcript as the record of spoken content and the slides as supporting material. "
            "Do not claim that the original audio was independently checked. "
            "Use the slides to extract exact mathematical notation, precise terminology, "
            "definitions, and diagram structures ONLY for topics supported by the transcript. "
            "STRICT NEGATIVE CONSTRAINT: DO NOT include any slide, topic, formula, or example that the doctor skipped, omitted, "
            "or that the transcript does not support. "
        )

    prompt = (
        f"Analyze this university lecture transcript completely.{hint_text} "
        f"{notes_instruction}"
        "Identify the academic course/subject, lecture topic, and professor from the transcript (or user context). "
        "This lecture covers an engineering or STEM discipline (e.g. Electrical, Electronics, Signals & Systems, Mechanical, Thermodynamics, Fluid Dynamics, Computer Science, Software Engineering, Civil, Structural, Chemical, Biomedical, Robotics, Control Systems, or Applied Mathematics/Physics). "
        "Translate all Arabic speech, spoken explanations, and doctor's cues into 100% fluent academic English. "
        "STRICT MANDATE 1 (LANGUAGE): DO NOT OUTPUT ANY ARABIC SCRIPT OR ARABIC CHARACTERS ANYWHERE IN THE OUTPUT. "
        "STRICT MANDATE 2 (FIDELITY): Keep the content strictly confined to what the transcript supports. "
        "Do NOT invent outside textbook explanations, unmentioned circuits/laws/diseases, or questions on topics not supported by the transcript. "
        "Translate what the doctor said into English for `cue_detected`. "
        "Extract full in-depth notes, governing mathematical formulas (if applicable; leave empty if non-math), "
        "structured comparison tables, visual diagram specifications, and realistic exam practice questions with model answers. "
        f"Study mode: {mode_instructions[selected_mode]} "
        "For every section, populate source_reference with the best approximate timestamp from the transcript segment markers. "
        "Do not fabricate timestamps; use an empty string when genuinely uncertain."
        f"\n\nLOCAL TRANSCRIPT (ordered recordings, timestamps, detected language):\n{transcript_text}"
    )

    from config import gemini_model_candidates
    candidate_models = gemini_model_candidates(chosen_model)

    response = None
    last_error = None
    successful_model = chosen_model

    contents_payload = [*notes_files, prompt]

    for model_name in candidate_models:
        for attempt in range(2):
            try:
                if progress_callback:
                    retry_label = f" (Attempt {attempt + 1}/2)" if attempt > 0 else ""
                    progress_callback(f"Generating the guide with {model_name}{retry_label}...", 66)

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents_payload,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=LectureStudyGuide,
                        temperature=0.2,
                    )
                )
                if response is not None:
                    last_error = None
                if response and response.text:
                    break
            except Exception as exc:
                last_error = exc
                if _is_retryable_gemini_error(exc):
                    wait_sec = 2
                    if progress_callback:
                        progress_callback(f"{model_name} is temporarily busy; retrying within the configured model policy...", 66)
                    time.sleep(wait_sec)
                    continue
                else:
                    raise RuntimeError(_gemini_error_category(exc)) from exc
        if response and response.text:
            successful_model = model_name
            break
        if not last_error or not _is_retryable_gemini_error(last_error):
            break

    if not response or not response.text:
        if last_error and _is_retryable_gemini_error(last_error):
            raise RuntimeError(
                f"{_gemini_error_category(last_error)} Automatic attempts were limited to two per approved model ({', '.join(candidate_models)}). Please try again later."
            ) from last_error
        raise RuntimeError(
            "Gemini did not return a study guide." if last_error is None else _gemini_error_category(last_error)
        ) from last_error

    # Parse and validate returned JSON
    raw_json = response.text.strip()
    try:
        data = json.loads(raw_json)
        draft_guide = LectureStudyGuide.model_validate(data)
    except Exception as parse_exc:
        match = re.search(r"\{.*\}", raw_json, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            draft_guide = LectureStudyGuide.model_validate(data)
        else:
            raise ValueError(f"Failed to parse model response into LectureStudyGuide: {parse_exc}")

    if notes_ref_label:
        draft_guide.notes_reference = notes_ref_label

    # Phase 2: Check draft guide against the local transcript and optional slides.
    verified_guide, _ = verify_and_reconcile_study_guide(
        client=client,
        transcript_text=transcript_text,
        notes_file=notes_files if notes_files else None,
        notes_reference=notes_ref_label,
        guide=draft_guide,
        model=successful_model,
        progress_callback=progress_callback
    )
    if notes_ref_label and not verified_guide.notes_reference:
        verified_guide.notes_reference = notes_ref_label
    return verified_guide


AUDIT_SYSTEM_INSTRUCTION = """
You are the Chief Academic Auditor, Fact-Checker, and University Examination Inspector.
Your sole duty is to protect students from errors, hallucinations, scope creep, and contradictions between the local transcript, official lecture notes/slides, and generated study materials.

You will be provided with:
1. The locally generated, timestamped transcript of the lecture. The original audio is not provided.
2. (If provided) The official lecture notes or slides deck for this class.
3. A draft Study Guide generated from this lecture.

YOUR RIGOROUS AUDIT MANDATE:
Cross-check the draft Study Guide against the locally generated transcript AND optional lecture notes/slides. Do not claim to verify the transcript against audio.
Detect ANY AND ALL contradictions, factual discrepancies, erroneous statements, or scope violations, including:
1. Slide Scope Leakage & Unmentioned Content:
   - Check whether the guide added information, sections, formulas, or slides not supported by the transcript.
   - If slide content is not supported by the transcript, flag it and remove it from `corrected_guide` where appropriate.
2. Operational / Physical / Conceptual Contradictions:
   - Inverted operating states (e.g., guide says diode conducts when vs < 0, but professor explained it blocks; guide says drug is an agonist when professor taught it is an antagonist; guide says court overturned when professor said affirmed).
   - Reversed cause-and-effect, inverted polarities, or wrong direction of currents/forces/signals.
3. Formula / Derivation Errors:
   - Discrepancies in governing equations, wrong coefficients, missing factors of pi, 2, or sqrt(2), or wrong mathematical limits compared to what the professor wrote/stated and what the slides specify.
4. Spoken Rules, Warnings & Emphases:
   - Misattributions of what the professor explicitly stated would be tested or cautioned students about.
   - Any alert claiming the professor said something that contradicts what was actually said.
5. Completeness & Scope Fidelity:
   - Ensure the guide captures all material taught by the professor—not more than what was taught in the lecture, and not less (unless it was not in the lecture record).

CRITICAL RESOLUTION RULES:
- If you detect any contradiction or scope leakage:
  1. Record each specific issue in `contradictions`:
     - `section_title`: The topic or section where the issue occurred.
     - `guide_statement`: The exact contradictory or unmentioned claim in the draft guide.
     - `audio_truth`: Relevant transcript evidence (or note that the point is unsupported by the transcript).
     - `correction_applied`: The precise correction made to resolve the discrepancy or prune the unmentioned content.
  2. Produce the FULL, CORRECTED `LectureStudyGuide` in `corrected_guide`:
     - Modify the text, bullets, formulas, tables, alerts, and exam questions to resolve discrepancies against the transcript.
     - Preserve all other accurate content from the draft guide.
     - Set `contradictions_detected` to the number of resolved contradictions.
     - Update `audit_summary` explaining the resolutions made.
- If the draft Study Guide has ZERO transcript discrepancies or scope leakages:
  - Set `contradictions_detected` to 0.
  - Set `contradictions` to an empty list `[]`.
  - Return the draft guide as `corrected_guide`.
  - Provide a clear `audit_summary` stating that the guide was checked against the transcript and notes; do not claim audio-to-transcript accuracy was checked.

STRICT MANDATES:
- Output MUST be 100% in academic English (Zero Arabic script).
- Confine all corrections to content supported by the transcript and provided notes.
"""


def verify_and_reconcile_study_guide(
    client: genai.Client,
    transcript_text: str,
    guide: LectureStudyGuide,
    notes_file: Optional[Union[Any, List[Any]]] = None,
    notes_reference: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Tuple[LectureStudyGuide, VerificationAuditReport]:
    """
    Performs an automated audit comparing the generated study guide against
    locally transcribed text and (optionally) lecture notes/slides.
    Detects contradictions, scope discrepancies, or formula errors,
    and returns a reconciled study guide and verification audit report.
    """
    notes_list = (notes_file if isinstance(notes_file, (list, tuple)) else [notes_file]) if notes_file else []

    has_notes = len(notes_list) > 0
    if not transcript_text or not transcript_text.strip():
        raise ValueError("A non-empty local transcript is required for verification.")
    audit_notes_desc = f" and attached lecture slides ({notes_reference})" if has_notes else ""
    if progress_callback:
        progress_callback(f"Checking study guide against local transcript{audit_notes_desc} for contradictions and scope...", 72)

    audit_prompt = (
        f"Perform an exhaustive fact-check, contradiction audit, and scope verification of this Study Guide against the local transcript{audit_notes_desc}. The original audio was not provided and its transcription accuracy is not being assessed.\n\n"
        "DRAFT STUDY GUIDE TO AUDIT:\n"
        f"{guide.model_dump_json(exclude={'full_transcript_english'})}\n\n"
        "Use the transcript text and its timestamps to check every operational claim, formula, lecturer alert, and exam question. "
        + (
            "CRITICAL: Verify that NO topics, proofs, or details from the attached lecture slides are included in the guide "
            "unless the transcript supports them. If any slide content is not supported by the transcript, "
            "flag it in `contradictions` and remove it from `corrected_guide`. "
            if has_notes else ""
        )
        + "If there are any contradictions or discrepancies, document each in `contradictions` and return the complete "
        "reconciled study guide in `corrected_guide`. "
        "If there are no contradictions, set `contradictions_detected` to 0 and return the guide unchanged."
    )

    contents_payload = [*notes_list, f"LOCAL TRANSCRIPT:\n{transcript_text}\n\n{audit_prompt}"]

    from config import gemini_model_candidates
    candidate_models = gemini_model_candidates(model)

    last_audit_error = None
    nonretryable_audit_failure = False
    for model_name in candidate_models:
        resp = None
        for attempt in range(2):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=contents_payload,
                    config=types.GenerateContentConfig(
                        system_instruction=AUDIT_SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=VerificationResult,
                        temperature=0.1,
                    )
                )
                if resp is not None:
                    last_audit_error = None
                if resp and resp.text:
                    break
            except Exception as e:
                last_audit_error = e
                if _is_retryable_gemini_error(e):
                    time.sleep(2)
                    continue
                nonretryable_audit_failure = True
                break

        if nonretryable_audit_failure:
            break
        if (not resp or not resp.text) and (not last_audit_error or not _is_retryable_gemini_error(last_audit_error)):
            break

        if resp and resp.text:
            raw_json = resp.text.strip()
            try:
                v_result = VerificationResult.model_validate_json(raw_json)
            except Exception:
                m = re.search(r"\{.*\}", raw_json, re.DOTALL)
                if m:
                    try:
                        v_result = VerificationResult.model_validate_json(m.group(0))
                    except Exception:
                        last_audit_error = ValueError("Invalid audit response")
                        nonretryable_audit_failure = True
                        break
                else:
                    last_audit_error = ValueError("Invalid audit response")
                    nonretryable_audit_failure = True
                    break

            if nonretryable_audit_failure:
                break

            scope_discrepancies = 0
            if v_result.contradictions:
                for c in v_result.contradictions:
                    c_text = f"{c.guide_statement} {c.audio_truth} {c.correction_applied}".lower()
                    if any(term in c_text for term in ["slide", "scope", "not mentioned", "unmentioned", "skipped", "not covered"]):
                        scope_discrepancies += 1

            audit_report = VerificationAuditReport(
                audit_passed=True,
                contradictions_detected=v_result.contradictions_detected,
                contradictions=v_result.contradictions,
                overall_fidelity_summary=(
                    f"Transcript-to-guide check completed: {v_result.contradictions_detected} discrepancy/scope issue(s) identified and reconciled. Audio-to-transcript accuracy was not independently verified."
                    if v_result.contradictions_detected > 0 else
                    f"No discrepancies found in the transcript-to-guide check{' with slides' if has_notes else ''}. Audio-to-transcript accuracy was not independently verified."
                ),
                verified_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                notes_audited=has_notes,
                notes_reference=notes_reference,
                scope_discrepancies_resolved=scope_discrepancies
            )

            reconciled = v_result.corrected_guide
            # Retain transcript if stripped during audit prompt
            if not reconciled.full_transcript_english and guide.full_transcript_english:
                reconciled.full_transcript_english = guide.full_transcript_english
            if notes_reference and not reconciled.notes_reference:
                reconciled.notes_reference = notes_reference
            reconciled.verification_report = audit_report

            if progress_callback:
                if v_result.contradictions_detected > 0:
                    progress_callback(
                        f"Resolved {v_result.contradictions_detected} transcript/slide discrepancy issue(s). Updated study guide.",
                        82
                    )
                else:
                    progress_callback(
                        "Transcript-to-guide check complete: no discrepancies found; audio recognition accuracy was not independently verified.",
                        82
                    )

            return reconciled, audit_report

    # Graceful fallback if verification API call fails: preserve original guide
    failure_summary = (
        f"Transcript-to-guide verification unavailable: {_gemini_error_category(last_audit_error)} Audio recognition accuracy was not independently verified."
        if last_audit_error else
        "Transcript-to-guide verification unavailable: Gemini did not return a usable audit response. Audio recognition accuracy was not independently verified."
    )
    fallback_report = VerificationAuditReport(
        audit_passed=False,
        contradictions_detected=0,
        contradictions=[],
        overall_fidelity_summary=failure_summary,
        verified_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        notes_audited=has_notes,
        notes_reference=notes_reference,
        scope_discrepancies_resolved=0
    )
    guide.verification_report = fallback_report
    if notes_reference and not guide.notes_reference:
        guide.notes_reference = notes_reference
    if progress_callback:
        progress_callback("Fidelity check unavailable (verification API call failed).", 82)
    return guide, fallback_report

