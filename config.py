import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

# Directories
UPLOAD_DIR = BASE_DIR / "uploads"
ASSETS_DIR = BASE_DIR / "generated_assets"
OUTPUT_DIR = BASE_DIR / "output_pdfs"

for folder in [UPLOAD_DIR, ASSETS_DIR, OUTPUT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PRIMARY_GEMINI_MODEL = "gemini-3.8-flash"
FALLBACK_GEMINI_MODEL = "gemini-3.6-flash"
ALLOWED_GEMINI_MODELS = frozenset({PRIMARY_GEMINI_MODEL, FALLBACK_GEMINI_MODEL})

def default_gemini_model(configured_model: str | None = None) -> str:
    """Resolve the deployment default, allowing only an approved explicit override."""
    selected = (configured_model or PRIMARY_GEMINI_MODEL).strip()
    return selected if selected in ALLOWED_GEMINI_MODELS else PRIMARY_GEMINI_MODEL

_configured_model = os.environ.get("GEMINI_MODEL", "").strip()
# Keep old .env files usable, while never allowing obsolete/unapproved IDs at runtime.
DEFAULT_MODEL = default_gemini_model(_configured_model)

WHISPER_MODEL = os.environ.get("LECTUREAI_WHISPER_MODEL", "small").strip() or "small"
WHISPER_DEVICE = os.environ.get("LECTUREAI_WHISPER_DEVICE", "cpu").strip().lower() or "cpu"
WHISPER_COMPUTE_TYPE = os.environ.get("LECTUREAI_WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"

def set_gemini_model(model_name: str) -> None:
    """Set active model, restricted to the supported primary/fallback pair."""
    global DEFAULT_MODEL
    if model_name not in ALLOWED_GEMINI_MODELS:
        raise ValueError("Unsupported Gemini model. Choose gemini-3.8-flash or gemini-3.6-flash.")
    DEFAULT_MODEL = model_name
    os.environ["GEMINI_MODEL"] = model_name

def resolve_gemini_model(model_name: str | None = None) -> str:
    """Return an approved configured model or reject unsupported runtime input."""
    selected = (model_name or DEFAULT_MODEL).strip()
    if selected not in ALLOWED_GEMINI_MODELS:
        raise ValueError("Unsupported Gemini model. Choose gemini-3.8-flash or gemini-3.6-flash.")
    return selected

def gemini_model_candidates(model_name: str | None = None) -> list[str]:
    """Return the selected model and, for the primary only, its approved fallback."""
    selected = resolve_gemini_model(model_name)
    if selected == PRIMARY_GEMINI_MODEL:
        return [PRIMARY_GEMINI_MODEL, FALLBACK_GEMINI_MODEL]
    return [selected]

# Supported Audio Formats
SUPPORTED_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm", ".wma"}

# Supported Notes & Slides Formats
SUPPORTED_NOTES_EXTS = {".pdf", ".txt", ".md"}

def set_gemini_api_key(key: str) -> None:
    """Save API key to .env and environment."""
    global GEMINI_API_KEY
    GEMINI_API_KEY = key
    os.environ["GEMINI_API_KEY"] = key
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(f"GEMINI_API_KEY={key}\nGEMINI_MODEL={DEFAULT_MODEL}\n")

def get_gemini_api_key() -> str:
    """Return active Gemini API key or empty string."""
    return os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
