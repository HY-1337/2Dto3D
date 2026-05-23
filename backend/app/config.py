from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
MODELS_DIR = PROJECT_ROOT / "models"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

SUPPORTED_EXTENSIONS = {".webp", ".jpg", ".jpeg", ".png", ".svg", ".pdf"}
JOB_STATUSES = {
    "queued",
    "preprocessing",
    "generating",
    "processing_mesh",
    "exporting",
    "done",
    "failed",
}


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
