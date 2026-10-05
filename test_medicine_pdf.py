import os
from pathlib import Path
from models import (
    LectureStudyGuide, LectureSection, DoctorAlert, TableDefinition,
    DiagramDefinition, DiagramElement, ExamQuestion
)
from pdf_builder import PDFStudyGuideBuilder

guide_med = LectureStudyGuide(
    course_name="Medical Pharmacology & Therapeutics (MED305)",
    lecture_title="Beta-Adrenergic Blockers: Receptor Selectivity, Indications & Clinical Pitfalls",
    lecturer_name="Prof. Nadia El-Sayed",
    lecture_date="Fall Academic Semester",
    executive_summary=(
        "This lecture provides an exhaustive clinical analysis of beta-adrenergic receptor antagonists. "
        "Prof. Nadia examines the pharmacological distinction between cardioselective (beta-1) and non-selective "
        "agents, their hemodynamic effects on cardiac output and peripheral resistance, and their therapeutic role "
        "in ischemic heart disease, heart failure, and hypertension. Crucial clinical pearls and black-box warnings "
        "regarding abrupt withdrawal and asthmatic bronchospasm were strongly emphasized for university exams."
    ),
    sections=[
        LectureSection(
            section_number=1,
            topic_title="Receptor Selectivity: Cardioselective vs Non-Selective Beta-Blockers",
            detailed_explanation=(
                "Beta-adrenergic receptors are divided into Beta-1 (predominantly in cardiac tissue, mediating positive "
                "inotropy and chronotropy) and Beta-2 (located in bronchial smooth muscle, mediating bronchodilation, and in "
                "vascular smooth muscle). Non-selective beta-blockers (e.g., Propranolol) antagonize both receptor subtypes with "
                "equal affinity. Cardioselective beta-blockers (e.g., Metoprolol, Atenolol, Bisoprolol) exhibit roughly 20-fold "
                "greater affinity for Beta-1 receptors at standard therapeutic doses.\n\n"
                "However, selectivity is dose-dependent: at higher doses, cardioselectivity is lost, resulting in significant "
                "Beta-2 blockade and consequent bronchospasm in vulnerable patients."
            ),
            key_bullet_points=[
                "Beta-1 receptors mediate cardiac contractility (inotropy) and heart rate (chronotropy).",
                "Beta-2 receptors mediate bronchial and vascular smooth muscle relaxation.",
                "Cardioselectivity is relative and diminishes at supratherapeutic dosages.",
                "Third-generation agents (e.g., Carvedilol, Labetalol) offer additional alpha-1 blockade for systemic vasodilation."
            ],
            doctor_alerts=[
                DoctorAlert(
                    alert_type="CRITICAL_CONCEPT",
                    highlight_title="Loss of Cardioselectivity at High Doses",
                    cue_detected="Doctor emphasized: 'Remember this rule for the exam: Metoprolol is cardioselective only at standard doses. If you push the dose, you will trigger severe asthma!'",
                    alert_content=(
                        "Cardioselectivity is not absolute. High doses spill over to Beta-2 receptors, inducing life-threatening bronchoconstriction."
                    ),
                    exam_impact="Case studies testing hypertension in asthmatic patients require recognizing the limits of beta-1 selectivity."
                )
            ],
            tables=[
                TableDefinition(
                    title="Classification of Representative Beta-Adrenergic Antagonists",
                    columns=["Drug Name", "Generation", "Selectivity Profile", "Intrinsic Sympathomimetic (ISA)"],
                    rows=[
                        ["Propranolol", "First Generation", "Non-Selective (Beta-1 & Beta-2)", "No"],
                        ["Atenolol", "Second Generation", "Cardioselective (Beta-1)", "No"],
                        ["Metoprolol", "Second Generation", "Cardioselective (Beta-1)", "No"],
                        ["Carvedilol", "Third Generation", "Non-Selective + Alpha-1 Blockade", "No"],
                        ["Pindolol", "First Generation", "Non-Selective", "Yes (Partial Agonist)"]
                    ],
                    notes="Intrinsic sympathomimetic activity (ISA) avoids resting bradycardia but is contraindicated post-MI."
                )
            ],
            formulas=[], # Non-math subject: 0 formulas
            diagrams=[
                DiagramDefinition(
                    diagram_id="med_receptor_map",
                    title="Adrenergic Receptor Distribution and Biological Responses",
                    diagram_type="CONCEPT_MAP",
                    elements=[
                        DiagramElement(label="Beta-1 Receptors", description="Myocardium: Increased SA node rate & contractility"),
                        DiagramElement(label="Beta-2 Receptors", description="Bronchial Tree: Bronchodilation & glycogenolysis"),
                        DiagramElement(label="Alpha-1 Receptors", description="Vascular Bed: Arteriolar constriction & BP rise"),
                        DiagramElement(label="Renal Juxtaglomerular", description="Beta-1: Renin release & RAAS activation")
                    ],
                    caption="Physiological organ mapping of adrenergic receptor targets."
                )
            ]
        ),
        LectureSection(
            section_number=2,
            topic_title="Clinical Indications, Absolute Contraindications, and Rebound Tachycardia",
            detailed_explanation=(
                "Beta-blockers represent cornerstone therapy in post-myocardial infarction secondary prevention, stable angina, "
                "and compensated chronic heart failure (specifically Bisoprolol, Carvedilol, and Metoprolol Succinate).\n\n"
                "Absolute contraindications include: severe symptomatic bradycardia (heart rate < 45 bpm), second- or third-degree "
                "AV block without a pacemaker, cardiogenic shock, and severe decompensated acute pulmonary edema. Abrupt cessation of "
                "chronic beta-blocker therapy causes profound rebound tachycardia, malignant ventricular arrhythmias, and acute MI due "
                "to pharmacological upregulation of cell-surface beta-adrenergic receptors."
            ),
            key_bullet_points=[
                "Evidence-based mortality benefit in chronic heart failure is established strictly for Metoprolol, Bisoprolol, and Carvedilol.",
                "Never initiate or uptitrate beta-blockers during acute decompensated heart failure.",
                "Taper doses gradually over 10 to 14 days to prevent upregulation-induced rebound ischemia."
            ],
            doctor_alerts=[
                DoctorAlert(
                    alert_type="EXAM_PREDICTION",
                    highlight_title="Receptor Upregulation and Withdrawal Syndrome",
                    cue_detected="Doctor warned: 'I will ask this clinical scenario on the exam: A patient stops their Atenolol abruptly before surgery. What happens and why?'",
                    alert_content=(
                        "Prolonged receptor blockade leads to compensatory receptor upregulation. Sudden drug withdrawal exposes hypersensitive "
                        "receptors to endogenous catecholamines, triggering hypertensive crisis or fatal arrhythmias."
                    ),
                    exam_impact="Students must explain the molecular mechanism (upregulation) and state the prevention protocol (gradual tapering)."
                )
            ],
            tables=[],
            formulas=[],
            diagrams=[
                DiagramDefinition(
                    diagram_id="med_timeline",
                    title="Clinical Timeline for Beta-Blocker Initiation in Heart Failure",
                    diagram_type="TIMELINE",
                    elements=[
                        DiagramElement(label="Clinical Stabilization", description="Patient euvolemic on diuretics"),
                        DiagramElement(label="Low-Dose Initiation", description="Initiate Carvedilol 3.125mg BID"),
                        DiagramElement(label="Bi-Weekly Titration", description="Double dose every 2-4 weeks"),
                        DiagramElement(label="Target Maintenance", description="Achieve target mortality-reducing dose")
                    ],
                    caption="Protocolized slow titration stages to prevent worsening heart failure."
                )
            ]
        )
    ],
    exam_readiness_section=[
        ExamQuestion(
            question_number=1,
            question_type="CASE_STUDY",
            question_prompt=(
                "A 58-year-old male with a 15-year history of moderate-to-severe bronchial asthma suffers an acute anterior ST-elevation "
                "myocardial infarction. Following successful primary percutaneous intervention, his physician plans long-term cardioprotective "
                "pharmacotherapy. Which of the following agents is the safest choice to mitigate post-MI remodeling while minimizing pulmonary complications?"
            ),
            options=[
                "A) Propranolol",
                "B) Nadolol",
                "C) Metoprolol Tartrate at low-to-moderate dosage",
                "D) Timolol ophthalmic solution"
            ],
            correct_answer="C) Metoprolol Tartrate at low-to-moderate dosage",
            model_explanation=(
                "Metoprolol is a second-generation cardioselective Beta-1 antagonist. While all beta-blockers must be used with caution in asthma, "
                "low-dose cardioselective agents are preferentially used when compelling indications (post-MI mortality reduction) exist. "
                "Propranolol, Nadolol, and Timolol are non-selective and carry high risk of fatal bronchospasm."
            ),
            doctor_hint="The professor explicitly noted that cardioselective agents must be chosen when asthma coexists with an absolute post-MI indication.",
            probability="Definite (Doctor Stated)"
        )
    ],
    full_transcript_english=(
        "Good morning, doctors. Welcome to today's medical pharmacology lecture on adrenergic receptor antagonists. "
        "Today we focus on one of the most widely prescribed drug classes in clinical medicine: beta-blockers.\n\n"
        "To master these drugs for your clinical rotations and board exams, you must understand receptor selectivity. "
        "Beta-1 receptors are your cardiac targets: they regulate heart rate and contractility. Beta-2 receptors reside in bronchial "
        "smooth muscle and peripheral blood vessels. When you administer a non-selective agent like Propranolol, you block both equally. "
        "In a healthy individual, bronchial tone remains manageable, but in an asthmatic patient, blocking Beta-2 removes the sympathetic "
        "bronchodilatory drive, leading to acute bronchospasm. Always remember this distinction.\n\n"
        "Now, let us discuss receptor upregulation. When you treat a patient with chronic beta-blockers, the cell membrane responds to "
        "prolonged antagonism by synthesizing and inserting more beta receptors on the cardiomyocyte surface. If that patient stops their "
        "medication abruptly, circulating adrenaline and noradrenaline bind to an increased density of hypersensitive receptors. "
        "The result is severe rebound tachycardia, malignant arrhythmias, or rebound myocardial infarction. Never stop beta-blockers abruptly; "
        "always taper gradually over two weeks. Thank you for your dedication."
    )
)

out_pdf = PDFStudyGuideBuilder(guide_med, output_filename="Medicine_Beta_Blockers_Guide.pdf").build()
print("Compiled Medicine Study Guide PDF:", out_pdf)
print(f"Size: {out_pdf.stat().st_size / 1024:.1f} KB")
