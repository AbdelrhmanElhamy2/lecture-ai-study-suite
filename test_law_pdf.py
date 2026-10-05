import os
from pathlib import Path
from models import (
    LectureStudyGuide, LectureSection, DoctorAlert, TableDefinition,
    DiagramDefinition, DiagramElement, ExamQuestion
)
from pdf_builder import PDFStudyGuideBuilder

guide_law = LectureStudyGuide(
    course_name="Constitutional Law & Jurisprudence (LAW102)",
    lecture_title="The Doctrine of Judicial Review and the Constitutional Proportionality Test",
    lecturer_name="Prof. Hesham Abdel-Rahman",
    lecture_date="Academic Term 2026",
    executive_summary=(
        "This lecture examines the theoretical and judicial underpinnings of constitutional supremacy. "
        "Prof. Hesham analyzes the origins of judicial review, comparing the American decentralized model "
        "with the European/Egyptian concentrated constitutional court framework. The lecture culminates in an "
        "exhaustive dissection of the three-tier Proportionality Test (Legitimate Aim, Suitability & Necessity, "
        "and Proportionality Stricto Sensu) applied when state legislation curtails fundamental individual liberties."
    ),
    sections=[
        LectureSection(
            section_number=1,
            topic_title="Constitutional Supremacy & Comparative Models of Judicial Review",
            detailed_explanation=(
                "Constitutional supremacy dictates that all statutory enactments, administrative decrees, and executive "
                "acts must conform to the governing constitutional charter. Judicial review is the operational mechanism "
                "empowering courts to invalidate legislation contrary to the constitution.\n\n"
                "Two principal institutional models exist globally:\n"
                "1. Diffuse / Decentralized Model (American Model): Any court in the judicial hierarchy can assess the "
                "constitutionality of an applied statute in an active dispute (inter partes effect).\n"
                "2. Concentrated Model (Kelsenian / European / Egyptian Model): Exclusive jurisdiction is vested in a single "
                "specialized constitutional tribunal (such as the Supreme Constitutional Court of Egypt), rendering decisions "
                "with absolute, erga omnes authority binding all public authorities and ordinary courts."
            ),
            key_bullet_points=[
                "The constitution stands at the apex of the legal hierarchy (Kelsen's Normative Pyramid).",
                "Diffuse systems allow ordinary judges to refuse application of unconstitutional laws.",
                "Concentrated systems reserve invalidation exclusively to a dedicated Constitutional Court.",
                "Supreme Constitutional Court rulings possess erga omnes authority binding all branches of government."
            ],
            doctor_alerts=[
                DoctorAlert(
                    alert_type="EXAM_PREDICTION",
                    highlight_title="Diffuse vs Concentrated Judicial Review Distinction",
                    cue_detected="Doctor emphasized: 'This essay question is guaranteed on your midterm: Distinguish between the legal effects of diffuse judicial review versus concentrated constitutional adjudication!'",
                    alert_content=(
                        "Students often confuse inter partes effect with erga omnes effect. In concentrated systems, invalidation has universal "
                        "erga omnes effect from the date of publication in the Official Gazette."
                    ),
                    exam_impact="Failure to mention erga omnes vs inter partes will result in a deduction of at least 5 marks on the essay."
                )
            ],
            tables=[
                TableDefinition(
                    title="Comparison of Global Judicial Review Frameworks",
                    columns=["System Feature", "Diffuse Model (USA)", "Concentrated Model (Egypt / Germany)"],
                    rows=[
                        ["Adjudicating Body", "All ordinary courts", "Exclusive Supreme Constitutional Court"],
                        ["Legal Effect of Ruling", "Inter partes (parties to case)", "Erga omnes (absolute and universal)"],
                        ["Timing of Review", "Strictly concrete (active dispute)", "Concrete reference or abstract petition"],
                        ["Remedy", "Refusal of enforcement in dispute", "Total nullification of statutory text"]
                    ],
                    notes="Concentrated review provides uniform legal certainty across the entire state apparatus."
                )
            ],
            formulas=[],
            diagrams=[
                DiagramDefinition(
                    diagram_id="law_hierarchy",
                    title="Kelsenian Hierarchy of Legal Norms",
                    diagram_type="FLOWCHART",
                    elements=[
                        DiagramElement(label="Constitution", description="Supreme Law: Grundnorm of the state"),
                        DiagramElement(label="Organic & Statutory Laws", description="Acts passed by parliamentary legislature"),
                        DiagramElement(label="Executive Decrees & Regs", description="Subordinate administrative orders"),
                        DiagramElement(label="Individual Judicial Rulings", description="Court decisions applying statutory law")
                    ],
                    caption="Hierarchical subordination of positive legal norms."
                )
            ]
        ),
        LectureSection(
            section_number=2,
            topic_title="The Three-Tier Proportionality Test in Rights Adjudication",
            detailed_explanation=(
                "Whenever the state restricts a constitutional liberty (such as freedom of expression or assembly) in the interest "
                "of public order or national security, the restriction is legally void unless it satisfies the tripartite Proportionality Test:\n\n"
                "1. Legitimate Objective & Suitability: The measure must pursue a legally recognized, constitutionally valid public objective "
                "and must be rationally capable of achieving that objective.\n"
                "2. Necessity (Least Restrictive Means): The legislative measure must be the least intrusive intervention available. If an equally "
                "effective alternative exists that infringes upon rights to a lesser degree, the statute fails.\n"
                "3. Proportionality Stricto Sensu (Balancing): The societal benefits realized by the public interest must strictly outweigh "
                "the severity of the harm inflicted upon the constitutional right."
            ),
            key_bullet_points=[
                "Every statutory limitation upon a constitutional right must survive strict proportionality scrutiny.",
                "Legitimate aim alone does not justify an overbroad or disproportionate statute.",
                "The state bears the burden of proving that no less restrictive alternative was feasible."
            ],
            doctor_alerts=[
                DoctorAlert(
                    alert_type="CRITICAL_CONCEPT",
                    highlight_title="Strict Sequential Application of the Proportionality Test",
                    cue_detected="Doctor warned: 'When answering case problems, you MUST evaluate Suitability first, then Necessity, and finally Balancing. Skipping to Balancing directly is an automatic failure!'",
                    alert_content=(
                        "The proportionality stages are hierarchical. If a measure fails Necessity (because a less intrusive measure existed), "
                        "the analysis terminates immediately as unconstitutional."
                    ),
                    exam_impact="In problem scenarios, organize your legal argument into three separate subheadings: Suitability, Necessity, and Balancing."
                )
            ],
            tables=[],
            formulas=[],
            diagrams=[
                DiagramDefinition(
                    diagram_id="law_prop_flow",
                    title="Three-Tier Constitutional Proportionality Scrutiny Algorithm",
                    diagram_type="FLOWCHART",
                    elements=[
                        DiagramElement(label="Stage 1: Legitimate Aim", description="Is objective constitutionally valid & suitable?"),
                        DiagramElement(label="Stage 2: Necessity Test", description="Is this the least restrictive means feasible?"),
                        DiagramElement(label="Stage 3: Balancing", description="Does societal benefit outweigh rights infringement?"),
                        DiagramElement(label="Judicial Outcome", description="Constitutional validity upheld or statute nullified")
                    ],
                    caption="Sequential judicial algorithm for evaluating state interference with protected rights."
                )
            ]
        )
    ],
    exam_readiness_section=[
        ExamQuestion(
            question_number=1,
            question_type="CASE_STUDY",
            question_prompt=(
                "Parliament enacts a blanket statutory prohibition banning all public demonstrations, rallies, and gatherings in public spaces "
                "after 8:00 PM to curtail nighttime traffic congestion. A human rights organization petitions the Constitutional Court, alleging "
                "a violation of freedom of assembly. Apply the constitutional proportionality test to determine the validity of this enactment."
            ),
            options=None,
            correct_answer=(
                "The statutory enactment is unconstitutional. While traffic management is a legitimate state aim (Stage 1), a blanket total "
                "prohibition on all assemblies after 8:00 PM fails the Necessity requirement (Stage 2), because less restrictive alternatives "
                "(such as prior notification, designated demonstration routes, or time-restricted permit systems) were readily available. "
                "Furthermore, under Stage 3, the disproportionate suppression of a foundational democratic liberty far outweighs the incidental "
                "benefit of traffic facilitation."
            ),
            model_explanation=(
                "Graders evaluate: 1) Identification of the legitimate public objective; 2) Application of the Least Restrictive Means rule; "
                "3) Explicit conclusion that a blanket ban violates the necessity and balancing prongs."
            ),
            doctor_hint="The professor explicitly warned that blanket bans almost always fail the Necessity prong because narrower alternatives exist.",
            probability="Definite (Doctor Stated)"
        )
    ],
    full_transcript_english=(
        "Good morning, counsel. Welcome to our advanced lecture on Constitutional Law. "
        "Today we explore the bedrock of the rule of law: how the judiciary protects constitutional rights against legislative overreach.\n\n"
        "Constitutional supremacy means nothing if ordinary statutes can contradict the supreme charter with impunity. "
        "This is why judicial review exists. In Egypt, we follow the European concentrated model: our Supreme Constitutional Court "
        "holds exclusive monopoly over constitutional adjudication, and its decisions are erga omnes, binding every authority in the land.\n\n"
        "Now, when the government claims it must restrict freedom of speech or assembly for public order, we apply the Proportionality Test. "
        "Remember the three steps: First, Suitability — is the measure rationally connected to a legitimate goal? Second, Necessity — is it the "
        "least restrictive means possible? If a less severe measure could accomplish the goal, the law is unconstitutional! And third, Balancing — "
        "does the public benefit outweigh the individual rights infringement? Master this three-part framework for your final exam."
    )
)

out_pdf = PDFStudyGuideBuilder(guide_law, output_filename="Law_Constitutional_Proportionality_Guide.pdf").build()
print("Compiled Law Study Guide PDF:", out_pdf)
print(f"Size: {out_pdf.stat().st_size / 1024:.1f} KB")
