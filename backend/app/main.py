from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import images, jobs, system
from app.config import FRONTEND_DIR, settings, ensure_dirs


ensure_dirs()

app = FastAPI(title="Unified 2D/3D AI Studio", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(images.router, prefix="/api")

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

app.mount("/image-outputs", StaticFiles(directory=str(settings.output_dir)), name="image_outputs")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "index.html",
        headers={"Cache-Control": "no-store"},
    )
