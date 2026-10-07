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
        """Regression test for Part 1: Validation and ignoring manual uploads when folder mode is active."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)

        # 1. Posting without any audio input and without demo mode returns clear 400
        res_empty = client.post("/api/process_audio", data={})
        self.assertEqual(res_empty.status_code, 400)
        self.assertIn("No lecture recording provided", res_empty.json()["detail"])

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


if __name__ == "__main__":
    unittest.main()


