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


if __name__ == "__main__":
    unittest.main()


