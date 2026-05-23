from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from app.config import JOBS_DIR
from app.models.job import Backend, JobError, JobOutputs, JobState, Profile


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(profile: Profile, backend: Backend) -> JobState:
    job_id = uuid4().hex
    job_dir(job_id).mkdir(parents=True, exist_ok=False)
    state = JobState(
        job_id=job_id,
        status="queued",
        progress=0.0,
        created_at=now_iso(),
        updated_at=now_iso(),
        profile=profile,
        backend=backend,
        outputs=JobOutputs(),
    )
    save_state(state)
    return state


def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def state_path(job_id: str) -> Path:
    return job_dir(job_id) / "status.json"


def log_path(job_id: str) -> Path:
    return job_dir(job_id) / "log.txt"


def load_state(job_id: str) -> JobState:
    path = state_path(job_id)
    if not path.exists():
        raise FileNotFoundError(job_id)
    return JobState.model_validate_json(path.read_text(encoding="utf-8"))


def save_state(state: JobState) -> None:
    state.updated_at = now_iso()
    state_path(state.job_id).write_text(
        json.dumps(state.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_state(job_id: str, **changes) -> JobState:
    state = load_state(job_id)
    for key, value in changes.items():
        setattr(state, key, value)
    save_state(state)
    return state


def fail_job(job_id: str, code: str, message: str) -> JobState:
    return update_state(
        job_id,
        status="failed",
        progress=1.0,
        error=JobError(code=code, message=message),
    )

