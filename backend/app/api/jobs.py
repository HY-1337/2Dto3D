from __future__ import annotations

from pathlib import Path
import shutil
import re

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import SUPPORTED_EXTENSIONS
from app.core.bambu import open_bambu_with_file
from app.core.errors import AppError
from app.core.exporter import build_obj_archive
from app.core.job_store import create_job, job_dir, load_state, save_state
from app.core.pipeline import run_job
from app.models.job import Backend, JobState, Profile


router = APIRouter(tags=["jobs"])


@router.post("/jobs", response_model=JobState)
def create_job_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    profile: Profile = Form("print"),
    backend: Backend = Form("local"),
    pdf_page: int = Form(1),
) -> JobState:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={"code": "UNSUPPORTED_FILE_TYPE", "message": f"Unsupported file type: {ext}"},
        )

    state = create_job(profile=profile, backend=backend)
    path = job_dir(state.job_id)
    input_path = path / f"input_original{ext}"
    with input_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    state.input_file = file.filename
    save_state(state)
    background_tasks.add_task(run_job, state.job_id, pdf_page)
    return state


@router.get("/jobs/{job_id}", response_model=JobState)
def get_job(job_id: str) -> JobState:
    try:
        return load_state(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@router.get("/jobs/{job_id}/download")
def download_job(job_id: str, format: str) -> FileResponse:
    path = job_dir(job_id)
    try:
        state = load_state(job_id)
        stem = _safe_filename(Path(state.input_file or "model").stem)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    if format == "obj":
        build_obj_archive(path, f"{stem}-{job_id[:8]}")
        target = path / "model.zip"
        media_type = "application/zip"
        filename = f"{stem}-{job_id[:8]}.zip"
    elif format == "3mf":
        target = path / "output.3mf"
        media_type = "model/3mf"
        filename = f"{stem}-{job_id[:8]}.3mf"
    else:
        raise HTTPException(status_code=400, detail="format must be obj or 3mf")

    if not target.exists():
        raise HTTPException(status_code=404, detail="Output not found")
    return FileResponse(
        target,
        media_type=media_type,
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/jobs/{job_id}/preview")
def preview_job(job_id: str) -> FileResponse:
    target = job_dir(job_id) / "preview.glb"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Preview not found")
    return FileResponse(
        target,
        media_type="model/gltf-binary",
        filename=f"preview-{job_id[:8]}.glb",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/jobs/{job_id}/open-bambu")
def open_bambu(job_id: str) -> dict:
    try:
        executable = open_bambu_with_file(job_dir(job_id) / "output.3mf")
        return {"ok": True, "path": str(executable)}
    except AppError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return cleaned or "model"
