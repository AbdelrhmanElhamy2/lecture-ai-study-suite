from models import (
    LectureStudyGuide, LectureSection, DoctorAlert, TableDefinition,
    DiagramDefinition, DiagramElement, ExamQuestion, KeyFormula
)

def get_sample_bilingual_lecture_guide() -> LectureStudyGuide:
    """
    Returns a realistic lecture study guide generated from a bilingual (Arabic + English)
    lecture on Operating Systems: Concurrency, Deadlocks, and Semaphores.
    """
    return LectureStudyGuide(
        course_name="Operating Systems & Concurrent Computing (CS302)",
        lecture_title="Concurrency Control, Semaphores, and Deadlock Prevention",
        lecturer_name="Prof. Tarek Mansour",
        lecture_date="Academic Term 2026",
        executive_summary=(
            "This lecture addresses fundamental challenges in concurrent multi-threaded execution. "
            "The professor explores race conditions, critical section criteria, Edsger Dijkstra's "
            "semaphore primitives (wait and signal), dining philosophers problem, and the four Coffman "
            "conditions required for deadlocks. Special emphasis was placed on resource allocation "
            "graphs and Banker's algorithm calculations frequently tested on university exams."
        ),
        sections=[
            LectureSection(
                section_number=1,
                topic_title="Critical Section Problem & Synchronization Primitives",
                detailed_explanation=(
                    "When multiple threads or processes execute concurrently and share mutable memory, "
                    "uncontrolled interleaved access leads to race conditions where output depends on non-deterministic "
                    "scheduling order. The critical section is any code segment accessing shared resources.\n\n"
                    "To build a valid critical section protocol, three mandatory criteria must be satisfied simultaneously:\n"
                    "1. Mutual Exclusion: If thread Pi is executing in its critical section, no other thread can execute.\n"
                    "2. Progress: If no thread is in its critical section and some wish to enter, selection cannot be postponed indefinitely.\n"
                    "3. Bounded Waiting: A bound must exist on the number of times other threads are allowed to enter after a thread has requested entry."
                ),
                key_bullet_points=[
                    "Race conditions occur due to non-deterministic thread interleaving on shared variables.",
                    "Mutual exclusion alone is insufficient; progress and bounded waiting must also be guaranteed.",
                    "Disabling interrupts is only feasible in single-core kernel code and inappropriate for user-level multi-core applications."
                ],
                doctor_alerts=[
                    DoctorAlert(
                        alert_type="EXAM_PREDICTION",
                        highlight_title="The Three Critical Section Rules",
                        cue_detected="Doctor emphasized: 'Pay close attention here, this is coming in the midterm: Mutual Exclusion alone is not enough, you must include Progress and Bounded Waiting!'",
                        alert_content=(
                            "The professor explicitly stressed that answering an exam question by mentioning only "
                            "Mutual Exclusion will result in losing half the marks. You MUST state Progress and Bounded Waiting "
                            "with their formal definitions."
                        ),
                        exam_impact=(
                            "Expect an essay or definition question asking: 'Define the Critical Section Problem and state the three "
                            "requirements for its valid solution.' Always write Mutual Exclusion, Progress, and Bounded Waiting."
                        )
                    )
                ],
                tables=[
                    TableDefinition(
                        title="Synchronization Solutions Comparison",
                        columns=["Mechanism", "Level", "Busy Waiting?", "Multi-Core Safe?"],
                        rows=[
                            ["Peterson's Algorithm", "User / Software", "Yes (Spinlock)", "Only with memory barriers"],
                            ["TestAndSet / CAS", "Hardware Atomic", "Yes (Spinlock)", "Yes (Atomic instruction)"],
                            ["POSIX Mutex Locks", "OS / Library", "No (Sleep/Wakeup)", "Yes"],
                            ["Counting Semaphores", "OS Abstraction", "No (Block queue)", "Yes"]
                        ],
                        notes="Comparative evaluation of software, hardware, and OS synchronization tools."
                    )
                ],
                formulas=[
                    KeyFormula(
                        formula_name="Speedup Factor under Amdahl's Law",
                        latex_expression=r"S(N) = \frac{1}{(1 - P) + \frac{P}{N}}",
                        plain_text_expression="S(N) = 1 / ((1 - P) + (P / N))",
                        variables_explanation=[
                            "S(N): Overall theoretical speedup",
                            "P: Parallel portion of execution time (0 <= P <= 1)",
                            "N: Number of processing cores"
                        ],
                        exam_application="Expect numerical questions calculating speedup limits when scaling to many cores."
                    )
                ],
                diagrams=[
                    DiagramDefinition(
                        diagram_id="sync_flow",
                        title="Thread Synchronization Entry-Exit Cycle",
                        diagram_type="FLOWCHART",
                        elements=[
                            DiagramElement(label="Entry Section", description="Acquires lock or decrements semaphore"),
                            DiagramElement(label="Critical Section", description="Executes shared data modifications"),
                            DiagramElement(label="Exit Section", description="Releases lock or increments semaphore"),
                            DiagramElement(label="Remainder Section", description="Executes non-critical thread work")
                        ],
                        caption="Classical structure of concurrent processes executing shared memory sections."
                    )
                ]
            ),
            LectureSection(
                section_number=2,
                topic_title="Deadlocks and the Four Coffman Conditions",
                detailed_explanation=(
                    "A deadlock is a catastrophic state where every thread in a set is waiting for an event "
                    "that only another thread in the set can cause. In operating systems, deadlocks arise when "
                    "threads contend for non-preemptible exclusive resources (printers, locks, database records).\n\n"
                    "In 1971, Edward G. Coffman Jr. proved that a deadlock can arise IF AND ONLY IF all four conditions "
                    "hold simultaneously in the system. Breaking even a single condition makes deadlock impossible."
                ),
                key_bullet_points=[
                    "Deadlock requires ALL FOUR Coffman conditions to hold concurrently.",
                    "Resource Allocation Graphs (RAG) with cycles indicate deadlock if and only if each resource has a single instance.",
                    "Banker's Algorithm by Dijkstra provides deadlock avoidance by testing safe states before resource allocation."
                ],
                doctor_alerts=[
                    DoctorAlert(
                        alert_type="COMMON_PITFALL",
                        highlight_title="Cycles in Multi-Instance Resource Allocation Graphs",
                        cue_detected="Doctor warned: 'Students always get confused here: having a cycle in the Resource Allocation Graph does NOT automatically mean deadlock if multiple instances exist!'",
                        alert_content=(
                            "A cycle in a Resource Allocation Graph is a NECESSARY and SUFFICIENT condition for deadlock "
                            "ONLY when every resource type has exactly 1 instance. If resource types have multiple instances, "
                            "a cycle does NOT guarantee deadlock!"
                        ),
                        exam_impact=(
                            "This is a guaranteed trick question on the midterm. If given a graph with multiple instances per resource "
                            "and asked 'Is this system deadlocked?', do NOT jump to yes just because you see a loop. Trace the thread allocations!"
                        )
                    )
                ],
                tables=[
                    TableDefinition(
                        title="The Four Coffman Conditions for Deadlock",
                        columns=["Condition", "Definition", "Prevention Strategy"],
                        rows=[
                            ["1. Mutual Exclusion", "At least one resource held non-shareably", "Make resources shareable (e.g. read-only files)"],
                            ["2. Hold and Wait", "Process holds resource while requesting more", "Require process to request all resources upfront"],
                            ["3. No Preemption", "Resources cannot be forcibly confiscated", "Preempt resources if new request cannot be allocated"],
                            ["4. Circular Wait", "Chain of processes each waiting for next", "Enforce strict global resource ordering protocol"]
                        ],
                        notes="To prevent deadlocks, the OS must invalidate at least one of these four conditions."
                    )
                ],
                diagrams=[
                    DiagramDefinition(
                        diagram_id="coffman_cycle",
                        title="Four Necessary Coffman Conditions",
                        diagram_type="PROCESS_CYCLE",
                        elements=[
                            DiagramElement(label="Mutual Exclusion"),
                            DiagramElement(label="Hold & Wait"),
                            DiagramElement(label="No Preemption"),
                            DiagramElement(label="Circular Wait")
                        ],
                        caption="All 4 conditions must hold simultaneously for a system deadlock to persist."
                    )
                ]
            )
        ],
        exam_readiness_section=[
            ExamQuestion(
                question_number=1,
                question_type="MCQ",
                question_prompt=(
                    "In a computer system, a Resource Allocation Graph contains a cycle. Which of the following statements is unconditionally TRUE?"
                ),
                options=[
                    "A) The system is definitely deadlocked.",
                    "B) The system is deadlocked only if each resource type in the cycle has exactly one instance.",
                    "C) The system cannot be deadlocked because cycles indicate safe feedback loops.",
                    "D) Deadlock can be resolved by terminating all waiting processes simultaneously."
                ],
                correct_answer="B) The system is deadlocked only if each resource type in the cycle has exactly one instance.",
                model_explanation=(
                    "If each resource class possesses only 1 unit, a cycle is necessary and sufficient for deadlock. "
                    "However, if multiple instances exist, other non-deadlocked threads can release instances to break the cycle."
                ),
                doctor_hint="The doctor warned: 'الطلبة بتلخبط في الحتة دي' - students always pick A blindly!",
                probability="Definite (Doctor Stated)"
            ),
            ExamQuestion(
                question_number=2,
                question_type="SHORT_ANSWER",
                question_prompt=(
                    "Explain why disabling hardware interrupts is NOT considered an acceptable mutual exclusion mechanism for user-level multi-core applications."
                ),
                correct_answer=(
                    "1) Multi-core systems: Disabling interrupts on one core only affects that specific core; other CPU cores continue executing and accessing shared memory.\n"
                    "2) Security & Liveness: If a user thread disables interrupts and enters an infinite loop, the entire operating system hangs and loses CPU control."
                ),
                model_explanation="Exam graders look for two key points: Multi-core ineffectiveness and vulnerability to denial of service.",
                doctor_hint="Doctor mentioned this while discussing why Peterson's algorithm or atomic instructions are needed instead of simple CLI instructions.",
                probability="High Probability Exam Question"
            ),
            ExamQuestion(
                question_number=3,
                question_type="PROBLEM_SOLVING",
                question_prompt=(
                    "Given 3 processes (P0, P1, P2) and 12 units of magnetic tape drives. Currently, P0 holds 5 (needs max 10), "
                    "P1 holds 2 (needs max 4), and P2 holds 2 (needs max 9). Is the current system state SAFE? Show step-by-step Bankers algorithm evaluation."
                ),
                correct_answer=(
                    "Total tape drives = 12. Currently allocated = 5 + 2 + 2 = 9. Available = 12 - 9 = 3 units.\n"
                    "Remaining Need: P0 needs 5, P1 needs 2, P2 needs 7.\n"
                    "Step 1: Available (3) >= Need of P1 (2). P1 executes to completion and releases 2 + 2 = 4 units. New Available = 3 + 2 = 5.\n"
                    "Step 2: Available (5) >= Need of P0 (5). P0 executes to completion and releases 5 units. New Available = 5 + 5 = 10.\n"
                    "Step 3: Available (10) >= Need of P2 (7). P2 completes.\n"
                    "Conclusion: SAFE state exists with execution sequence <P1, P0, P2>."
                ),
                model_explanation="Full marks require showing the Available vector after each step and explicitly writing the safe sequence <P1, P0, P2>.",
                doctor_hint="Doctor stated: 'مسألة الـ Banker's algorithm جاية في الفاينال بنفس الأرقام دي تقريباً!'",
                probability="Definite (Doctor Stated)"
            )
        ],
        full_transcript_english=(
            "Good morning class. Today we are entering one of the most critical topics in computer systems architecture: "
            "concurrency, synchronization, and deadlocks. As you know, modern computing is inherently parallel. We no longer "
            "have single-core machines executing sequential commands one by one. Our systems run hundreds of concurrent threads...\n\n"
            "Now let me explain what happens when threads share memory without coordination. We get what is called a race condition. "
            "Notice this carefully: if two threads attempt to increment a counter variable at the exact same microsecond, what happens? "
            "At the machine code level, incrementing a variable requires three instructions: load from memory into CPU register, "
            "add one to the register, and store the register back into RAM. If the OS scheduler context-switches between the load "
            "and store, the final value will be corrupted.\n\n"
            "To solve this, we define the Critical Section. The doctor emphasized: Pay close attention here, this is on the exam! "
            "Mutual Exclusion alone is NOT enough! You must ensure Progress and Bounded Waiting as well. Students always write "
            "Mutual Exclusion and forget the other two rules, losing half their marks.\n\n"
            "Now moving on to Deadlocks. A deadlock happens when threads are stuck in a cycle of waiting. Edward Coffman proved "
            "the four necessary conditions: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait. All four must hold! "
            "And here is another classic exam trap: if you see a cycle in a Resource Allocation Graph, do NOT automatically say "
            "there is a deadlock unless every resource has only one instance. If there are multiple instances, a cycle does not "
            "guarantee deadlock! Remember this for your midterm."
        )
    )
