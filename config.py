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
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

def set_gemini_model(model_name: str) -> None:
    """Set active model."""
    global DEFAULT_MODEL
    DEFAULT_MODEL = model_name
    os.environ["GEMINI_MODEL"] = model_name

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
