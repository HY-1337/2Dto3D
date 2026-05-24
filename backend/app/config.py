from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
MODELS_DIR = PROJECT_ROOT / "models"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"
IMAGE_OUTPUT_DIR = BACKEND_DIR / "outputs"

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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    image_provider: str = "dashscope"
    dashscope_api_key: str = ""
    dashscope_model: str = "wan2.7-image"
    dashscope_api_url: str = ""
    dashscope_size: str = ""
    dashscope_watermark: bool = False
    dashscope_thinking_mode: bool = True

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "dall-e-3"
    custom_api_url: str = ""
    custom_api_key: str = ""

    default_width: int = 1024
    default_height: int = 1024
    output_dir: Path = IMAGE_OUTPUT_DIR


settings = Settings()


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
