import os
os.environ["LECTUREAI_TESTING"] = "1"

import unittest
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models import (
    LectureStudyGuide, LectureSection, DoctorAlert, TableDefinition,
    DiagramDefinition, DiagramElement, ExamQuestion
)
from visualizer import generate_diagram
from pdf_builder import PDFStudyGuideBuilder
from pipeline import process_lecture
from mock_generator import get_sample_bilingual_lecture_guide
from config import ASSETS_DIR, OUTPUT_DIR
import pypdf

class TestLectureAISuite(unittest.TestCase):

    def test_01_models_validation(self):
        """Test Pydantic model validation and serialization."""
        guide = get_sample_bilingual_lecture_guide()
        self.assertIn("Operating Systems", guide.course_name)
        self.assertEqual(len(guide.sections), 2)
        self.assertTrue(len(guide.exam_readiness_section) >= 3)
        dump = guide.model_dump()
        self.assertIn("sections", dump)
        self.assertIn("exam_readiness_section", dump)

    def test_02_visualizer_diagrams(self):
        """Test rendering of flowcharts, comparison charts, and process cycles."""
        # 1. Flowchart
        flow_diag = DiagramDefinition(
            diagram_id="test_flow_diag",
            title="3-Tier Software Architecture",
            diagram_type="FLOWCHART",
            elements=[
                DiagramElement(label="Client Tier", description="Web Browser / Mobile App"),
                DiagramElement(label="Logic Tier", description="FastAPI REST Services"),
                DiagramElement(label="Data Tier", description="PostgreSQL Database")
            ],
            caption="Standard three-tier software design."
        )
        p1 = generate_diagram(flow_diag, ASSETS_DIR)
        self.assertTrue(p1.exists())
        self.assertGreater(p1.stat().st_size, 1000)

        # 2. Cycle
        cycle_diag = DiagramDefinition(
            diagram_id="test_cycle_diag",
            title="Agile Sprint Lifecycle",
            diagram_type="PROCESS_CYCLE",
            elements=[
                DiagramElement(label="Planning"),
                DiagramElement(label="Design"),
                DiagramElement(label="Development"),
                DiagramElement(label="Testing"),
                DiagramElement(label="Deployment")
            ],
            caption="Iterative software engineering sprint loop."
        )
        p2 = generate_diagram(cycle_diag, ASSETS_DIR)
        self.assertTrue(p2.exists())
        self.assertGreater(p2.stat().st_size, 1000)

        # 3. Bar Chart
        bar_diag = DiagramDefinition(
            diagram_id="test_bar_diag",
            title="Algorithm Latency Benchmark (ms)",
            diagram_type="COMPARISON_BAR",
            elements=[
                DiagramElement(label="QuickSort", value=12.4),
                DiagramElement(label="MergeSort", value=15.1),
                DiagramElement(label="BubbleSort", value=145.8)
            ],
            caption="Execution time comparison in milliseconds."
        )
        p3 = generate_diagram(bar_diag, ASSETS_DIR)
        self.assertTrue(p3.exists())
        self.assertGreater(p3.stat().st_size, 1000)

    def test_03_pdf_builder(self):
        """Test PDF compilation and page count integrity."""
        guide = get_sample_bilingual_lecture_guide()
        builder = PDFStudyGuideBuilder(guide, output_filename="UnitTest_Guide.pdf")
        pdf_path = builder.build()
        
        self.assertTrue(pdf_path.exists())
        self.assertGreater(pdf_path.stat().st_size, 10000)
        
        # Verify with pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        self.assertGreaterEqual(len(reader.pages), 3)

    def test_04_pipeline_simulation(self):
        """Test complete pipeline orchestration in demo mode."""
        result = process_lecture(
            use_sample_demo=True,
            custom_output_filename="Pipeline_Test_Guide.pdf"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["sections_count"], 2)
        self.assertEqual(result["alerts_count"], 2)
        self.assertGreaterEqual(result["exam_questions_count"], 3)
        self.assertTrue(result["verification_passed"])
        self.assertEqual(result["contradictions_detected"], 0)
        self.assertTrue(Path(result["pdf_path"]).exists())

    def test_05_verification_audit_and_reconciliation(self):
        """Test contradiction reporting, self-correction schemas, and PDF certificate generation."""
        from models import ContradictionItem, VerificationAuditReport

        # 1. Create a guide with resolved contradictions
        guide = get_sample_bilingual_lecture_guide()
        contradiction = ContradictionItem(
            section_title="Operating Conditions",
            guide_statement="Process priority was initially stated as descending from 0 to 10.",
            audio_truth="Professor stated: 'Priority values in this system are inverted: 0 is highest priority'.",
            correction_applied="Inverted priority hierarchy to establish 0 as the highest priority level."
        )
        report = VerificationAuditReport(
            audit_passed=True,
            contradictions_detected=1,
            contradictions=[contradiction],
            overall_fidelity_summary="Audit reconciled 1 priority order contradiction with the lecture audio.",
            verified_at="2026-09-22T01:55:00+03:00"
        )
        guide.verification_report = report

        # 2. Build PDF with the verification report embedded
        builder = PDFStudyGuideBuilder(guide, output_filename="Verified_Audit_Test_Guide.pdf")
        pdf_path = builder.build()
        self.assertTrue(pdf_path.exists())
        self.assertGreater(pdf_path.stat().st_size, 10000)

        # 3. Read back PDF and confirm it contains the verified audit certificate
        reader = pypdf.PdfReader(str(pdf_path))
        page_texts = "".join([p.extract_text() or "" for p in reader.pages])
        self.assertIn("AUDIO FIDELITY AUDIT", page_texts)
        self.assertIn("Priority values in this system are inverted", page_texts)

    def test_06_lecture_notes_and_slide_slicing(self):
        """Test PDF slicing helper, notes metadata in pipeline, and dual-source verification certificate."""
        from pedagogy_engine import slice_pdf_pages
        from reportlab.pdfgen import canvas
        from config import UPLOAD_DIR

        # 1. Create a temporary 5-page dummy lecture slide PDF
        dummy_slides_path = UPLOAD_DIR / "test_dummy_lecture_deck.pdf"
        c = canvas.Canvas(str(dummy_slides_path))
        for p in range(1, 6):
            c.drawString(100, 700, f"Lecture Slide Page {p}: Operating Systems Topics")
            c.showPage()
        c.save()
        self.assertTrue(dummy_slides_path.exists())

        # 2. Test slice_pdf_pages with range 2 to 4
        sliced_path, label = slice_pdf_pages(dummy_slides_path, start_page=2, end_page=4, output_dir=UPLOAD_DIR)
        self.assertTrue(sliced_path.exists())
        self.assertEqual(label, "Slides 2–4 of 5")
        sliced_reader = pypdf.PdfReader(str(sliced_path))
        self.assertEqual(len(sliced_reader.pages), 3)

        # 3. Test slice_pdf_pages with full range (no start or end)
        full_path, full_label = slice_pdf_pages(dummy_slides_path, start_page=None, end_page=None)
        self.assertEqual(full_path, dummy_slides_path)
        self.assertIn("Full slide deck", full_label)

        # 4. Test pipeline simulation with lecture notes & slide bounds
        res = process_lecture(
            use_sample_demo=True,
            notes_path=dummy_slides_path,
            start_slide=2,
            end_slide=4,
            custom_output_filename="Notes_Integrated_Guide.pdf"
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["notes_audited"])
        self.assertIn("Slides 2–4", res["notes_reference"])
        self.assertTrue(Path(res["pdf_path"]).exists())

        # 5. Verify the compiled PDF contains lecture notes references & dual-source certificate
        reader = pypdf.PdfReader(res["pdf_path"])
        full_text = "".join([p.extract_text() or "" for p in reader.pages])
        self.assertIn("Lecture Notes / Slides:", full_text)
        self.assertIn("AUDIO & SLIDES FIDELITY", full_text)

    def test_07_record_deletion_and_math_healing(self):
        """Test math defect auto-healing and record deletion API."""
        import asyncio
        import json
        import uuid
        from pdf_builder import format_math_in_text
        from app import delete_history_entry, HISTORY_FILE, OUTPUT_DIR

        # 1. Verify math typography defect auto-healer
        corrupted_math = "V_O = ∆ rac{1}{2π} ∫_0^π V_m ∂∆∁(ω t) d(ω t)"
        healed = format_math_in_text(corrupted_math)
        self.assertNotIn("∆ rac", healed)
        self.assertNotIn("\u2201", healed)  # No complement tofu character
        self.assertIn("sin", healed)
        self.assertIn("&pi;", healed)
        self.assertIn("&omega;", healed)

        # 2. Verify record and file deletion
        test_id = f"test-del-{uuid.uuid4().hex[:8]}"
        dummy_pdf_name = f"Test_Delete_Target_{test_id}.pdf"
        dummy_pdf_file = OUTPUT_DIR / dummy_pdf_name
        dummy_pdf_file.write_text("Dummy PDF content for deletion test", encoding="utf-8")
        self.assertTrue(dummy_pdf_file.exists())

        # Seed dummy record into history
        history = []
        if HISTORY_FILE.exists():
            try:
                history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                history = []
        
        history.append({
            "id": test_id,
            "created_at": "2026-09-22T20:00:00Z",
            "source_name": "test_del.m4a",
            "course_name": "Test Delete Course",
            "result": {
                "pdf_filename": dummy_pdf_name,
                "pdf_title": "Test Delete PDF",
                "summary": "Deletion unit test"
            }
        })
        HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

        # Execute deletion endpoint logic
        del_res = asyncio.run(delete_history_entry(test_id))
        self.assertTrue(del_res["success"])
        self.assertTrue(del_res["pdf_deleted"])
        self.assertFalse(dummy_pdf_file.exists())

        # Verify record was purged from history file
        updated_history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        self.assertFalse(any(item["id"] == test_id for item in updated_history))

    def test_08_selective_folder_materials_and_sections(self):
        """Test selective lecture materials, AT section lecture note inclusion, and continued note discovery."""
        from link_downloader import search_session_in_folder, download_selected_folder_items
        import tempfile
        import shutil

        # 1. Create a simulated course folder with lectures, sections, and multiple slide decks
        with tempfile.TemporaryDirectory() as temp_dir:
            course_dir = Path(temp_dir) / "Biomedical Instrumentation"
            rec_lec_dir = course_dir / "record (Biomedical Instrumentation)" / "lectures"
            rec_sec_dir = course_dir / "record (Biomedical Instrumentation)" / "sections"
            lec_slides_dir = course_dir / "lectures"
            rec_lec_dir.mkdir(parents=True)
            rec_sec_dir.mkdir(parents=True)
            lec_slides_dir.mkdir(parents=True)

            # Create lecture files
            (rec_lec_dir / "lecture 1 bioinst.m4a").write_text("dummy audio 1", encoding="utf-8")
            (rec_lec_dir / "lecture 2 bioinst.m4a").write_text("dummy audio 2", encoding="utf-8")
            (rec_sec_dir / "section 1 bioinst.m4a").write_text("dummy section audio", encoding="utf-8")
            (lec_slides_dir / "BIO 301 Electrodes.pdf").write_text("dummy slide 1", encoding="utf-8")
            (lec_slides_dir / "Amplifiers and CMRR.pdf").write_text("dummy slide 2", encoding="utf-8")

            # 2. Test searching for Lecture 1
            res_lec = search_session_in_folder(str(course_dir), "Lecture 1")
            self.assertTrue(res_lec["success"])
            self.assertEqual(len(res_lec["records"]), 1)
            self.assertEqual(res_lec["records"][0]["name"], "lecture 1 bioinst.m4a")
            self.assertTrue(len(res_lec["all_course_notes"]) >= 2)
            self.assertFalse(res_lec["is_section_query"])

            # 3. Test searching for Section 1 (AT section mode)
            res_sec = search_session_in_folder(str(course_dir), "Section 1")
            self.assertTrue(res_sec["success"])
            self.assertEqual(len(res_sec["records"]), 1)
            self.assertEqual(res_sec["records"][0]["name"], "section 1 bioinst.m4a")
            self.assertTrue(res_sec["is_section_query"])
            # In section mode, all lecture notes/slides are provided for AT reference
            self.assertTrue(len(res_sec["notes"]) >= 2)
            self.assertTrue(any("Electrodes" in n["name"] for n in res_sec["notes"]))
            self.assertTrue(any("Amplifiers" in n["name"] for n in res_sec["notes"]))

            # 4. Test selecting only 1 of the 2 notes (User choice verification)
            chosen_note = [n for n in res_sec["notes"] if "Electrodes" in n["name"]]
            resolved = download_selected_folder_items(chosen_note, Path(temp_dir) / "dl", "notes")
            self.assertEqual(len(resolved), 1)
            self.assertEqual(resolved[0][1], "BIO 301 Electrodes.pdf")
            self.assertTrue(resolved[0][0].exists())

    def test_09_physics_waveform_and_collision_free_rendering(self):
        """Test accurate waveform rendering, two-panel card layouts, and zero-collision routing."""
        # 1. Shockley relaxation oscillator sawtooth waveform
        shockley_diag = DiagramDefinition(
            diagram_id="test_suite_shockley",
            title="Shockley Diode Relaxation Oscillator Circuit and Sawtooth Waveform",
            diagram_type="PROCESS_CYCLE",
            elements=[
                DiagramElement(label="1. RC Charging Phase", description="Capacitor charges exponentially through resistor R toward DC supply voltage"),
                DiagramElement(label="2. Threshold Detection at V_BO", description="Capacitor voltage reaches Shockley breakover voltage V_BO"),
                DiagramElement(label="3. Regenerative Latching", description="Shockley diode abruptly turns on, providing a low-resistance discharge path"),
                DiagramElement(label="4. Rapid Discharge & Extinction", description="Capacitor dumps charge rapidly until current falls below holding current I_H, turning diode off")
            ],
            caption="Cyclic operation of a Shockley diode relaxation oscillator."
        )
        p1 = generate_diagram(shockley_diag, ASSETS_DIR)
        self.assertTrue(p1.exists())
        self.assertGreater(p1.stat().st_size, 5000)

        # 2. Double Zener waveform clipper
        clipper_diag = DiagramDefinition(
            diagram_id="test_suite_clipper",
            title="Double Zener Waveform Clipper Circuit and Waveforms",
            diagram_type="FLOWCHART",
            elements=[
                DiagramElement(label="Input AC Sine Wave (v_i)", description="Continuous sinusoidal input signal alternating between +Vm and -Vm"),
                DiagramElement(label="Series Resistor R", description="Limits peak current through the clipping network"),
                DiagramElement(label="Back-to-Back Zeners (Z1 & Z2)", description="Z1 forward conducts while Z2 breaks down on positive cycle; vice-versa on negative cycle"),
                DiagramElement(label="Clipped Output Waveform (v_o)", description="Truncated wave clamped at +(V_Z2 + 0.7 V) and -(V_Z1 + 0.7 V)")
            ],
            caption="Double Zener clipper circuit truncating positive and negative peaks."
        )
        p2 = generate_diagram(clipper_diag, ASSETS_DIR)
        self.assertTrue(p2.exists())
        self.assertGreater(p2.stat().st_size, 5000)

        # 3. Flowchart with conduction path (must not be hijacked by rectifier waveforms)
        bridge_diag = DiagramDefinition(
            diagram_id="test_suite_bridge_paths",
            title="Full-Wave Bridge Rectifier Current Conduction Paths",
            diagram_type="FLOWCHART",
            elements=[
                DiagramElement(label="Positive Half-Cycle (v_s > 0)", description="Top terminal positive: current flows through D1 -> Load Resistor R -> D2"),
                DiagramElement(label="Negative Half-Cycle (v_s < 0)", description="Bottom terminal positive: current flows through D3 -> Load Resistor R -> D4"),
                DiagramElement(label="Load Resistor Voltage", description="Current enters the positive terminal of R in both half-cycles, producing a strictly unipolar DC output")
            ],
            caption="Current routes through diagonal diode pairs during opposite AC half-cycles."
        )
        p3 = generate_diagram(bridge_diag, ASSETS_DIR)
        self.assertTrue(p3.exists())
        self.assertGreater(p3.stat().st_size, 5000)

    def test_10_no_tofu_glyphs_regression(self):
        """Regression test for Item 1: ensure zero tofu boxes ('□', '\\x00', '\\ufffd') in compiled PDF."""
        guide = get_sample_bilingual_lecture_guide()
        builder = PDFStudyGuideBuilder(guide, output_filename="Tofu_Glyph_Regression_Guide.pdf")
        pdf_path = builder.build()
        self.assertTrue(pdf_path.exists())

        reader = pypdf.PdfReader(str(pdf_path))
        full_text = ""
        for i, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            full_text += f"\n--- Page {i+1} ---\n" + txt
            self.assertNotIn("□", txt, f"Tofu box '□' found on page {i+1}")
            self.assertNotIn("\x00", txt, f"Null/.notdef glyph found on page {i+1}")
            self.assertNotIn("\ufffd", txt, f"Replacement character found on page {i+1}")
        
        # Explicit check for headings and callouts
        self.assertIn("Equation 1:", full_text)
        self.assertNotIn("□ Equation 1:", full_text)
        self.assertIn("Exam Readiness: How Questions Will Come in Exams", full_text)
        self.assertIn("Model Answer / Solution:", full_text)

    def test_11_no_component_n_labels_regression(self):
        """Regression test for Item 6 & 7: ensure no 'Component N' labels and validate Three Pillars node count."""
        import re
        from visualizer import render_system_block_diagram, validate_and_normalize_diagram
        import matplotlib.pyplot as plt

        # 1. Test Block Diagram with only 5 elements (should NOT generate 'Component 6')
        block_diag = DiagramDefinition(
            diagram_id="test_regression_block_diag",
            title="General Power Electronic System Architecture",
            diagram_type="SYSTEM_BLOCK_DIAGRAM",
            elements=[
                DiagramElement(label="Power Source", description="AC Utility Grid"),
                DiagramElement(label="Power Electronic Converter", description="Solid-State Switches"),
                DiagramElement(label="Electrical Load", description="Motor / Battery"),
                DiagramElement(label="Sensing & Feedback", description="Current & Voltage Transducers"),
                DiagramElement(label="Controller / DSP", description="Microcontroller PWM Logic"),
            ],
            caption="Six-block closed-loop power conversion architecture."
        )

        out_path = ASSETS_DIR / "test_regression_block.png"
        res_path = render_system_block_diagram(block_diag, out_path)
        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 1000)

        # Also test with explicit 'Component 6' label in elements - must be sanitized
        block_diag_comp6 = DiagramDefinition(
            diagram_id="test_regression_block_comp6",
            title="General Power Electronic System Architecture",
            diagram_type="SYSTEM_BLOCK_DIAGRAM",
            elements=[
                DiagramElement(label="Power Source", description="AC Utility Grid"),
                DiagramElement(label="Power Electronic Converter", description="Solid-State Switches"),
                DiagramElement(label="Electrical Load", description="Motor / Battery"),
                DiagramElement(label="Sensing & Feedback", description="Current & Voltage Transducers"),
                DiagramElement(label="Controller / DSP", description="Microcontroller PWM Logic"),
                DiagramElement(label="Component 6", description="Actuator / Driver"),
            ],
            caption="Six-block architecture testing Component 6 sanitization."
        )
        res_comp6 = render_system_block_diagram(block_diag_comp6, ASSETS_DIR / "test_comp6.png")
        self.assertTrue(res_comp6.exists())

        # 2. Test Three Pillars normalization (Item 7)
        pillars_diag = DiagramDefinition(
            diagram_id="test_regression_pillars",
            title="The Three Pillars of Power Electronics",
            diagram_type="CONCEPT_MAP",
            elements=[
                DiagramElement(label="Power Systems", description="Generation, transmission, utilities"),
                DiagramElement(label="Solid-State Electronics", description="Semiconductor switches, diodes"),
                DiagramElement(label="Power Electronics", description="Duplicate center concept"),
                DiagramElement(label="Control Theory", description="Feedback loops, stability, PWM")
            ],
            caption="The three interdisciplinary disciplines underpinning power electronics."
        )
        norm_diag = validate_and_normalize_diagram(pillars_diag)
        self.assertEqual(len(norm_diag.elements), 3, "Three Pillars must normalize to exactly 3 outer nodes")
        labels = [e.label for e in norm_diag.elements]
        self.assertEqual(labels, ["Power", "Electronics", "Control"])

    def test_12_delete_history_endpoint_success_and_failure(self):
        """Regression test for Part 1B: Delete endpoint returns 200 on success and 404 on failure."""
        import json
        import uuid
        from fastapi.testclient import TestClient
        from app import app, HISTORY_FILE, load_history

        client = TestClient(app)
        test_id = f"test-delete-{uuid.uuid4()}"

        # 1. Setup temporary entry in history
        history = [x for x in load_history() if not str(x.get("id", "")).startswith("test-delete-")]
        history.append({
            "id": test_id,
            "source_name": "Regression Test Delete Lecture",
            "created_at": "2026-10-07T12:00:00",
            "study_mode": "detailed",
            "result": {"lecture_title": "Regression Test Delete Lecture", "pdf_filename": "non_existent_test.pdf"}
        })
        HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

        # 2. Test successful deletion (HTTP 200, success: True)
        res_del = client.delete(f"/api/history/{test_id}")
        self.assertEqual(res_del.status_code, 200)
        data_del = res_del.json()
        self.assertTrue(data_del.get("success"), "Expected success: True on successful deletion")
        self.assertEqual(data_del.get("id"), test_id)

        # Confirm removed from local file
        updated_history = load_history()
        self.assertNotIn(test_id, [x.get("id") for x in updated_history])

        # 3. Test failure case (deleting again should return HTTP 404 with friendly detail)
        res_del_again = client.delete(f"/api/history/{test_id}")
        self.assertEqual(res_del_again.status_code, 404)
        err_data = res_del_again.json()
        self.assertIn("detail", err_data)
        self.assertEqual(err_data["detail"], "History entry not found")

    def test_13_demo_endpoint_and_job_lifecycle(self):
        """Regression test for Part 1B: Demo generation returns consistent 200 response and job lifecycle."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)

        # 1. Start demo generation
        res = client.post("/api/process_audio", data={"demo_mode": "true", "study_mode": "detailed"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("job_id", data)
        job_id = data["job_id"]

        # 2. Status polling
        stat_res = client.get(f"/api/status/{job_id}")
        self.assertEqual(stat_res.status_code, 200)
        stat_data = stat_res.json()
        self.assertIn(stat_data.get("status"), ["pending", "running", "completed"])

        # 3. Status 404 for invalid job
        bad_stat = client.get("/api/status/non-existent-job-404")
        self.assertEqual(bad_stat.status_code, 404)

        # 4. Cancel 404 for invalid job
        bad_cancel = client.post("/api/cancel/non-existent-job-404")
        self.assertEqual(bad_cancel.status_code, 404)

    def test_14_folder_mode_ignores_manual_uploads(self):
        """Regression test for Part 1: Unified mixed intake replaces old folder-mode lock; manual uploads and folder items work together."""
        from fastapi.testclient import TestClient
        from app import app
        import tempfile
        import io
        import json
        from unittest.mock import patch

        client = TestClient(app)

        # 1. Posting without any audio input and without demo mode returns clear 400
        res_empty = client.post("/api/process_audio", data={})
        self.assertEqual(res_empty.status_code, 400)
        self.assertIn("No lecture recording provided", res_empty.json()["detail"])

        # 2. In unified mixed intake, course folder items and manual computer uploads can be combined
        # (the old folder-mode lock that discarded manual uploads is completely eliminated)
        with tempfile.TemporaryDirectory() as tmp_dir:
            course_dir = Path(tmp_dir) / "Fall 2026" / "Biomaterials"
            course_dir.mkdir(parents=True, exist_ok=True)
            folder_slide_file = course_dir / "Biomaterials_Deck.pdf"
            folder_slide_file.write_bytes(b"%PDF-1.4 folder dummy slide content")

            dummy_audio_bytes = io.BytesIO(b"dummy mp3 audio data")
            dummy_audio_bytes.name = "part1_recording.mp3"

            sources_payload = json.dumps([
                {"id": "rec_upload", "kind": "upload", "role": "audio", "order": 0, "display_name": "part1_recording.mp3"},
                {"id": "notes_folder", "kind": "folder", "role": "notes", "order": 0, "local_path": str(folder_slide_file), "display_name": "Biomaterials_Deck.pdf"}
            ])

            with patch("link_downloader.get_configured_courses_roots", return_value=[Path(tmp_dir)]):
                with patch("app.process_lecture") as mock_pipeline:
                    mock_pipeline.return_value = {
                        "success": True,
                        "pdf_path": str(Path("output_pdfs") / "mock.pdf"),
                        "pdf_filename": "mock.pdf",
                        "lecture_title": "Biomaterials",
                        "summary": "Mock summary",
                        "contradictions": [],
                        "notes_audited": True,
                        "notes_reference": "Full slide deck",
                        "audio_fidelity_score": 100,
                    }
                    res_mixed = client.post(
                        "/api/process_audio",
                        data={"sources": sources_payload, "api_key": "mock_api_key"},
                        files={"file_rec_upload": ("part1_recording.mp3", dummy_audio_bytes, "audio/mpeg")}
                    )
                    self.assertEqual(res_mixed.status_code, 200)
                    self.assertTrue(res_mixed.json().get("success"))
                    self.assertTrue(mock_pipeline.called)
                    # Verify both manual upload audio and course folder notes were passed to pipeline
                    call_kwargs = mock_pipeline.call_args.kwargs
                    self.assertEqual(len(call_kwargs["audio_path"]), 1)
                    self.assertEqual(len(call_kwargs["notes_path"]), 1)
                    self.assertEqual(call_kwargs["notes_path"][0].name, "Biomaterials_Deck.pdf")

    def test_15_pdf_corrupt_and_encrypted_error_handling(self):
        """Regression test for corrupt and encrypted PDFs raising user-friendly errors."""
        import tempfile
        from pedagogy_engine import slice_pdf_pages

        # Test corrupt PDF raises descriptive ValueError
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"CORRUPTED BYTES - NOT A VALID PDF HEADER")
            corrupt_path = Path(f.name)

        try:
            with self.assertRaises(ValueError) as ctx:
                slice_pdf_pages(corrupt_path, start_page=1, end_page=2)
            self.assertIn("corrupt", str(ctx.exception).lower())
        finally:
            corrupt_path.unlink(missing_ok=True)

    def test_16_demo_cleanliness_and_audit_badge_regression(self):
        """Regression test for Item 1: demo output has no tofu boxes, no Amdahl's Law, correct Banker's, and DEMO badge."""
        import pypdf
        from mock_generator import get_sample_bilingual_lecture_guide
        from pdf_builder import PDFStudyGuideBuilder, ARABIC_REGEX

        guide = get_sample_bilingual_lecture_guide()

        # 1. Verify Amdahl's Law is absent
        for s in guide.sections:
            self.assertNotIn("amdahl", s.topic_title.lower())
            self.assertNotIn("amdahl", s.detailed_explanation.lower())
            for bp in s.key_bullet_points:
                self.assertNotIn("amdahl", bp.lower())
            for f in getattr(s, "formulas", []):
                self.assertNotIn("amdahl", f.formula_name.lower())

        # 2. Verify Banker's algorithm step 1 arithmetic
        q3 = guide.exam_readiness_section[2]
        self.assertIn("releases its 2 allocated units", q3.correct_answer)
        self.assertIn("New Available = 3 + 2 = 5 units", q3.correct_answer)

        # 3. Verify clean doctor hints without Arabic or garbled quotes
        for q in guide.exam_readiness_section:
            if q.doctor_hint:
                self.assertFalse(bool(ARABIC_REGEX.search(q.doctor_hint)), f"Arabic found in hint: {q.doctor_hint}")
                self.assertNotIn("The doctor warned: ' '", q.doctor_hint)
                self.assertNotIn("Doctor stated: ' Banker's algorithm !", q.doctor_hint)

        # 4. Build PDF and verify page text
        builder = PDFStudyGuideBuilder(guide, output_filename="Verified_Demo_Cleanliness.pdf")
        pdf_path = builder.build()
        self.assertTrue(pdf_path.exists())

        reader = pypdf.PdfReader(str(pdf_path))
        self.assertGreaterEqual(len(reader.pages), 7, "Demo guide should have at least 7 pages")

        for idx, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            # Zero tofu box glyphs across all pages
            self.assertNotIn("□", txt, f"Tofu box '□' found on page {idx + 1}")
            self.assertNotIn("\ufffd", txt, f"Replacement character found on page {idx + 1}")
            self.assertNotIn("\x00", txt, f"Null glyph found on page {idx + 1}")

        # Page 1 checks
        page1_txt = reader.pages[0].extract_text() or ""
        self.assertIn("DEMO MODE", page1_txt)
        self.assertIn("SIMULATION", page1_txt)
        self.assertIn("DEMO MODE: SIMULATED", page1_txt)
        # Must not display unbadged audit
        self.assertNotIn("AUDIO FIDELITY & CONTRADICTION AUDIT: 100% VERIFIED", page1_txt)

        # Page 2 & 7 checks
        page2_txt = reader.pages[1].extract_text() or ""
        self.assertNotIn("amdahl", page2_txt.lower())

        page7_txt = reader.pages[6].extract_text() or ""
        self.assertIn("releases its 2 allocated units", page7_txt)
        self.assertIn("3 + 2 = 5 units", page7_txt)

        # Clean up temporary test PDF
        try:
            pdf_path.unlink(missing_ok=True)
        except OSError:
            pass

    def test_17_config_model_and_api_key_privacy(self):
        """Regression test for Item 2 & Item 3: model single source of truth and API key never leaked."""
        import os
        from fastapi.testclient import TestClient
        from app import app
        import config

        client = TestClient(app)

        # 1. Config endpoint reports exactly config.DEFAULT_MODEL
        resp = client.get("/api/config")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("model"), config.DEFAULT_MODEL)
        self.assertEqual(config.DEFAULT_MODEL, "gemini-3.8-flash")

        # 2. Response never contains 'masked_key'
        self.assertNotIn("masked_key", data)

        # 3. Even with a simulated API key set, no characters of the key leak into the response
        test_key = "AIzA_SECRET_TEST_KEY_987654321_XYZZY"
        old_key = os.environ.get("GEMINI_API_KEY")
        try:
            os.environ["GEMINI_API_KEY"] = test_key
            resp_keyed = client.get("/api/config")
            self.assertEqual(resp_keyed.status_code, 200)
            data_keyed = resp_keyed.json()
            self.assertTrue(data_keyed.get("has_key"))
            self.assertNotIn("masked_key", data_keyed)
            # Ensure not even a 4-char fragment of the key appears in any value or the response text
            self.assertNotIn("AIzA", resp_keyed.text)
            self.assertNotIn("XYZZY", resp_keyed.text)
            self.assertNotIn("SECRET", resp_keyed.text)
            self.assertNotIn("987654321", resp_keyed.text)
        finally:
            if old_key is not None:
                os.environ["GEMINI_API_KEY"] = old_key
            else:
                os.environ.pop("GEMINI_API_KEY", None)

    def test_18_delete_flow_removes_file_and_updates_history(self):
        """Regression test for Item 5b: delete flow removes throwaway PDF from disk and updates history."""
        from fastapi.testclient import TestClient
        from app import app, HISTORY_FILE, load_history
        from config import OUTPUT_DIR
        import json
        import uuid

        client = TestClient(app)

        # Create throwaway test file in OUTPUT_DIR
        test_pdf_name = f"test_throwaway_delete_{uuid.uuid4().hex[:8]}.pdf"
        test_pdf_path = OUTPUT_DIR / test_pdf_name
        test_pdf_path.write_bytes(b"%PDF-1.4 throwaway test content")
        self.assertTrue(test_pdf_path.exists())

        test_entry_id = str(uuid.uuid4())
        history = load_history()
        history.insert(0, {
            "id": test_entry_id,
            "created_at": "2026-10-08T00:00:00+00:00",
            "source_name": "Test Throwaway",
            "study_mode": "detailed",
            "result": {
                "pdf_filename": test_pdf_name,
                "lecture_title": "Test Throwaway Title"
            }
        })
        HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

        try:
            # Send DELETE request
            del_resp = client.delete(f"/api/history/{test_entry_id}")
            self.assertEqual(del_resp.status_code, 200)
            del_data = del_resp.json()
            self.assertTrue(del_data.get("success"))
            self.assertTrue(del_data.get("pdf_deleted"))

            # Verify PDF file unlinked from disk
            self.assertFalse(test_pdf_path.exists(), "Throwaway PDF file should have been deleted from disk")

            # Verify entry no longer in history
            updated_hist = load_history()
            self.assertNotIn(test_entry_id, [h.get("id") for h in updated_hist])
        finally:
            # Cleanup if anything failed
            test_pdf_path.unlink(missing_ok=True)

    def test_19_download_filename_directory_escape(self):
        """Regression test for Issue 1: Malicious Content-Disposition filename cannot write outside target directory."""
        from link_downloader import download_from_link
        import tempfile
        import uuid
        from unittest.mock import patch, MagicMock

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            target_dir = Path(tmp_dir_str)

            # Simulated responses with malicious directory traversal filenames
            malicious_headers = [
                'attachment; filename="../../escape_test.mp3"',
                'attachment; filename="..\\..\\windows_escape.mp3"',
                'attachment; filename="/tmp/absolute_escape.mp3"',
                'attachment; filename="....//....//deep_escape.mp3"',
                'attachment; filename="../../../etc/passwd"',
            ]

            for header_val in malicious_headers:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.headers = {"content-disposition": header_val}
                mock_resp.iter_content.return_value = [b"dummy audio binary data"]
                mock_resp.__enter__.return_value = mock_resp
                mock_resp.__exit__.return_value = None

                with patch("requests.Session.get", return_value=mock_resp):
                    final_path, orig_name = download_from_link(
                        url="https://example.com/audio/sample.mp3",
                        target_dir=target_dir,
                        expected_type="audio"
                    )
                    # The saved file must reside strictly inside target_dir
                    self.assertTrue(final_path.exists())
                    self.assertEqual(final_path.resolve().parent, target_dir.resolve())
                    self.assertTrue(target_dir.resolve() in final_path.resolve().parents)
                    # Must not contain path separators in orig_name
                    self.assertNotIn("/", orig_name)
                    self.assertNotIn("\\", orig_name)

            # Normal filename must still download cleanly
            normal_resp = MagicMock()
            normal_resp.status_code = 200
            normal_resp.headers = {"content-disposition": 'attachment; filename="legit_lecture.mp3"'}
            normal_resp.iter_content.return_value = [b"legit data"]
            normal_resp.__enter__.return_value = normal_resp
            normal_resp.__exit__.return_value = None

            with patch("requests.Session.get", return_value=normal_resp):
                final_path, orig_name = download_from_link(
                    url="https://example.com/audio/legit.mp3",
                    target_dir=target_dir,
                    expected_type="audio"
                )
                self.assertTrue(final_path.exists())
                self.assertEqual(final_path.resolve().parent, target_dir.resolve())
                self.assertEqual(orig_name, "legit_lecture.mp3")

    def test_20_cancellation_stops_job_and_prevents_history_writes(self):
        """Regression test for Issue 2: Cancelling a running job stops subsequent processing and prevents history writes."""
        from fastapi.testclient import TestClient
        from app import (
            app, jobs, cancel_events, is_job_cancelled,
            background_process, load_history
        )
        import uuid
        import threading
        from unittest.mock import patch

        client = TestClient(app)

        # 1. Test cancel endpoint and cancel signal
        job_id = f"test_cancel_{uuid.uuid4().hex[:8]}"
        jobs[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "progress": 10,
            "status_message": "Starting processing",
            "result": None,
            "error": None,
            "cancelled": False
        }
        cancel_events[job_id] = threading.Event()

        self.assertFalse(is_job_cancelled(job_id))
        resp = client.post(f"/api/cancel/{job_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(is_job_cancelled(job_id))
        self.assertEqual(jobs[job_id]["status"], "cancelled")
        self.assertTrue(cancel_events[job_id].is_set())

        # 2. Test blocking fake process_lecture: cancel while blocked, release, assert stopped cleanly
        bg_job_id = f"test_bg_cancel_{uuid.uuid4().hex[:8]}"
        jobs[bg_job_id] = {
            "job_id": bg_job_id,
            "status": "queued",
            "progress": 5,
            "status_message": "Queued",
            "result": None,
            "error": None,
            "cancelled": False
        }
        cancel_events[bg_job_id] = threading.Event()

        blocked_event = threading.Event()
        release_event = threading.Event()

        def fake_blocking_process_lecture(*args, **kwargs):
            blocked_event.set()
            release_event.wait(timeout=5.0)
            return {
                "study_guide": get_sample_bilingual_lecture_guide(),
                "pdf_path": str(ASSETS_DIR / "sample.pdf"),
                "audit_report": None
            }

        initial_history_count = len(load_history())

        worker_thread = threading.Thread(
            target=background_process,
            kwargs={
                "job_id": bg_job_id,
                "audio_paths": [Path("dummy.mp3")],
                "notes_paths": None,
                "source_name": "Cancelled Test Lecture",
                "study_mode": "detailed",
                "is_demo": True
            }
        )

        with patch("app.process_lecture", side_effect=fake_blocking_process_lecture):
            worker_thread.start()
            self.assertTrue(blocked_event.wait(timeout=3.0), "Worker did not reach blocking point")
            cancel_resp = client.post(f"/api/cancel/{bg_job_id}")
            self.assertEqual(cancel_resp.status_code, 200)
            release_event.set()
            worker_thread.join(timeout=5.0)

        # Assert job remains cancelled, not overwritten with 'completed'
        self.assertEqual(jobs[bg_job_id]["status"], "cancelled")
        # Assert no history entry was written
        current_history = load_history()
        self.assertEqual(len(current_history), initial_history_count)
        self.assertNotIn(bg_job_id, [h.get("id") for h in current_history])

    def test_21_verification_api_failure_represented_as_unavailable(self):
        """Regression test for Issue 3: Verification API failure sets audit_passed=False and PDF does not say 100% Verified."""
        from pedagogy_engine import verify_and_reconcile_study_guide
        from mock_generator import get_sample_bilingual_lecture_guide
        from pdf_builder import PDFStudyGuideBuilder
        from unittest.mock import MagicMock
        import pypdf

        draft_guide = get_sample_bilingual_lecture_guide()
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("503 Service Unavailable")

        # 1. verify_and_reconcile_study_guide returns fallback with audit_passed=False
        reconciled_guide, report = verify_and_reconcile_study_guide(
            client=mock_client,
            audio_file=MagicMock(),
            notes_file=None,
            notes_reference=None,
            guide=draft_guide,
            model="gemini-3.8-flash"
        )
        self.assertFalse(report.audit_passed)
        self.assertIn("unavailable", report.overall_fidelity_summary.lower())

        # 2. PDF generation must reflect unavailable audit and NOT claim 100% VERIFIED
        reconciled_guide.is_demo = False
        reconciled_guide.verification_report = report
        test_out_pdf = "Test_Audit_Failed_Regression.pdf"
        builder = PDFStudyGuideBuilder(reconciled_guide, output_filename=test_out_pdf)
        pdf_path = builder.build()
        try:
            self.assertTrue(pdf_path.exists())
            reader = pypdf.PdfReader(str(pdf_path))
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() or ""

            self.assertIn("UNAVAILABLE", full_text.upper())
            self.assertNotIn("100% VERIFIED", full_text)
        finally:
            pdf_path.unlink(missing_ok=True)

    def test_22_standalone_auditor_cleans_up_uploaded_media(self):
        """Regression test for Issue 4: verify_audio_fidelity deletes uploaded files on both success and exception."""
        from unittest.mock import patch, MagicMock
        import verify_audio_fidelity
        import tempfile
        import io

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            fake_audio = tmp_path / "fake_audio.mp3"
            fake_audio.write_bytes(b"dummy audio")
            fake_guide = tmp_path / "fake_guide.json"
            sample_guide = get_sample_bilingual_lecture_guide()
            fake_guide.write_text(sample_guide.model_dump_json(), encoding="utf-8")

            # Case A: Normal completion -> uploaded file is deleted
            mock_client = MagicMock()
            mock_audio_file = MagicMock()
            mock_audio_file.name = "files/test_audio_success"
            mock_client.files.upload.return_value = mock_audio_file

            test_args = [
                "verify_audio_fidelity.py",
                "--audio", str(fake_audio),
                "--guide", str(fake_guide),
                "--api-key", "dummy_key"
            ]

            with patch("sys.argv", test_args), \
                 patch("verify_audio_fidelity.genai.Client", return_value=mock_client), \
                 patch("verify_audio_fidelity.verify_and_reconcile_study_guide", return_value=(sample_guide, MagicMock(contradictions_detected=0, contradictions=[], notes_audited=False, overall_fidelity_summary="Passed", audit_passed=True))), \
                 patch("verify_audio_fidelity.PDFStudyGuideBuilder.build", return_value=tmp_path / "out.pdf"), \
                 patch("sys.stdout", new_callable=io.StringIO):
                verify_audio_fidelity.main()

            mock_client.files.delete.assert_called_with(name="files/test_audio_success")

            # Case B: Exception occurs during verification -> uploaded file is still deleted in finally block
            mock_client.reset_mock()
            mock_audio_file_fail = MagicMock()
            mock_audio_file_fail.name = "files/test_audio_failure"
            mock_client.files.upload.return_value = mock_audio_file_fail

            with patch("sys.argv", test_args), \
                 patch("verify_audio_fidelity.genai.Client", return_value=mock_client), \
                 patch("verify_audio_fidelity.verify_and_reconcile_study_guide", side_effect=RuntimeError("Simulated Gemini error")), \
                 patch("sys.stdout", new_callable=io.StringIO):
                with self.assertRaises(RuntimeError):
                    verify_audio_fidelity.main()

            mock_client.files.delete.assert_called_with(name="files/test_audio_failure")

    def test_23_staged_upload_cleanup_on_later_rejected_file(self):
        """Regression test for Issue 5: Rejected multi-file upload cleans up every file staged earlier in the same request."""
        from fastapi.testclient import TestClient
        from app import app
        from config import UPLOAD_DIR
        import io

        client = TestClient(app)

        # 1. Test rejection on audio: valid audio + invalid audio format (.exe)
        initial_files = set(p.name for p in UPLOAD_DIR.iterdir()) if UPLOAD_DIR.exists() else set()
        response_audio = client.post(
            "/api/process_audio",
            data={"study_mode": "detailed"},
            files=[
                ("audio", ("good_audio.mp3", io.BytesIO(b"dummy mp3 data"), "audio/mpeg")),
                ("audio", ("bad_audio.exe", io.BytesIO(b"executable data"), "application/octet-stream"))
            ]
        )
        self.assertEqual(response_audio.status_code, 400)
        self.assertIn("Unsupported audio format", response_audio.text)
        current_files = set(p.name for p in UPLOAD_DIR.iterdir()) if UPLOAD_DIR.exists() else set()
        self.assertEqual(current_files - initial_files, set(), "Audio staging left orphan files after rejection")

        # 2. Test rejection on notes: valid audio + valid notes + invalid notes format (.bat)
        initial_files_2 = set(p.name for p in UPLOAD_DIR.iterdir()) if UPLOAD_DIR.exists() else set()
        response_notes = client.post(
            "/api/process_audio",
            data={"study_mode": "detailed"},
            files=[
                ("audio", ("good_audio.mp3", io.BytesIO(b"dummy mp3 data"), "audio/mpeg")),
                ("notes", ("valid_notes.pdf", io.BytesIO(b"%PDF-1.4 dummy pdf"), "application/pdf")),
                ("notes", ("bad_notes.bat", io.BytesIO(b"@echo off"), "text/plain"))
            ]
        )
        self.assertEqual(response_notes.status_code, 400)
        self.assertIn("Unsupported lecture notes format", response_notes.text)
        current_files_2 = set(p.name for p in UPLOAD_DIR.iterdir()) if UPLOAD_DIR.exists() else set()
        self.assertEqual(current_files_2 - initial_files_2, set(), "Notes staging left orphan files after rejection")

    def test_24_system_block_diagram_preserves_five_elements(self):
        """Regression test for Issue 6: System block diagram preserves five-element input without adding nodes."""
        from visualizer import render_system_block_diagram
        import tempfile

        # 1. 5-element diagram
        block_diag_5 = DiagramDefinition(
            diagram_id="test_diag_5_nodes",
            title="Five-Block Closed Loop Architecture",
            diagram_type="SYSTEM_BLOCK_DIAGRAM",
            elements=[
                DiagramElement(label="AC Utility Grid", description="Power Source"),
                DiagramElement(label="Power Converter", description="Switching Stage"),
                DiagramElement(label="DC Motor", description="Load"),
                DiagramElement(label="Current Transducer", description="Sensor"),
                DiagramElement(label="Microcontroller", description="Controller")
            ],
            caption="Five block control diagram without invented dummy components."
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "five_block.png"
            rendered = render_system_block_diagram(block_diag_5, out_file)
            self.assertTrue(rendered.exists())
            self.assertGreater(rendered.stat().st_size, 1000)

            # Element count must be strictly 5
            self.assertEqual(len(block_diag_5.elements), 5)
            labels = [e.label for e in block_diag_5.elements]
            self.assertNotIn("Component 6", labels)
            self.assertEqual(labels, [
                "AC Utility Grid", "Power Converter", "DC Motor", "Current Transducer", "Microcontroller"
            ])

        # 2. 6-element diagram
        block_diag_6 = DiagramDefinition(
            diagram_id="test_diag_6_nodes",
            title="Six-Block System Architecture",
            diagram_type="SYSTEM_BLOCK_DIAGRAM",
            elements=[
                DiagramElement(label=f"Block {i}", description=f"Desc {i}") for i in range(1, 7)
            ],
            caption="Six block diagram."
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file_6 = Path(tmp_dir) / "six_block.png"
            rendered_6 = render_system_block_diagram(block_diag_6, out_file_6)
            self.assertTrue(rendered_6.exists())
            self.assertEqual(len(block_diag_6.elements), 6)

        # 3. 4-element diagram (routes to flowchart)
        block_diag_4 = DiagramDefinition(
            diagram_id="test_diag_4_nodes",
            title="Four-Block Architecture",
            diagram_type="SYSTEM_BLOCK_DIAGRAM",
            elements=[
                DiagramElement(label=f"Step {i}", description=f"Desc {i}") for i in range(1, 5)
            ],
            caption="Four block diagram routed to flowchart."
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file_4 = Path(tmp_dir) / "four_block.png"
            rendered_4 = render_system_block_diagram(block_diag_4, out_file_4)
            self.assertTrue(rendered_4.exists())
            self.assertEqual(len(block_diag_4.elements), 4)

    def test_25_function_plot_preserves_five_elements(self):
        """Regression test for Issue 7: Function-plot renderer does not omit an element when given five elements."""
        from visualizer import render_function_plot
        import tempfile

        five_elem_plot = DiagramDefinition(
            diagram_id="test_plot_5_elements",
            title="Multi-stage Frequency Response",
            diagram_type="FUNCTION_PLOT",
            elements=[
                DiagramElement(label="Stage 1: Input Filter", value=10.5, description="Low-pass filter stage"),
                DiagramElement(label="Stage 2: Pre-Amplifier", value=25.0, description="Low-noise pre-amp"),
                DiagramElement(label="Stage 3: Main Gain", value=50.2, description="Variable gain amplifier"),
                DiagramElement(label="Stage 4: Post-Filter", value=75.8, description="Bandpass shaping"),
                DiagramElement(label="Stage 5: Buffer Output", value=99.1, description="High-current line driver"),
            ],
            caption="Five-stage scientific frequency curve and description badges."
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "function_plot_5.png"
            rendered = render_function_plot(five_elem_plot, out_file)
            self.assertTrue(rendered.exists())
            self.assertGreater(rendered.stat().st_size, 1000)

            # Verify all 5 elements are intact in diagram definition
            self.assertEqual(len(five_elem_plot.elements), 5)
    def test_26_protect_local_mutations_testserver_restriction(self):
        """Regression test for Point 4: protect_local_mutations restricts testserver so production path rejects it."""
        from fastapi.testclient import TestClient
        from app import app
        from unittest.mock import patch

        client = TestClient(app)

        # 1. Under test environment, testclient is allowed
        resp_test = client.get("/api/config")
        self.assertEqual(resp_test.status_code, 200)

        # 2. In simulated production (is_test_environment returns False):
        with patch("app.is_test_environment", return_value=False):
            # Testserver host/origin must be REJECTED with 403 Forbidden
            resp_prod_testserver = client.post(
                "/api/set_key",
                data={"key": "test_key"},
                headers={"host": "testserver", "origin": "http://testserver"}
            )
            self.assertEqual(resp_prod_testserver.status_code, 403)
            self.assertIn("Requests must come from the local LectureAI dashboard", resp_prod_testserver.text)

            # External attacker origin must be REJECTED with 403
            resp_attacker = client.post(
                "/api/set_key",
                data={"key": "test_key"},
                headers={"origin": "http://attacker.com"}
            )
            self.assertEqual(resp_attacker.status_code, 403)

            # Legitimate local origin in production must SUCCEED (200)
            resp_prod_local = client.post(
                "/api/set_key",
                data={"key": "valid_key"},
                headers={"host": "127.0.0.1:8000", "origin": "http://127.0.0.1:8000"}
            )
            self.assertEqual(resp_prod_local.status_code, 200)

    def test_27_mixed_sources_all_computer(self):
        """Mixed sources: All-computer sources (multiple audio + notes) are resolved and staged in order."""
        import io
        import json
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        audio1_bytes = io.BytesIO(b"audio part 1 dummy bytes")
        audio2_bytes = io.BytesIO(b"audio part 2 dummy bytes")
        notes_bytes = io.BytesIO(b"%PDF-1.4 notes dummy bytes")

        sources_payload = json.dumps([
            {"id": "a1", "kind": "upload", "role": "audio", "order": 0, "display_name": "lecture_part1.mp3"},
            {"id": "a2", "kind": "upload", "role": "audio", "order": 1, "display_name": "lecture_part2.wav"},
            {"id": "n1", "kind": "upload", "role": "notes", "order": 0, "display_name": "lecture_notes.pdf"},
        ])

        with patch("app.process_lecture") as mock_pipeline:
            mock_pipeline.return_value = {
                "success": True,
                "pdf_path": "output_pdfs/mock.pdf",
                "pdf_filename": "mock.pdf",
                "lecture_title": "All Computer Test",
                "summary": "Mock summary",
                "contradictions": [],
                "notes_audited": True,
                "notes_reference": "Full slide deck",
                "audio_fidelity_score": 100,
            }
            res = client.post(
                "/api/process_audio",
                data={"sources": sources_payload, "api_key": "mock_api_key"},
                files={
                    "file_a1": ("lecture_part1.mp3", audio1_bytes, "audio/mpeg"),
                    "file_a2": ("lecture_part2.wav", audio2_bytes, "audio/wav"),
                    "file_n1": ("lecture_notes.pdf", notes_bytes, "application/pdf"),
                }
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data.get("success"))
            self.assertTrue(mock_pipeline.called)
            kwargs = mock_pipeline.call_args.kwargs
            self.assertEqual(len(kwargs["audio_path"]), 2)
            self.assertTrue(kwargs["audio_path"][0].name.endswith("lecture_part1.mp3"))
            self.assertTrue(kwargs["audio_path"][1].name.endswith("lecture_part2.wav"))
            self.assertEqual(len(kwargs["notes_path"]), 1)
            self.assertTrue(kwargs["notes_path"][0].name.endswith("lecture_notes.pdf"))

    def test_28_mixed_sources_all_links(self):
        """Mixed sources: All-links sources (mocked downloader) are safely retrieved and passed in order."""
        import json
        import tempfile
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        sources_payload = json.dumps([
            {"id": "l1", "kind": "link", "role": "audio", "order": 0, "link": "https://drive.google.com/file/d/audio1", "display_name": "cloud_audio1.mp3"},
            {"id": "l2", "kind": "link", "role": "audio", "order": 1, "link": "https://example.com/audio2.m4a", "display_name": "cloud_audio2.m4a"},
            {"id": "ln1", "kind": "link", "role": "notes", "order": 0, "link": "https://example.com/slides.pdf", "display_name": "cloud_slides.pdf"},
        ])

        with tempfile.TemporaryDirectory() as tmp_dir:
            a1_file = Path(tmp_dir) / "cloud_audio1.mp3"
            a2_file = Path(tmp_dir) / "cloud_audio2.m4a"
            n1_file = Path(tmp_dir) / "cloud_slides.pdf"
            a1_file.write_bytes(b"mock audio 1")
            a2_file.write_bytes(b"mock audio 2")
            n1_file.write_bytes(b"%PDF-1.4 mock notes")

            def mock_dl(url, target_dir, expected_type, progress_callback=None):
                if "audio1" in url:
                    return a1_file, "cloud_audio1.mp3"
                elif "audio2" in url:
                    return a2_file, "cloud_audio2.m4a"
                else:
                    return n1_file, "cloud_slides.pdf"

            with patch("app.download_from_link", side_effect=mock_dl):
                with patch("app.process_lecture") as mock_pipeline:
                    mock_pipeline.return_value = {
                        "success": True,
                        "pdf_path": "output_pdfs/mock.pdf",
                        "pdf_filename": "mock.pdf",
                        "lecture_title": "All Links Test",
                        "summary": "Mock summary",
                        "contradictions": [],
                        "notes_audited": True,
                        "notes_reference": "Full slide deck",
                        "audio_fidelity_score": 100,
                    }
                    res = client.post(
                        "/api/process_audio",
                        data={"sources": sources_payload, "api_key": "mock_api_key"}
                    )
                    self.assertEqual(res.status_code, 200)
                    self.assertTrue(res.json().get("success"))
                    self.assertTrue(mock_pipeline.called)
                    kwargs = mock_pipeline.call_args.kwargs
                    self.assertEqual(len(kwargs["audio_path"]), 2)
                    self.assertEqual(kwargs["audio_path"][0], a1_file)
                    self.assertEqual(kwargs["audio_path"][1], a2_file)
                    self.assertEqual(len(kwargs["notes_path"]), 1)
                    self.assertEqual(kwargs["notes_path"][0], n1_file)

    def test_29_mixed_sources_all_folder(self):
        """Mixed sources: All-folder sources (audio + notes) inside configured courses directory are validated and resolved."""
        import json
        import tempfile
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        with tempfile.TemporaryDirectory() as tmp_dir:
            course_dir = Path(tmp_dir) / "Biomechanics"
            course_dir.mkdir(parents=True, exist_ok=True)
            folder_audio = course_dir / "lecture_01.mp3"
            folder_notes = course_dir / "lecture_01_notes.pdf"
            folder_audio.write_bytes(b"dummy audio folder content")
            folder_notes.write_bytes(b"%PDF-1.4 dummy notes folder content")

            sources_payload = json.dumps([
                {"id": "f_a", "kind": "folder", "role": "audio", "order": 0, "local_path": str(folder_audio), "display_name": "lecture_01.mp3"},
                {"id": "f_n", "kind": "folder", "role": "notes", "order": 0, "local_path": str(folder_notes), "display_name": "lecture_01_notes.pdf"},
            ])

            with patch("link_downloader.get_configured_courses_roots", return_value=[Path(tmp_dir)]):
                with patch("app.process_lecture") as mock_pipeline:
                    mock_pipeline.return_value = {
                        "success": True,
                        "pdf_path": "output_pdfs/mock.pdf",
                        "pdf_filename": "mock.pdf",
                        "lecture_title": "All Folder Test",
                        "summary": "Mock summary",
                        "contradictions": [],
                        "notes_audited": True,
                        "notes_reference": "Full slide deck",
                        "audio_fidelity_score": 100,
                    }
                    res = client.post(
                        "/api/process_audio",
                        data={"sources": sources_payload, "api_key": "mock_api_key"}
                    )
                    self.assertEqual(res.status_code, 200)
                    self.assertTrue(res.json().get("success"))
                    self.assertTrue(mock_pipeline.called)
                    kwargs = mock_pipeline.call_args.kwargs
                    self.assertEqual(len(kwargs["audio_path"]), 1)
                    self.assertEqual(kwargs["audio_path"][0].resolve(), folder_audio.resolve())
                    self.assertEqual(len(kwargs["notes_path"]), 1)
                    self.assertEqual(kwargs["notes_path"][0].resolve(), folder_notes.resolve())

    def test_30_mixed_sources_combination(self):
        """Mixed sources: Mixed combination (computer + link + folder) preserves user order and per-deck slide ranges."""
        import io
        import json
        import tempfile
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        with tempfile.TemporaryDirectory() as tmp_dir:
            course_dir = Path(tmp_dir) / "Medical_Robotics"
            course_dir.mkdir(parents=True, exist_ok=True)
            folder_slides = course_dir / "deck_intro.pdf"
            folder_slides.write_bytes(b"%PDF-1.4 intro slides")

            link_audio_file = Path(tmp_dir) / "part2_web.mp3"
            link_audio_file.write_bytes(b"mock link audio bytes")

            comp_audio_bytes = io.BytesIO(b"part 1 upload bytes")
            comp_notes_bytes = io.BytesIO(b"%PDF-1.4 upload continued slides")

            sources_payload = json.dumps([
                {"id": "up_a", "kind": "upload", "role": "audio", "order": 0, "display_name": "part1_mic.mp3"},
                {"id": "lk_a", "kind": "link", "role": "audio", "order": 1, "link": "https://example.com/part2_web.mp3", "display_name": "part2_web.mp3"},
                {"id": "fd_n", "kind": "folder", "role": "notes", "order": 0, "local_path": str(folder_slides), "display_name": "deck_intro.pdf", "start_slide": 1, "end_slide": 25},
                {"id": "up_n", "kind": "upload", "role": "notes", "order": 1, "display_name": "deck_advanced.pdf", "slide_range": "26-50"},
            ])

            def mock_dl(url, target_dir, expected_type, progress_callback=None):
                return link_audio_file, "part2_web.mp3"

            with patch("link_downloader.get_configured_courses_roots", return_value=[Path(tmp_dir)]):
                with patch("app.download_from_link", side_effect=mock_dl):
                    with patch("app.process_lecture") as mock_pipeline:
                        mock_pipeline.return_value = {
                            "success": True,
                            "pdf_path": "output_pdfs/mock.pdf",
                            "pdf_filename": "mock.pdf",
                            "lecture_title": "Mixed Combo Test",
                            "summary": "Mock summary",
                            "contradictions": [],
                            "notes_audited": True,
                            "notes_reference": "Slides 1-50",
                            "audio_fidelity_score": 100,
                        }
                        res = client.post(
                            "/api/process_audio",
                            data={"sources": sources_payload, "api_key": "mock_api_key"},
                            files={
                                "file_up_a": ("part1_mic.mp3", comp_audio_bytes, "audio/mpeg"),
                                "file_up_n": ("deck_advanced.pdf", comp_notes_bytes, "application/pdf"),
                            }
                        )
                        self.assertEqual(res.status_code, 200)
                        self.assertTrue(res.json().get("success"))
                        self.assertTrue(mock_pipeline.called)
                        kwargs = mock_pipeline.call_args.kwargs
                        # Chronological order verified
                        self.assertEqual(len(kwargs["audio_path"]), 2)
                        self.assertTrue(kwargs["audio_path"][0].name.endswith("part1_mic.mp3"))
                        self.assertEqual(kwargs["audio_path"][1], link_audio_file)
                        self.assertEqual(len(kwargs["notes_path"]), 2)
                        self.assertEqual(kwargs["notes_path"][0].resolve(), folder_slides.resolve())
                        self.assertTrue(kwargs["notes_path"][1].name.endswith("deck_advanced.pdf"))
                        # Per-deck slide ranges verified
                        self.assertEqual(kwargs["slide_ranges"], [(1, 25), (26, 50)])

    def test_31_mixed_sources_failing_link_cleanup(self):
        """Mixed sources: Failing link in the middle fails the job with item name and cleans up staged files."""
        import io
        import json
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app import app, jobs, UPLOAD_DIR

        client = TestClient(app)
        audio_upload_bytes = io.BytesIO(b"part 1 upload bytes to stage")

        sources_payload = json.dumps([
            {"id": "up_1", "kind": "upload", "role": "audio", "order": 0, "display_name": "part1_stage.mp3"},
            {"id": "lk_2", "kind": "link", "role": "audio", "order": 1, "link": "https://example.com/bad_link.mp3", "display_name": "bad_link.mp3"},
        ])

        def failing_dl(url, target_dir, expected_type, progress_callback=None):
            raise RuntimeError("Connection timed out 504")

        with patch("app.download_from_link", side_effect=failing_dl):
            res = client.post(
                "/api/process_audio",
                data={"sources": sources_payload, "api_key": "mock_api_key"},
                files={"file_up_1": ("part1_stage.mp3", audio_upload_bytes, "audio/mpeg")}
            )
            self.assertEqual(res.status_code, 200)
            job_id = res.json()["job_id"]

            job_state = jobs[job_id]
            self.assertEqual(job_state["status"], "failed")
            self.assertIn("bad_link.mp3", job_state["error"])
            self.assertIn("Connection timed out 504", job_state["error"])

            # Verify no orphaned staged files from this job remain in UPLOAD_DIR
            staged_matches = list(UPLOAD_DIR.glob("*part1_stage.mp3"))
            self.assertEqual(len(staged_matches), 0, "All staged files must be removed on failure")

    def test_32_mixed_sources_unsupported_extension_rejected(self):
        """Mixed sources: Unsupported extensions and empty audio are rejected upfront with HTTP 400."""
        import json
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)

        # 1. Unsupported audio extension (e.g. .exe)
        bad_audio = json.dumps([
            {"id": "bad_a", "kind": "link", "role": "audio", "order": 0, "link": "https://example.com/malware.exe", "display_name": "malware.exe"}
        ])
        res_bad_a = client.post("/api/process_audio", data={"sources": bad_audio, "api_key": "mock_key"})
        self.assertEqual(res_bad_a.status_code, 400)
        self.assertIn("Unsupported audio format '.exe'", res_bad_a.json()["detail"])

        # 2. Unsupported notes extension (e.g. .mp4)
        bad_notes = json.dumps([
            {"id": "good_a", "kind": "link", "role": "audio", "order": 0, "link": "https://example.com/lec.mp3", "display_name": "lec.mp3"},
            {"id": "bad_n", "kind": "link", "role": "notes", "order": 0, "link": "https://example.com/video.mp4", "display_name": "video.mp4"}
        ])
        res_bad_n = client.post("/api/process_audio", data={"sources": bad_notes, "api_key": "mock_key"})
        self.assertEqual(res_bad_n.status_code, 400)
        self.assertIn("Unsupported lecture notes format '.mp4'", res_bad_n.json()["detail"])

        # 3. Missing recording validation
        empty_audio = json.dumps([
            {"id": "n1", "kind": "link", "role": "notes", "order": 0, "link": "https://example.com/deck.pdf", "display_name": "deck.pdf"}
        ])
        res_no_audio = client.post("/api/process_audio", data={"sources": empty_audio, "api_key": "mock_key"})
        self.assertEqual(res_no_audio.status_code, 400)
        self.assertIn("No lecture recording provided", res_no_audio.json()["detail"])

    def test_33_mixed_sources_path_outside_courses_rejected(self):
        """Mixed sources: Course folder path outside allowed courses roots is rejected upfront with HTTP 400."""
        import json
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        bad_folder = json.dumps([
            {"id": "a1", "kind": "folder", "role": "audio", "order": 0, "local_path": "C:/Windows/System32/evil.mp3", "display_name": "evil.mp3"}
        ])
        res = client.post("/api/process_audio", data={"sources": bad_folder, "api_key": "mock_key"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("outside the configured courses directory", res.json()["detail"])

    def test_34_mixed_sources_order_preserved(self):
        """Mixed sources: Exact chronological ordering is preserved regardless of alphabetical sorting."""
        import json
        import tempfile
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        sources_payload = json.dumps([
            {"id": "a_z", "kind": "link", "role": "audio", "order": 0, "link": "https://example.com/z.mp3", "display_name": "Zeta_Part_A.mp3"},
            {"id": "a_a", "kind": "link", "role": "audio", "order": 1, "link": "https://example.com/a.mp3", "display_name": "Alpha_Part_B.mp3"},
            {"id": "n_w", "kind": "link", "role": "notes", "order": 0, "link": "https://example.com/w.pdf", "display_name": "Omega_Slides.pdf"},
            {"id": "n_b", "kind": "link", "role": "notes", "order": 1, "link": "https://example.com/b.pdf", "display_name": "Beta_Slides.pdf"},
        ])

        with tempfile.TemporaryDirectory() as tmp_dir:
            zeta_file = Path(tmp_dir) / "Zeta_Part_A.mp3"
            alpha_file = Path(tmp_dir) / "Alpha_Part_B.mp3"
            omega_file = Path(tmp_dir) / "Omega_Slides.pdf"
            beta_file = Path(tmp_dir) / "Beta_Slides.pdf"
            zeta_file.write_bytes(b"z")
            alpha_file.write_bytes(b"a")
            omega_file.write_bytes(b"%PDF-1.4 w")
            beta_file.write_bytes(b"%PDF-1.4 b")

            def mock_dl(url, target_dir, expected_type, progress_callback=None):
                if "z.mp3" in url: return zeta_file, "Zeta_Part_A.mp3"
                if "a.mp3" in url: return alpha_file, "Alpha_Part_B.mp3"
                if "w.pdf" in url: return omega_file, "Omega_Slides.pdf"
                return beta_file, "Beta_Slides.pdf"

            with patch("app.download_from_link", side_effect=mock_dl):
                with patch("app.process_lecture") as mock_pipeline:
                    mock_pipeline.return_value = {
                        "success": True,
                        "pdf_path": "output_pdfs/mock.pdf",
                        "pdf_filename": "mock.pdf",
                        "lecture_title": "Order Preserved Test",
                        "summary": "Mock summary",
                        "contradictions": [],
                        "notes_audited": True,
                        "notes_reference": "Full slide deck",
                        "audio_fidelity_score": 100,
                    }
                    res = client.post("/api/process_audio", data={"sources": sources_payload, "api_key": "mock_key"})
                    self.assertEqual(res.status_code, 200)
                    self.assertTrue(mock_pipeline.called)
                    kwargs = mock_pipeline.call_args.kwargs
                    self.assertEqual(kwargs["audio_path"], [zeta_file, alpha_file])
                    self.assertEqual(kwargs["notes_path"], [omega_file, beta_file])

    def test_35_chunked_upload_60mb_dummy_file(self):
        """Mixed sources robustness: 60MB dummy file is written in chunks to disk without whole-file memory buffering."""
        import json
        import io
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app import app, UPLOAD_DIR

        client = TestClient(app)
        target_size = 60 * 1024 * 1024  # 60 MB

        # 60 MB stream in 1 MB blocks
        chunk = b"0" * (1024 * 1024)
        large_stream = io.BytesIO(chunk * 60)
        large_stream.name = "large_60mb_lecture.mp3"

        sources_payload = json.dumps([
            {"id": "big_upload", "kind": "upload", "role": "audio", "order": 0, "display_name": "large_60mb_lecture.mp3"}
        ])

        with patch("app.process_lecture") as mock_pipeline:
            mock_pipeline.return_value = {
                "success": True,
                "pdf_path": "output_pdfs/mock.pdf",
                "pdf_filename": "mock.pdf",
                "lecture_title": "60MB Upload Test",
                "summary": "Mock summary",
                "contradictions": [],
                "notes_audited": True,
                "notes_reference": "Full slide deck",
                "audio_fidelity_score": 100,
            }
            res = client.post(
                "/api/process_audio",
                data={"sources": sources_payload, "api_key": "mock_api_key"},
                files={"file_big_upload": ("large_60mb_lecture.mp3", large_stream, "audio/mpeg")}
            )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json().get("success"))
            self.assertTrue(mock_pipeline.called)

            passed_path = mock_pipeline.call_args.kwargs["audio_path"][0]
            self.assertTrue(passed_path.exists())
            self.assertEqual(passed_path.stat().st_size, target_size)

            # Cleanup staged file
            passed_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()


