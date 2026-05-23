from typing import Literal

from pydantic import BaseModel


JobStatus = Literal[
    "queued",
    "preprocessing",
    "generating",
    "processing_mesh",
    "exporting",
    "done",
    "failed",
]

Profile = Literal["print", "render"]
Backend = Literal["local", "cloud_stub"]


class JobError(BaseModel):
    code: str
    message: str


class JobOutputs(BaseModel):
    obj: bool = False
    threemf: bool = False
    preview: bool = False


class JobState(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = 0.0
    created_at: str
    updated_at: str
    profile: Profile
    backend: Backend
    input_file: str | None = None
    error: JobError | None = None
    outputs: JobOutputs = JobOutputs()

