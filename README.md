# 🎓 LectureAI — Academic Study Suite

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Google Gemini API](https://img.shields.io/badge/AI-Google%20Gemini%203.8%20Flash-orange.svg?logo=google&logoColor=white)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

**Transform spoken university lectures and slide decks into publication-quality academic study guides, automated engineering schematics, practice exam kits, and audio-audited PDFs.**

[Key Capabilities](#-key-capabilities) • [System Architecture](#-system-architecture) • [Quick Start](#-quick-start) • [CLI Usage](#-cli-usage) • [Interactive Web UI](#-interactive-web-ui) • [License](#-license)

</div>

---

## 💡 What is LectureAI?

University lectures in Engineering, Medicine, Science, and STEM often move fast. Spoken explanations frequently deviate from slides, professors drop verbal hints about exams, and technical terminology is mixed across dialects (such as English and spoken Arabic code-switching).

**LectureAI** is an intelligent, multimodal academic companion. Feed it raw lecture audio (or video) and optional slide decks:

1. **Listens & Translates**: Transcribes spoken audio, handles multilingual dialect code-switching, and synthesizes 100% academic English notes.
2. **Grounds in Slides**: Matches spoken topics to slide decks, extracts precise formulas, and excludes unmentioned slide material.
3. **Fact-Checks & Reconciles**: Cross-examines generated notes against the spoken recording to eliminate hallucinations and embeds an official **Audio & Slides Fidelity Certificate**.
4. **Draws Visual Schematics**: Automatically generates publication-grade block diagrams, circuit waveforms, flowcharts, timelines, and concept maps.
5. **Compiles Publication PDFs**: Builds print-ready PDFs with two-pass page numbering (`Page X of Y`), typographic math, and verbatim transcript appendices.

---

## 🌟 Key Capabilities

### 🎙️ 1. Multimodal Audio & Slide Ingestion
- **Any Audio/Video Format**: Supports `.m4a`, `.mp3`, `.wav`, `.aac`, `.ogg`, `.flac`, `.mp4`, `.mov`, `.mkv`.
- **Direct Cloud & Google Drive Streaming**: Paste public or shareable Google Drive links or direct URLs.
- **Multi-Part Lectures**: Handles multiple consecutive recordings (Part 1, Part 2) and merges them chronologically into one unified narrative.
- **Slide Range Bounds**: Target specific slides (e.g. `Slides 5–28`). If left blank, LectureAI inspects the full deck and includes only concepts verbally taught.

### 🌐 2. Bilingual Speech & Dialect Code-Switching
- Seamlessly transcribes bilingual college lectures (e.g., Egyptian / Levantine Arabic mixed with English engineering terms).
- Synthesizes clean, formal, **100% Academic English** summaries and study guides with zero tofu boxes (`□`) or mixed-language clutter in the final document.

### 📊 3. Zero-Collision Universal Diagram Generator
Generates high-resolution vector diagrams via Matplotlib with collision-free layouts:
- **Electronic Waveforms & Circuit Responses**: Half-wave/full-wave rectifiers, Zener clippers, Shockley oscillators, and harmonic plots.
- **System Block Diagrams**: Subsystems, controller feedback loops, sensor chains, and interface buses.
- **Process Cycles & State Machines**: Iterative loops, feedback cycles, and biological or algorithmic sequences.
- **Scientific Flowcharts**: Decision trees, diagnostic algorithms, and procedural pipelines.
- **Comparison Bar Charts**: Benchmark metrics, computational latencies, and material properties.
- **Timelines & Historical Milestones**: Chronological developments and legal or scientific progressions.
- **Hierarchical Concept Maps**: Taxonomy trees and structural categorizations.

### 📐 4. Typographic Math & Auto-Healing Engine
- Advanced regex healer repairs corrupted mathematical tokens (such as `\Delta rac` &rarr; `\frac`, missing square roots, unrendered subscripts).
- Converts formulas into clear, beautifully formatted mathematical typography without missing-glyph defects.

### 🛡️ 5. Audio & Slides Contradiction Auditor
- Every generated guide is automatically cross-examined against the original spoken audio and slides.
- Contradictions, misheard numbers, or slide discrepancies are caught and reconciled before PDF compilation.
- Embeds a cryptographically timestamped **Audio & Slides Fidelity Certificate** directly in the PDF.

### ⚠️ 6. "Doctor's Spoken Exam Traps" & Exam Kit
- **Doctor Alerts**: Highlights verbal warnings, grading pitfalls, and "this will be on the final" hints in prominent amber callout boxes.
- **Active Recall Exam Kit**: Generates clinical vignettes, engineering derivations, and conceptual questions modeled on university exams.
- **Interactive Quiz Mode**: Practice one question at a time in the web dashboard, test your knowledge, reveal model answers, and track your recall score.

### 🧬 7. Pre-Configured STEM & Biomedical Focus
- Preloaded with Biomedical Engineering & College STEM courses:
  - *Bioinstrumentation & Biosensors*
  - *Biomedical Signal Processing*
  - *Biomechanics & Biomaterials*
  - *Medical Imaging Systems*
  - *Human Anatomy & Physiology for Engineers*
  - *Medical Device Design & Electrical Safety*
- Add any custom course with 1 click; saved permanently in your browser via `localStorage`.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph INPUT["1. Input Sources"]
        A["Spoken Lecture Audio / Video\n(.m4a, .mp3, .wav, .mp4)"]
        B["Lecture Slides / Notes\n(PDF, Markdown, Text)"]
        C["Cloud / Google Drive Links"]
    end

    subgraph INGEST["2. Ingestion & Preprocessing"]
        A & C --> D["Chunked Audio Streamer\n& Media Normalizer"]
        B --> E["Slide Slicer & Page Extractor\n(PyPDF)"]
    end

    subgraph ENGINE["3. Pedagogical AI Engine"]
        D & E --> F["Google Gemini 3.8 Flash\nMultimodal Analysis"]
        F --> G["Pedagogical Breakdown\n(Sections, Alerts, Formulas)"]
        F --> H["Exam Readiness Kit\n(Vignettes, Derivations, MCQs)"]
        F --> I["Verbatim Spoken Transcript"]
    end

    subgraph AUDIT["4. Fidelity & Verification"]
        G & D --> J["Contradiction Auditor\nCross-Examines Draft vs Audio"]
        J --> K["Reconciled Study Guide\n+ Fidelity Certificate"]
    end

    subgraph VISUALS["5. Visual Schematics Generator"]
        G --> L["Universal Visualizer Engine\n(Matplotlib)"]
        L --> M["Waveforms, Block Diagrams,\nFlowcharts, Timelines, Maps"]
    end

    subgraph OUTPUT["6. Distribution & UI"]
        K & M --> N["ReportLab PDF Builder\n(Two-Pass Dynamic Numbering)"]
        N --> O["📄 Publication-Grade PDF Guide"]
        K --> P["💻 Interactive Web Dashboard\n& Active Recall Quiz"]
    end
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** ([Download from python.org](https://www.python.org/downloads/))
- A free **Google Gemini API Key** ([Get your key at Google AI Studio](https://aistudio.google.com/apikey))

---

### Method A: Standard Setup (Windows, macOS, Linux)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/lecture-ai-study-suite.git
   cd lecture-ai-study-suite
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set your Gemini API key:**
   ```bash
   # Copy the sample environment file
   cp .env.example .env
   ```
   Open `.env` in any text editor and paste your key:
   ```ini
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.8-flash
   ```
   *(Alternatively, you can leave it blank and paste it directly into the web interface when launching).*

5. **Run the application:**
   ```bash
   # Option 1: Start the desktop launcher (with system tray / auto-browser)
   python launcher.py

   # Option 2: Run the FastAPI web server directly
   python app.py
   ```
   Open your browser at: 👉 **http://127.0.0.1:8000**

---

### Method B: 1-Click Setup (Windows)

1. Double-click **`Install_Dependencies.bat`** to automatically check Python and install all packages.
2. Double-click **`Launch_LectureAI.bat`** to start the app.
3. In the web dashboard that opens, click **"Configure Key"** at top right and paste your Gemini API key.

---

## 💻 CLI Usage

LectureAI includes a feature-rich terminal CLI for automated or headless environments:

```bash
# 1. Instant zero-cost simulation (tests models, diagrams, and PDF compilation without API key)
python cli.py --demo

# 2. Process a lecture audio file
python cli.py --audio "path/to/lecture.m4a" --course "Bioinstrumentation"

# 3. Process lecture audio with accompanying slides (slides 1 to 20)
python cli.py --audio "lecture.m4a" --notes "slides.pdf" --start-slide 1 --end-slide 20

# 4. Process multi-part audio recordings (e.g. split into two halves)
python cli.py --audio "part1.m4a" "part2.m4a" --notes "deck.pdf" --output "Lecture_01_Guide.pdf"

# 5. Process directly from Google Drive share links
python cli.py --course "Power Electronics" --audio "https://drive.google.com/file/d/1.../view"

# 6. Run standalone Audio & Slides Contradiction Auditor
python verify_audio_fidelity.py --audio "lecture.m4a" --notes "slides.pdf" --guide "cached_last_guide.json"
```

---

## 🧪 Running Automated Tests

Run the full automated unit test suite to verify models, diagram rendering, slide slicing, math healing, and PDF generation:

```bash
python -m unittest tests/test_suite.py -v
```

All 9 comprehensive tests run locally and verify:
- ✅ Pydantic schema validation & serialization
- ✅ Visualizer diagram generation (Flowcharts, Cycles, Bar charts)
- ✅ ReportLab PDF compilation and page numbering
- ✅ End-to-end pipeline simulation
- ✅ Contradiction detection & fidelity audit certificate
- ✅ PDF slide deck slicing and range bounding
- ✅ Math defect auto-healing & history deletion API
- ✅ Selective course material discovery
- ✅ Physics waveform plotting and collision-free layout

---

## 🔒 Security & Privacy

- **Zero Secret Leakage**: Your API key stays strictly on your local machine (`.env` is excluded via `.gitignore`).
- **No Cloud Storage Dependency**: All uploaded recordings (`uploads/`) and compiled study guides (`output_pdfs/`) remain stored locally on your device.
- **Ephemeral Session Data**: Cached runs and history (`lecture_history.json`, `cached_last_guide.json`) are kept local to your installation.

---

## 📁 Repository Structure

```
lecture-ai-study-suite/
├── app.py                     # FastAPI web application & REST API
├── launcher.py                # Desktop application launcher
├── cli.py                     # Command-line interface
├── pipeline.py                # End-to-end processing pipeline
├── pedagogy_engine.py         # Gemini multimodal analysis & auditor
├── pdf_builder.py             # ReportLab PDF compiler & math healer
├── visualizer.py              # Matplotlib visual schematics generator
├── models.py                  # Pydantic data schemas
├── link_downloader.py         # Google Drive & cloud file downloader
├── mock_generator.py          # Demo simulation guide generator
├── config.py                  # Environment & directory configuration
├── requirements.txt           # Python package dependencies
├── .env.example               # Template environment configuration
├── .gitignore                 # Excludes .env, recordings, and outputs
├── LICENSE                    # MIT Open Source License
├── Install_Dependencies.bat   # 1-click installer for Windows
├── Launch_LectureAI.bat       # 1-click launcher for Windows
├── templates/
│   └── index.html             # Interactive web UI dashboard
├── static/                    # Icons and application branding
├── tests/
│   └── test_suite.py          # Automated unit test suite
├── uploads/                   # Local staging directory (.gitkeep)
├── output_pdfs/               # Generated study guides (.gitkeep)
└── generated_assets/          # Rendered diagram images (.gitkeep)
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — see the LICENSE file for details.
